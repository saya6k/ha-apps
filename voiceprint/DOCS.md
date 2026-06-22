# Home Assistant Add-on: Voiceprint

## How it works

```text
HA Assist ──► Voiceprint (this add-on, :10350) ──► your STT (:10300)
```

Audio chunks are forwarded to the upstream STT **as they arrive**, so
streaming recognizers keep their low latency. While the upstream decodes,
the add-on computes a speaker embedding of the same audio and compares it
to your enrolled voiceprints. If no enrolled speaker matches, the upstream's
transcript is replaced with an empty one — Home Assistant treats it as
"didn't catch that" and nothing executes.

## Setup

1. Configure `upstream_uri` to point at your STT add-on
   (e.g. `tcp://03f32180-nemo-asr-cpp:10360`).
2. In **Settings → Devices & Services → Wyoming Protocol**, add this add-on
   (port 10350) and select it as the STT engine of your Assist pipeline.
   The upstream STT stays installed but is no longer used directly.

## Enrolling speakers

Create one folder per speaker under `/share/voiceprint/` and put WAV
recordings of that person inside:

```text
/share/voiceprint/
  john/
    clip-01.wav
    clip-02.wav
    ...
```

- 5–10 clips of a few seconds each work well; more and varied (distance,
  volume, time of day) is better.
- Best results come from recording with the **same microphone** you use for
  Assist (e.g. your voice satellite).
- 16 kHz mono 16-bit WAV is ideal; other rates and stereo are converted
  automatically.
- Restart the add-on after adding or changing clips.

If no voiceprints are enrolled, the add-on passes everything through
unverified and logs a warning.

## Options

| Option | Default | Description |
|---|---|---|
| `upstream_uri` | `tcp://03f32180-nemo-asr-cpp:10360` | Wyoming STT service to forward audio to (the downstream ASR) |
| `threshold` | `0.5` | Cosine similarity required to accept a speaker |
| `require_match` | `true` | Reject unmatched audio (empty transcript) |
| `tag_speaker` | `false` | Prefix transcripts with `[speaker]` |
| `capture` | `false` | Save each utterance to `/share/voiceprint/_captures` for in-domain enrollment |
| `debug_logging` | `false` | Log per-speaker similarity scores |

The advertised languages are always **mirrored from the downstream ASR**
(`upstream_uri`) — there is no language option to set.

### Proxy not selectable as STT?

Home Assistant only offers an STT engine to a pipeline when the engine
advertises the pipeline's language. The proxy mirrors the downstream ASR's
language list, so make sure that ASR is running and advertises your
language. If it was down when HA last asked, start it, restart this add-on,
then **reload the Wyoming integration entry** for this add-on (Settings →
Devices & Services) — HA caches the list from when the entry was set up.

### Tuning the threshold

Enable `debug_logging` and speak a few commands: your own commands should
score well above 0.5, other voices well below. If your commands are
rejected, lower the threshold (or add more enrollment clips from the actual
satellite microphone); if someone else's voice gets through, raise it.

`tag_speaker` prepends the matched name, e.g. `[john] turn on the lights` —
useful in automations, but note intent matching then sees the prefix too.
