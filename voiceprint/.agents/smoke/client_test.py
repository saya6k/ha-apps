"""Stream a WAV through the voiceprint proxy and print the transcript."""
import asyncio
import sys
import wave

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncClient

CHUNK_SAMPLES = 1024


async def main(path: str, uri: str = "tcp://127.0.0.1:10350") -> None:
    with wave.open(path, "rb") as wav:
        rate, width, channels = wav.getframerate(), wav.getsampwidth(), wav.getnchannels()
        frames = wav.readframes(wav.getnframes())

    client = AsyncClient.from_uri(uri)
    await client.connect()
    await client.write_event(Transcribe(language="en").event())
    await client.write_event(AudioStart(rate=rate, width=width, channels=channels).event())
    step = CHUNK_SAMPLES * width * channels
    for i in range(0, len(frames), step):
        await client.write_event(
            AudioChunk(rate=rate, width=width, channels=channels,
                       audio=frames[i:i + step]).event()
        )
    await client.write_event(AudioStop().event())
    while True:
        event = await client.read_event()
        if event is None:
            print("CONNECTION CLOSED WITHOUT TRANSCRIPT")
            break
        if Transcript.is_type(event.type):
            print(f"TRANSCRIPT: {Transcript.from_event(event).text!r}")
            break
    await client.disconnect()


asyncio.run(main(sys.argv[1], *sys.argv[2:]))
