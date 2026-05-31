"""Supertonic inference engine wrapper (MNN backend).

Thin adapter over `supertonic_mnn.SupertonicTTS`. Two non-obvious bits:

1. Thread environment (`OMP_NUM_THREADS=1` etc.) is configured before the
   numpy / MNN imports happen. Without this, libgomp's default ("FALSE")
   spawns a worker per core that competes with MNN's own thread pool —
   on a 4-core box you end up with 12–16 threads fighting for 4 cores
   and inference grinds to a crawl. Pinning BLAS pools to 1 lets MNN
   own the parallelism budget. (Same trick the previous ORT-based
   engine used.)

2. MNN's runtime configuration (thread count, memory/precision modes)
   lives in the model's `config.json` on disk, not in any Python API.
   We patch that file after `ensure_models()` downloads it so the user
   can tune threads / memory from add-on options.
"""
from __future__ import annotations

import json
import logging
import os
import platform
import time
from pathlib import Path
from typing import Iterable, List, Optional

_LOGGER = logging.getLogger(__name__)

_THREAD_ENVS = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
)


def configure_thread_envs() -> None:
    """Pin BLAS / OMP thread pools to 1 so MNN owns the parallelism budget.

    Must be called *before* importing numpy / MNN.
    """
    for key in _THREAD_ENVS:
        os.environ.setdefault(key, "1")


# Pin envs at import time. The package's __main__ imports engine lazily
# (after argparse), so this runs before numpy/MNN come in.
configure_thread_envs()

import numpy as np  # noqa: E402

from .const import MNN_CACHE_DIR, VOICES, WARMUP_TEXT  # noqa: E402


def _read_sysfs_int(path: str) -> Optional[int]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _read_sysfs_str(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def log_cpu_diagnostics() -> None:
    """Log per-CPU governor / freq range so users on weak-RTF hardware can
    tell at a glance whether their host is throttling.

    What to look for in the output:

      * ``cpuinfo_max_freq`` should be the CPU's rated turbo (e.g. 3400 MHz
        for N100, 2400 MHz for Pi 5, 1500 MHz for Pi 4). If it equals base
        clock, BIOS/firmware has locked turbo off.
      * ``scaling_max_freq`` lower than ``cpuinfo_max_freq`` means the
        governor or kernel has further capped it.
      * ``scaling_governor`` should be ``performance``, ``schedutil``, or
        ``ondemand``. ``powersave`` on Intel pegs the CPU at base clock
        and is the most common cause of "stuck at 800 MHz" on N100.
      * ``scaling_cur_freq`` is the current clock; under our warm-up load
        it should be close to ``scaling_max_freq``.
    """
    base = "/sys/devices/system/cpu"
    if not os.path.isdir(base):
        return

    cpus = sorted(
        d for d in os.listdir(base)
        if d.startswith("cpu") and d[3:].isdigit()
    )
    if not cpus:
        return

    rows = []
    for cpu in cpus:
        fdir = f"{base}/{cpu}/cpufreq"
        if not os.path.isdir(fdir):
            continue
        rows.append({
            "cpu": cpu,
            "gov": _read_sysfs_str(f"{fdir}/scaling_governor"),
            "cur": _read_sysfs_int(f"{fdir}/scaling_cur_freq"),
            "scaling_max": _read_sysfs_int(f"{fdir}/scaling_max_freq"),
            "cpuinfo_max": _read_sysfs_int(f"{fdir}/cpuinfo_max_freq"),
        })

    if not rows:
        _LOGGER.info(
            "CPU diagnostics: no cpufreq sysfs nodes visible to the "
            "container. Host governor / clocks cannot be inspected from here."
        )
        return

    def _mhz(khz: Optional[int]) -> str:
        return f"{khz // 1000} MHz" if khz else "?"

    _LOGGER.info(
        "CPU diagnostics (cur / scaling_max / cpuinfo_max, governor):"
    )
    for r in rows:
        _LOGGER.info(
            "  %s: %s / %s / %s, governor=%s",
            r["cpu"],
            _mhz(r["cur"]),
            _mhz(r["scaling_max"]),
            _mhz(r["cpuinfo_max"]),
            r["gov"] or "?",
        )

    # Loud warning if cpuinfo_max == ~base clock for a CPU that should
    # turbo much higher. We can't tell the CPU model from here, but if
    # cpuinfo_max <= 1.0 GHz on x86 it's almost certainly capped.
    cpuinfo_max = rows[0]["cpuinfo_max"]
    gov = rows[0]["gov"]
    if cpuinfo_max and cpuinfo_max <= 1_000_000 and platform.machine() == "x86_64":
        _LOGGER.warning(
            "Host reports CPU max = %s. Intel x86 typically turbos well "
            "above this. Check BIOS for SpeedStep / Turbo Boost and the "
            "host CPU governor (powersave pegs at base clock).",
            _mhz(cpuinfo_max),
        )
    elif gov == "powersave":
        _LOGGER.warning(
            "Host CPU governor is 'powersave' — this caps clock to base "
            "and roughly halves throughput. Switch the host to "
            "'performance' or 'schedutil' for full speed."
        )


def _detect_best_precision() -> str:
    """Pick the precision that best matches the host CPU's ISA.

    Read /proc/cpuinfo once and infer:

      * x86 with AVX-VNNI (Alder Lake / N100+, Zen 4+):
        int8 — VNNI accelerates 8-bit dot products ~2x over AVX2 fp32.
      * x86 without VNNI: fp32 — fp16 has no hardware path on most
        consumer Intel/AMD (AVX-512-FP16 only on Sapphire Rapids+),
        so it would be emulated and identical-or-slower than fp32.
      * ARM with FEAT_DotProd (`asimddp`): int8 — SDOT accelerates
        8-bit dot products. Pi 5 (Cortex-A76) and most A75+ cores.
      * ARM with FEAT_FP16 (`asimdhp` / `fphp`) but no DotProd:
        fp16 — hardware fp16 ops, ~2x bandwidth win.
      * Everything else (e.g. Pi 4 / Cortex-A72): fp32 — safest,
        and the only one without an emulation penalty here.
    """
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            cpuinfo = f.read()
    except OSError:
        return "fp32"

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        if "avx_vnni" in cpuinfo or "avx512_vnni" in cpuinfo:
            return "int8"
        return "fp32"
    if machine in ("aarch64", "arm64"):
        if "asimddp" in cpuinfo:
            return "int8"
        if "asimdhp" in cpuinfo or "fphp" in cpuinfo:
            return "fp16"
        return "fp32"
    return "fp32"


def float_to_pcm16(wav: np.ndarray) -> bytes:
    """Convert float32 mono [-1, 1] → int16 little-endian bytes."""
    if wav.size == 0:
        return b""
    peak = float(np.max(np.abs(wav)))
    if peak > 1.0:
        wav = wav / peak
    pcm = np.clip(wav * 32767.0, -32768.0, 32767.0).astype("<i2")
    return pcm.tobytes()


def _patch_mnn_config(
    model_dir: str,
    *,
    threads: Optional[int],
    memory_mode: Optional[str],
) -> None:
    """Rewrite the MNN config.json so we control thread_num / memory mode.

    supertonic_mnn reads these straight from disk on engine load and
    exposes no Python override, so this is the seam.
    """
    cfg_path = Path(model_dir) / "config.json"
    if not cfg_path.exists():
        _LOGGER.warning("MNN config.json not found at %s; skipping tuning", cfg_path)
        return

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        _LOGGER.warning("Could not read %s: %s", cfg_path, exc)
        return

    changed = False
    if threads is not None and cfg.get("mnn_cfg_thread_num") != threads:
        cfg["mnn_cfg_thread_num"] = int(threads)
        changed = True
    if memory_mode is not None and cfg.get("mnn_cfg_memory") != memory_mode:
        cfg["mnn_cfg_memory"] = memory_mode
        changed = True

    if not changed:
        return

    try:
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except OSError as exc:
        _LOGGER.warning("Could not write %s: %s", cfg_path, exc)
        return

    _LOGGER.info(
        "MNN config tuned: thread_num=%s, memory=%s",
        cfg.get("mnn_cfg_thread_num"),
        cfg.get("mnn_cfg_memory"),
    )


class SupertonicEngine:
    """Owns the loaded Supertonic MNN model and exposes a sync `synthesize`."""

    def __init__(
        self,
        *,
        precision: str = "fp16",
        version: str = "v3",
        steps: int = 3,
        speed: float = 1.0,
        threads: Optional[int] = None,
        memory_mode: Optional[str] = None,
        model_dir: str = MNN_CACHE_DIR,
    ) -> None:
        from supertonic_mnn import SupertonicTTS
        from supertonic_mnn.model import ensure_models

        log_cpu_diagnostics()

        if precision == "auto":
            picked = _detect_best_precision()
            _LOGGER.info(
                "Auto precision: picked %r based on host CPU (%s)",
                picked,
                platform.machine(),
            )
            precision = picked

        # Make sure config.json exists on disk before we try to patch it.
        ensure_models(model_dir, precision, version)
        _patch_mnn_config(model_dir, threads=threads, memory_mode=memory_mode)

        _LOGGER.info(
            "Loading Supertonic %s MNN model (precision=%s, cache=%s)...",
            version,
            precision,
            model_dir,
        )
        t0 = time.monotonic()
        self._tts = SupertonicTTS(
            model_dir=model_dir,
            precision=precision,
            version=version,
        )
        # Force MNN module load now so the first real request doesn't pay it.
        self._tts._get_engine()
        _LOGGER.info("Model loaded in %.2fs", time.monotonic() - t0)

        self.steps = int(steps)
        self.speed = float(speed)
        self.sample_rate = self._tts._get_engine().sample_rate

    @property
    def available_voices(self) -> List[str]:
        return list(VOICES)

    def synthesize(self, text: str, voice: str, lang: str) -> np.ndarray:
        """Synchronous synthesis. Returns float32 wav in [-1, 1]."""
        if voice not in VOICES:
            voice = VOICES[0]
        wav, _sr = self._tts.synthesize(
            text=text,
            voice=voice,
            lang=lang,
            steps=self.steps,
            speed=self.speed,
        )
        return np.asarray(wav, dtype=np.float32)

    def warmup(self, voices: Iterable[str]) -> None:
        """Run a single short utterance per voice so MNN has its modules
        resident before the first real request arrives."""
        wanted = [v for v in voices if v in VOICES]
        if not wanted:
            _LOGGER.info("No valid warmup voices; skipping warmup")
            return
        lang, text = WARMUP_TEXT
        _LOGGER.info("Warming %d voice(s)...", len(wanted))
        t_total = time.monotonic()
        for voice in wanted:
            t0 = time.monotonic()
            try:
                self.synthesize(text, voice, lang)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Warm-up failed for voice=%s: %s", voice, exc)
                continue
            _LOGGER.debug("  warmed %s in %.2fs", voice, time.monotonic() - t0)
        _LOGGER.info("Warm-up complete in %.2fs", time.monotonic() - t_total)
