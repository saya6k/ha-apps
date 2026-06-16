"""Boot-time CPU diagnostics.

A 0.6B INT4 conformer on CPU is clock-sensitive: an Intel N100 at its 3.4 GHz
turbo vs pinned at 800 MHz base (powersave governor / turbo disabled in BIOS /
thermal) is a ~4-7x swing in RTF. This dumps governor + per-core frequencies and
the relevant ISA flags at boot so throttling is visible without grepping sysfs.
"""
from __future__ import annotations

import glob
import logging
import os

_LOGGER = logging.getLogger(__name__)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def log_cpu_diagnostics() -> None:
    try:
        affinity = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        affinity = os.cpu_count() or 0
    _LOGGER.info("CPU: %s logical, %s usable (affinity)", os.cpu_count(), affinity)

    # ISA flags that decide which MatMulNBits / GEMM kernel onnxruntime picks.
    cpuinfo = _read("/proc/cpuinfo")
    if cpuinfo:
        flags = ""
        for line in cpuinfo.splitlines():
            if line.startswith("flags") or line.startswith("Features"):
                flags = line.split(":", 1)[-1]
                break
        # x86 (avx2/vnni) and ARM (asimddp=dotprod, i8mm, fp16) int8/fp accel flags.
        candidates = ("avx2", "avx512f", "avx_vnni", "avx512_vnni", "sse4_2",
                      "asimd", "asimddp", "i8mm", "asimdhp", "sve", "sve2")
        wanted = [f for f in candidates if f" {f} " in f" {flags} "]
        _LOGGER.info("CPU ISA: %s", ", ".join(wanted) or "(no known SIMD flags found)")

    govs = sorted(glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor"))
    if not govs:
        _LOGGER.info("CPU freq sysfs not available (cannot check throttling)")
        return
    _LOGGER.info("CPU diagnostics (cur / scaling_max / cpuinfo_max, governor):")
    for gpath in govs:
        base = os.path.dirname(gpath)
        cpu = os.path.basename(os.path.dirname(base))
        gov = _read(gpath)
        cur = _read(os.path.join(base, "scaling_cur_freq"))
        smax = _read(os.path.join(base, "scaling_max_freq"))
        imax = _read(os.path.join(base, "cpuinfo_max_freq"))
        def mhz(khz: str) -> str:
            return f"{int(khz)//1000} MHz" if khz.isdigit() else "?"
        _LOGGER.info(
            "  %s: %s / %s / %s, governor=%s", cpu, mhz(cur), mhz(smax), mhz(imax), gov
        )

    no_turbo = _read("/sys/devices/system/cpu/intel_pstate/no_turbo")
    if no_turbo == "1":
        _LOGGER.warning(
            "Intel turbo is DISABLED (intel_pstate/no_turbo=1) — the CPU is "
            "capped at base clock. This is the most common cause of high RTF on "
            "N100-class hosts. Enable turbo in BIOS / set the governor to "
            "'performance' for usable speech-to-text latency."
        )
