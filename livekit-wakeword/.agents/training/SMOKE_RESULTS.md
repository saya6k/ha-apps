# 빅스비 smoke run — 2026-06-12 (this Mac, MPS)

End-to-end pipeline validation with `bixby_smoke.yaml` (24 pos / 24 neg /
dnn-tiny / 500 steps). **Every stage works on Apple Silicon:**

| Stage | Result | Notes |
|---|---|---|
| setup --skip-acav | OK | VoxCPM2 snapshot 5.0 GB + backgrounds 233M + RIRs 10M + val features 176M |
| generate (VoxCPM2, MPS) | OK | bfloat16→float32 auto-adjust; **~30 s/clip**; Korean 빅스비 synthesized fine |
| augment + features | OK | (N, 16, 96) feature files |
| train (MPS) | OK | smoke metrics meaningless by design (recall 0.56, FPPH 975) |
| export → ONNX | OK | needs `livekit-wakeword[export]` extra (onnx, onnxscript) |
| add-on bridge inference | OK | exported ONNX loads in wyoming_livekit_wakeword Engine, scores stream |

Gotchas hit (already handled, will recur on a fresh machine):
- macOS python.org SSL: `SSL_CERT_FILE=$(python -m certifi)` needed for HF +
  NLTK downloads.
- `nltk cmudict` + `punkt` must be downloaded before generate's auto
  adversarial stage (English-biased; Korean negatives are manual in config).
- `[export]` extra is separate from `[train,eval]`.

## Production run (`bixby_prod.yaml`) — sizing

- TTS generation dominates: ~60k clips × ~30 s/clip on this Mac ≈ **20+ days**
  → not viable locally. On a rented CUDA GPU (4090/A100), VoxCPM ≈ 1–3 s/clip
  → TTS hours, train (50k steps) a few more hours; ~1 day, ~$5–20.
- Production also needs ACAV100M negatives (**~16 GB**, `setup` without
  `--skip-acav`) — local disk currently ~12 GB free.
- Workspace layout is portable: copy `bixby_prod.yaml`, run setup/run on the
  GPU box (SkyPilot example: upstream `skypilot/train.yaml`), bring back
  `output/bixby/bixby.onnx` → drop into `/share/livekit-wakeword/`.
