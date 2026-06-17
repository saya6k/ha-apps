#!/usr/bin/env python3
"""Convert Nemotron 3.5 ASR .nemo into the pure-C runtime binary format.

The generated file is intentionally simple: a little-endian tensor stream with
64-byte aligned tensor payloads, followed by the RNNT vocabulary strings.
Runtime inference does not need Python, PyTorch, NeMo, YAML, or SentencePiece.
"""

from __future__ import annotations

import argparse
import os
import struct
import tarfile
import tempfile
from pathlib import Path

import numpy as np
import torch
import yaml


MAGIC = b"NM35ASR\0"
VERSION = 1
DTYPE_F32 = 1
DTYPE_BF16 = 2
DTYPE_Q8P = 4

QUANT_MAP = {
    "f32":  (DTYPE_F32,  False, False),
    "bf16": (DTYPE_BF16, True,  False),
    "q8p":  (DTYPE_Q8P,  False, True),
}


def align64(f):
    pad = (-f.tell()) % 64
    if pad:
        f.write(b"\0" * pad)


def extract_member(tar: tarfile.TarFile, suffix: str, dst: Path) -> Path:
    for m in tar.getmembers():
        if m.name.endswith(suffix):
            out = dst / Path(m.name).name
            with tar.extractfile(m) as src, out.open("wb") as fp:
                if src is None:
                    raise RuntimeError(f"cannot extract {suffix}")
                while True:
                    b = src.read(1024 * 1024)
                    if not b:
                        break
                    fp.write(b)
            return out
    raise RuntimeError(f"{suffix} not found in archive")


def load_nemo(nemo_path: Path, work_dir: Path):
    cfg_path = work_dir / "model_config.yaml"
    ckpt_path = work_dir / "model_weights.ckpt"
    if not (cfg_path.exists() and ckpt_path.exists()):
        with tarfile.open(nemo_path, "r:") as tar:
            cfg_path = extract_member(tar, "model_config.yaml", work_dir)
            ckpt_path = extract_member(tar, "model_weights.ckpt", work_dir)
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    state = torch.load(ckpt_path, map_location="cpu", mmap=True, weights_only=True)
    return cfg, state


def should_write_bf16(key: str, tensor: torch.Tensor, enabled: bool) -> bool:
    if not enabled or not key.endswith(".weight"):
        return False
    if tensor.numel() == 0:
        return False

    linear_suffixes = (
        "encoder.pre_encode.out.weight",
        "prompt_kernel.0.weight",
        "prompt_kernel.2.weight",
        "joint.pred.weight",
        "joint.enc.weight",
        "joint.joint_net.2.weight",
    )
    if key in linear_suffixes:
        return True

    if key.startswith("decoder.prediction.dec_rnn.lstm.weight_"):
        return True

    if key.startswith("encoder.layers."):
        return any(s in key for s in (
            ".feed_forward1.linear1.weight",
            ".feed_forward1.linear2.weight",
            ".feed_forward2.linear1.weight",
            ".feed_forward2.linear2.weight",
            ".self_attn.linear_q.weight",
            ".self_attn.linear_k.weight",
            ".self_attn.linear_v.weight",
            ".self_attn.linear_out.weight",
            ".self_attn.linear_pos.weight",
            ".conv.pointwise_conv1.weight",
            ".conv.pointwise_conv2.weight",
        ))

    return False


def should_write_q8(key: str, tensor: torch.Tensor, enabled: bool) -> bool:
    return should_write_bf16(key, tensor, enabled)


# No w8a16 or q4p — upstream C runtime supports only f32, bf16, q8p.



def tensor_bf16_bytes(tensor: torch.Tensor) -> bytes:
    arr = tensor.detach().cpu().contiguous().float().numpy().astype("<f4", copy=False)
    bits = arr.view(np.uint32)
    rounded = bits + (((bits >> 16) & 1) + 0x7FFF)
    bf16 = (rounded >> 16).astype("<u2", copy=False)
    return bf16.tobytes(order="C")


def tensor_q8p_bytes(tensor: torch.Tensor) -> bytes:
    arr = tensor.detach().cpu().contiguous().float().numpy().astype("<f4", copy=False)
    if arr.ndim == 0:
        raise ValueError("cannot q8-quantize scalar tensor")
    rows = int(arr.shape[0])
    flat = arr.reshape(rows, -1)
    cols = int(flat.shape[1])
    stride = (cols + 15) & ~15
    row_tiles = (rows + 3) // 4

    max_abs = np.max(np.abs(flat), axis=1)
    scales = (max_abs / 127.0).astype("<f4", copy=False)
    safe_scales = scales.copy()
    safe_scales[safe_scales == 0.0] = 1.0
    q = np.rint(flat / safe_scales[:, None])
    q = np.clip(q, -127, 127).astype(np.int8, copy=False)

    qpad = np.zeros((row_tiles * 4, stride), dtype=np.int8)
    qpad[:rows, :cols] = q
    packed = np.empty((row_tiles, stride // 16, 4, 16), dtype=np.int8)
    for rt in range(row_tiles):
        tile = qpad[rt * 4:(rt + 1) * 4]
        packed[rt] = tile.reshape(4, stride // 16, 16).transpose(1, 0, 2)
    return scales.tobytes(order="C") + packed.tobytes(order="C")


def write_model(out_path: Path, cfg: dict, state: dict, quant: str = "f32"):
    """Write a .bin file with the requested quantization.

    Args:
        out_path: Destination .bin file path.
        cfg: Parsed model_config.yaml.
        state: PyTorch checkpoint state dict.
        quant: One of "f32", "bf16", "q8p".
    """
    if quant not in QUANT_MAP:
        raise ValueError(f"Unknown quantization: {quant}")
    target_dtype, use_bf16, use_q8p = QUANT_MAP[quant]

    vocab = list(cfg["joint"]["vocabulary"])
    keys = list(state.keys())
    with out_path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<IIII", VERSION, len(keys), len(vocab), 0))
        for key in keys:
            tensor = state[key].detach().cpu().contiguous()
            if tensor.dtype != torch.float32:
                tensor = tensor.float()
            name = key.encode("utf-8")
            if len(name) > 65535:
                raise ValueError(f"tensor name too long: {key}")
            dims = list(tensor.shape)
            dims4 = dims + [1] * (4 - len(dims))
            if target_dtype == DTYPE_Q8P and should_write_q8(key, tensor, use_q8p):
                dtype = DTYPE_Q8P
                raw = tensor_q8p_bytes(tensor)
            elif target_dtype == DTYPE_BF16 and should_write_bf16(key, tensor, use_bf16):
                dtype = DTYPE_BF16
                raw = tensor_bf16_bytes(tensor)
            else:
                dtype = DTYPE_F32
                raw = tensor.numpy().tobytes(order="C")
            f.write(struct.pack("<HBB", len(name), len(dims), dtype))
            f.write(name)
            f.write(struct.pack("<QQQQ", *dims4[:4]))
            f.write(struct.pack("<Q", len(raw)))
            align64(f)
            f.write(raw)
            align64(f)
        f.write(struct.pack("<I", len(vocab)))
        for token in vocab:
            b = str(token).encode("utf-8")
            f.write(struct.pack("<I", len(b)))
            f.write(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nemo", type=Path, help="nemotron-3.5-asr-streaming-0.6b.nemo")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Output .bin path (default: <stem>-<quant>.bin)")
    ap.add_argument("--work-dir", type=Path, default=None, help="Reuse/extract into this directory")
    ap.add_argument("--quants", nargs="+", default=["f32"],
                    choices=list(QUANT_MAP.keys()),
                    help="Quantization formats to produce (default: f32)")
    # Legacy flags (kept for backward compat).
    ap.add_argument("--bf16-linear-weights", action="store_true",
                    help=argparse.SUPPRESS)
    ap.add_argument("--w8a8-linear-weights", action="store_true",
                    help=argparse.SUPPRESS)
    args = ap.parse_args()

    # Map legacy flags to --quants.
    if args.bf16_linear_weights:
        args.quants = ["bf16"]
    elif args.w8a8_linear_weights:
        args.quants = ["q8p"]

    if args.work_dir:
        args.work_dir.mkdir(parents=True, exist_ok=True)
        cfg, state = load_nemo(args.nemo, args.work_dir)
    else:
        with tempfile.TemporaryDirectory(prefix="nemotron_nemo_") as td:
            cfg, state = load_nemo(args.nemo, Path(td))

    stem = args.nemo.stem
    for quant in args.quants:
        out_path = args.output or Path(f"{stem}-{quant}.bin")
        if len(args.quants) > 1 and args.output:
            # If multiple quants with a single output name, derive per-quant names.
            out_path = args.output.parent / f"{args.output.stem}-{quant}{args.output.suffix}"
        write_model(out_path, cfg, state, quant=quant)
        size_gb = os.path.getsize(out_path) / (1024**3)
        print(f"wrote {out_path} ({size_gb:.2f} GiB)")


if __name__ == "__main__":
    main()
