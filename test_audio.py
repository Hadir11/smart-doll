import asyncio, time
import audio

async def main():
    t = time.time()
    pcm = await audio.tts_pcm("Bonjour ! Combien font trois plus quatre ?")
    print(f"TTS: {len(pcm)/32000:.1f}s of audio in {time.time()-t:.1f}s")

    t = time.time()
    audio.get_model()
    print(f"Model load: {time.time()-t:.1f}s (first run also downloads it)")

    t = time.time()
    print("STT heard:", audio.transcribe(pcm), f"({time.time()-t:.1f}s)")

asyncio.run(main())