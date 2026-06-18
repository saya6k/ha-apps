# Spec: True Streaming for nemotron-asr-c

## Objective

현재 nemotron-asr-c는 RNN-T 루핑 아티팩트로 인해 `AudioStop` 시점에 전체 오디오를 일괄 처리한다 (`handler.py`). 이 스펙은 루핑 아티팩트의 **근본 원인을 수정하여** 청크 단위 실시간 전사(< 300ms 단어 레이턴시)를 구현하는 것이 목적이다.

**User:** HA 음성 파이프라인 사용자. 말하는 즉시 단어가 화면에 나타나는 Whisper/Deepgram 수준의 UX를 기대한다.

**Success criteria:**
- `AudioChunk` 수신마다 `stream.text()`가 반복 없이 점진적으로 성장하는 전사본을 반환
- `AudioStop` 시 최종 `Transcript`가 한 번 전송되고, 중간에 partial 텍스트가 변경될 때마다 `transcript-chunk` 이벤트 발송
- Buffered 모드(현재)와 동일하거나 더 나은 정확도 (WER regression 없음)
- `supports_transcript_streaming=True`로 변경

---

## Root Cause Analysis

### 버그: engine.py `accept_audio()` 전 프레임 재투입

`NemoCStream.accept_audio()` (engine.py:63–96)에 버그가 있다:

```python
# 현재 (버그):
self._audio = np.concatenate([self._audio, a])   # 누적
mel = nemo_mel_spectrogram(self._audio, n_samples)  # 전체 mel 재계산
self._feed_encoder(mel, total_frames)               # 전체 프레임 재투입 ← 버그
```

`nemo_encoder_forward_chunks`에 **항상 0번 프레임부터 전체**를 전달하므로, RNN-T 스트림이 같은 인코더 프레임을 중복으로 수신한다. `_mel_done` 필드가 이를 추적하도록 설계되어 있었으나 **사용되지 않음**.

실제 HA 파이프라인 로그에서 확인된 아티팩트 패턴:
```
오늘 날씨가 참 좋네요. <ko-KR> 안녕하세요. <ko-KR> 오늘 날씨가 참 좋네요. <ko-KR> ...
```
`<ko-KR>` 태그가 구분자 역할로 반복 — 각 `accept_audio()` 호출이 전체 시퀀스를 재방출한 결과.

### handler.py는 이를 bytearray 버퍼로 우회

`AudioStop` 시점에 전체 오디오를 한 번에 투입하면 `accept_audio()`가 단 한 번만 호출되므로 루핑이 발생하지 않는다. 이것이 현재 buffered 모드의 이유.

---

## Fix Plan

### Phase 1 — Python 버그 수정 (engine.py)

`accept_audio()` 를 고쳐 **새 mel 프레임만** 인코더에 투입한다:

```python
def accept_audio(self, samples: np.ndarray) -> None:
    a = np.ascontiguousarray(samples, dtype=np.float32)
    if a.size == 0:
        return
    self._audio = np.concatenate([self._audio, a])

    out_frames = c_int(0)
    mel_ptr = self._e._lib.nemo_mel_spectrogram(
        self._e._ctx,
        self._audio.ctypes.data_as(POINTER(c_float)),
        self._audio.shape[0],
        ctypes.byref(out_frames),
    )
    if not mel_ptr:
        return
    try:
        mel_frames = out_frames.value
        if mel_frames <= self._mel_done:
            return
        mel_arr = np.ctypeslib.as_array(
            ctypes.cast(mel_ptr, POINTER(c_float)),
            shape=(self._e._n_mels, mel_frames),
        ).copy()
        # 새 프레임만 (delta) 인코더에 투입
        new_mel = mel_arr[:, self._mel_done:]
        self._feed_encoder(new_mel, new_mel.shape[1])
        self._mel_done = mel_frames
    finally:
        _libc.free(mel_ptr)
```

`_feed_encoder()`는 변경 없음 — 받은 프레임만 처리하면 된다.

### Phase 2 — handler.py 스트리밍 전환

`AudioChunk`마다 C에 투입하고 partial 텍스트를 전송한다:

```python
# AudioStart:
self._stream = self._engine.create_stream(self._language)
self._last_partial = ""

# AudioChunk:
chunk = AudioChunk.from_event(event)
samples = _pcm16_to_float32(chunk.audio)
async with _ASR_LOCK:
    await loop.run_in_executor(None, self._stream.accept_audio, samples)
    partial = self._stream.text()
if partial != self._last_partial:
    await self.write_event(
        Event("transcript-chunk", {"text": partial})
    )
    self._last_partial = partial

# AudioStop:
async with _ASR_LOCK:
    await loop.run_in_executor(None, self._stream.finalize)
    text = self._stream.text()
self._stream.close()
await self.write_event(Transcript(text=text, language=self._language).event())
```

`supports_transcript_streaming=True` 로 변경.

### Phase 3 — C 런타임 패치 (조건부)

Phase 1 + 2 후에도 **매우 짧은 청크(< 160ms)**에서 루핑이 남아있으면:

**옵션 A: 최소 청크 강제 (Python)**
Phase 2에서 인코더 투입을 16 mel 프레임(≈ 160ms) 이상 쌓인 경우에만 수행:
```python
MIN_ENCODER_FRAMES = 16
if (mel_frames - self._mel_done) < MIN_ENCODER_FRAMES:
    return  # 아직 투입하지 않음
```

**옵션 B: C 런타임 패치 — blank 연속 억제**
RNN-T greedy decoder에서 연속 blank 토큰이 N회 이상 발생 시 같은 토큰 재방출을 억제하는 패치. `0004-rnnt-blank-suppression.patch`로 추가.

Phase 1 수정 후 실험적 검증을 통해 옵션 선택.

---

## Tech Stack

- **C runtime:** kdrkdrkdr/nemotron-asr-streaming.c (pinned, with vendored patches)
- **Python bridge:** ctypes over `libnemotron_asr.so`
- **Protocol:** Wyoming (`transcript-chunk` 이벤트 + `Transcript` 이벤트)
- **C stream API (이미 존재):**
  - `nemo_encoder_forward_chunks` — mel → encoder 청크 콜백
  - `nemo_rnnt_stream_accept` — 인코더 프레임 → RNN-T 디코더
  - `nemo_rnnt_stream_text` — 현재 partial 텍스트

---

## Commands

```bash
# Build
cd nemotron-asr-c && docker build .

# Lint
python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_nemotron_asr_c/*.py')]"
yamllint config.yaml translations/*.yaml
shellcheck rootfs/etc/s6-overlay/s6-rc.d/nemotron-asr-c/run

# Unit test (Phase 1 검증)
pytest tests/ -v

# Smoke
echo '{"type":"describe"}' | nc -w 1 localhost 10370 | grep -qi nemotron

# Streaming smoke — transcript-chunk 이벤트 확인
python3 -c "
import socket, json, struct, time
s = socket.create_connection(('localhost', 10370))
# AudioStart
s.sendall(json.dumps({'type':'audio-start','data':{'rate':16000,'width':2,'channels':1}}).encode() + b'\n')
# 청크 전송 후 transcript-chunk 수신 여부 확인
..."
```

---

## Project Structure

```
nemotron-asr-c/
  wyoming_nemotron_asr_c/
    engine.py     CHANGE: _mel_done 사용, 새 프레임만 feed
    handler.py    CHANGE: 스트리밍 모드 (stream 생성 on AudioStart, feed on AudioChunk)
    const.py      CHANGE: supports_transcript_streaming=True
  patches/
    0001-shared-lib.patch          # unchanged
    0002-set-att-right.patch       # unchanged
    0003-rnnt-hotword-biasing.patch  # unchanged
    0004-rnnt-blank-suppression.patch  # NEW, if Phase 3 Option B needed
  specs/
    hotword-boost.md               # existing
    true-streaming.md              # this file
  tests/
    test_engine.py   CHANGE: 스트리밍 동작 검증 추가
```

---

## Code Style

기존 `engine.py`/`handler.py`와 동일한 패턴. C 패치는 upstream 스타일 준수.

---

## Testing Strategy

### Unit (tests/test_engine.py)

```python
def test_incremental_mel_no_repeat():
    """accept_audio() 여러 번 호출 시 text()가 반복 없이 성장해야 함."""
    stream = mock_engine.create_stream()
    samples_1 = np.zeros(8000, dtype=np.float32)   # 0.5s silence
    samples_2 = np.random.randn(8000).astype(np.float32) * 0.01
    stream.accept_audio(samples_1)
    text_after_1 = stream.text()
    stream.accept_audio(samples_2)
    text_after_2 = stream.text()
    # 두 번째 호출 후 텍스트가 반복 패턴 없이 첫 번째보다 길거나 같아야 함
    assert text_after_2.count("<ko-KR>") <= 1  # 루핑 아티팩트 없음
    stream.close()

def test_mel_done_advances():
    """_mel_done이 각 accept_audio() 후 증가해야 함."""
    stream = mock_engine.create_stream()
    stream.accept_audio(np.zeros(8000, dtype=np.float32))
    assert stream._mel_done > 0
    prev = stream._mel_done
    stream.accept_audio(np.zeros(4000, dtype=np.float32))
    assert stream._mel_done > prev
    stream.close()
```

### Integration

실제 `.bin` 모델 없이는 완전한 통합 테스트 불가. HA 음성 파이프라인에서 실제 발화를 통해 검증:
1. "오늘 날씨 어때" 발화 → `transcript-chunk` 이벤트 수신 시간 측정
2. 최종 `Transcript` 가 반복 없는 정확한 텍스트인지 확인
3. Buffered 모드(Phase 1만 적용)와 Streaming 모드(Phase 1+2)의 WER 비교

---

## Boundaries

**Always:**
- `_mel_done`을 매 `accept_audio()` 후 반드시 업데이트
- `_feed_encoder()`에 슬라이싱된 new_mel 전달 (전체 아님)
- `stream.close()`를 `AudioStop` 핸들러의 finally에서 호출
- `transcript-chunk` 이벤트는 text가 실제로 변경된 경우에만 발송
- 기존 buffered 모드 대비 최종 Transcript 정확도 비교 테스트

**Ask first:**
- Phase 3 옵션 선택 (Python 최소 청크 vs C 패치) — 실험 결과 보고 결정
- `_ASR_LOCK`을 `AudioChunk`마다 잡는 방식의 변경 (현재 구조상 병렬 스트림은 없음)
- Wyoming `transcript-chunk` 이벤트 형식 표준과의 호환성

**Never:**
- `_mel_done` 없이 전체 mel 재투입 (이게 버그 원인)
- `handler.py`에서 스트림 객체를 핸들러 간 공유
- `nemo_rnnt_stream_free` / `nemo_encoder_stream_free` 누락 (메모리 누수)

---

## Open Questions

1. **Phase 3 필요 여부** — Phase 1 수정 후 160ms 이하 청크에서 루핑이 남아 있는지 실험 필요. `att_right` 값과 관련 있을 수 있음.

2. **`_ASR_LOCK`을 AudioChunk마다 잡는 비용** — C 추론이 GIL을 잡지 않는다면 asyncio 이벤트 루프 블로킹 위험. `run_in_executor`로 스레드 풀에서 실행하므로 OK이지만 확인 필요.

3. **Wyoming `transcript-chunk` 이벤트 형식** — wyoming 프로토콜에서 partial result 이벤트의 표준 키가 `"text"`인지 확인 필요.

---

## Risks

- **att_right와 chunk 크기의 관계:** 청크가 너무 작으면 인코더의 right-context가 부족해 정확도 저하. Phase 2에서 HA가 보내는 청크 크기(HA VAD가 ~80ms 청크 사용)를 확인하고 필요 시 최소 버퍼 추가.
- **`_mel_done` 슬라이싱의 mel 경계 정확도:** mel 스펙트로그램은 오버래핑 윈도우를 사용하므로 전체 오디오로 계산 후 새 프레임만 슬라이싱하는 방식이 정확함 (현재 코드도 이렇게 되어 있음).

---

## Resolution (implemented)

Phase 1/2의 delta-slicing 접근(#147)은 **잘못된 진단**이었다. 실제 근본 원인은 더 깊었다:

- 브리지가 C 런타임의 **stateful 스트리밍 API를 전혀 쓰지 않았다.** `engine.py`는
  매 청크마다 one-shot `nemo_mel_spectrogram`으로 전체 mel을 재계산하고
  `nemo_encoder_forward_chunks`를 호출했는데, 이 함수는 **호출마다 인코더 스트림을
  새로 만들고 해제**하는 래퍼다(`nemotron_asr_encoder.c:567`). 따라서 conformer
  left-context가 매번 사라져, delta 프레임만 받은 인코더가 chunk를 채우지 못해
  **출력이 비고(빈 transcript)**, 전체 mel 재계산이 **O(n²)로 폭발(RTF 8.66)**했다.
- upstream은 이미 완전한 3단 stateful 캐스케이드를 제공한다:
  `nemo_mel_stream_*` → `nemo_encoder_stream_*` → `nemo_rnnt_stream_*`
  (참조 소비자: `mic.c`의 `live_asr_accept`).

**Phase 3은 C 패치 불필요.** 수정은 전부 Python:
- `engine.py` `NemoCStream`이 세 스트림을 영속 생성하고, `accept_audio()`는 **새 PCM
  샘플만** `nemo_mel_stream_accept(final=0)`에 투입. mel→encoder→rnnt 콜백이 연쇄.
  `finalize()`는 `nemo_mel_stream_accept(final=1)`로 flush 후 `nemo_rnnt_stream_finish`.
- `handler.py`는 `TranscriptChunk.text`를 **delta**로 전송(누적 아님).
- `0004-rnnt-blank-suppression.patch`는 **만들지 않았다** (불필요).
- `tests/test_engine.py`는 캐스케이드 배선·delta 샘플 투입을 검증하도록 재작성.
