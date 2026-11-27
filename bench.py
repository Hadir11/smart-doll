import asyncio, time
import numpy as np
from faster_whisper import WhisperModel
import audio

async def main():
    pcm = await audio.tts_pcm("Bonjour ! Combien font trois plus quatre ?")
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0

    for name in ["base", "small"]:
        m = WhisperModel(name, device="cpu", compute_type="int8")
        for i in range(3):
            t = time.time()
            segs, _ = m.transcribe(x, language="fr", beam_size=1, vad_filter=False)
            txt = " ".join(s.text.strip() for s in segs)
            print(f"{name} run {i+1}: {time.time()-t:.1f}s -> {txt}")

    for i in range(3):
        t = time.time()
        await audio.tts_pcm("Super ! Trois plus quatre font sept.")
        print(f"TTS run {i+1}: {time.time()-t:.1f}s")

asyncio.run(main())