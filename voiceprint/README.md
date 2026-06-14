# Home Assistant Add-on: Voiceprint

A speaker-verifying Wyoming STT proxy. It sits between Home Assistant and
your speech-to-text service, streams audio through unchanged, and checks the
voice against enrolled voiceprints in parallel — commands from voices you
haven't enrolled (a TV, a guest, an ad) come back as an empty transcript and
never execute. Speaker embeddings run on-device via a CAM++ model
([3D-Speaker](https://github.com/modelscope/3D-Speaker), Apache 2.0) on the
LiteRT runtime.

Enroll a speaker by dropping a few WAV recordings into
`/share/voiceprint/<name>/` and restarting the add-on.
