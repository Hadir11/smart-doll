import asyncio, time
import audio

async def main():
    pcm = await audio.tts_pcm("Bonjour ! Combien font trois plus quatre ?")
    for i in range(3):
        t = time.time()
        txt = audio.transcribe(pcm)
        print(f"run {i+1}: {time.time()-t:.1f}s -> {txt}")

asyncio.run(main())