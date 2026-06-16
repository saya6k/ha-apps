# Model conversion recipe + runtime benchmark — 2026-06-12

Source model: `3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx`
from the sherpa-onnx GitHub release tagged `speaker-recongition-models`
(upstream's spelling), sha256
`aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2`.

## Why LiteRT (decision record)

| Stack | runtime installed | model | embed fidelity |
|---|---|---|---|
| onnxruntime fp32 | 65 MB | 27.6 MB | reference |
| onnxruntime int8 (dynamic) | 65 MB | 8.4 MB | cos 0.94–0.97 (slower on ARM!) |
| **LiteRT fp16 (shipped)** | **29 MB** | **14 MB** | **cos 0.999997** |

- No ggml speaker-embedding implementation exists (checked 2026-06) —
  going lighter than LiteRT means porting CAM++ to ggml by hand.
- M-series: ~85 ms / 5 s verify @ 1 thread. Speaker separation on the
  release's fangjun/leijun fixtures: same 0.81–0.89, different 0.10–0.29.

## Conversion steps (each one is load-bearing)

1. Fix the dynamic time axis (onnx2tf chokes on it in BOTH backends):
   `python -m onnxsim <src>.onnx campplus_fixed500.onnx --overwrite-input-shape "x:1,500,80"`
2. Constant-fold the remaining `Shape` nodes with onnx-graphsurgeon
   (replace each Shape whose input is now static with an int64 initializer),
   then onnxsim again → kills the `Where`/`Equal` shape arithmetic that
   causes onnx2tf's int64/int32 `Sub` TypeError.
3. `onnx2tf -i campplus_fixed500_clean.onnx -o out -tb tf_converter`
   - the default flatbuffer_direct backend's **fp16 output does not load**
     (CONV_2D prepare fails — no dequant layer); use the tf_converter one.
   - `-ett dynamic_range_quant` produced no extra file; fp16 is what ships.
4. The converted graph's input is **(1, 80, 500)** — onnx2tf transposed the
   layout. Feed `fbank.T`.
5. Fidelity gate before shipping: cosine(ONNX fp32, tflite) ≥ 0.999 on the
   fangjun/leijun fixtures (got 0.999997).

Runtime contract (mirrored in `wyoming_voiceprint/embedder.py`): 16 kHz
mono float32 [-1,1] → kaldi fbank 80 bins, dither 0, snip_edges →
subtract per-utterance mean (`feature_normalize_type: global-mean`) →
repeat-pad/crop to 500 frames → transpose → (1,80,500) → 192-dim, L2-norm.

Test WAVs + venvs in this directory are disposable; the only shipped
artifact is `../../models/campplus_zh_en_fp16.tflite` (sha256 in const.py).
