import argparse
import asyncio
import os
import subprocess
import tempfile
import time
import wave

import aiomqtt
from dotenv import load_dotenv

import audio

load_dotenv()
HOST = os.environ.get("MQTT_HOST", "localhost")
PASSWORD = os.environ["DOLL_MQTT_PASS"]
DOLL = "doll1"
CHUNK = 1024
rx = bytearray()
last_rx = 0.0
playing = False


async def receiver(client):
    global last_rx
    async for msg in client.messages:
        topic = str(msg.topic)
        if topic.endswith("audio/down"):
            rx.extend(msg.payload)
            last_rx = time.time()
        elif topic.endswith("cmd"):
            print("   [command]", msg.payload.decode())


async def player():
    global playing
    while True:
        await asyncio.sleep(0.2)
        if rx and time.time() - last_rx > 1.0:
            pcm = bytes(rx)
            rx.clear()
            playing = True
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                with wave.open(f.name, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(16000)
                    w.writeframes(pcm)
            print(f"   [playing {len(pcm) / 32000:.1f}s of audio]")
            await (await asyncio.create_subprocess_exec("afplay", f.name)).wait()
            os.unlink(f.name)
            playing = False


async def send_text(client, text):
    pcm = await audio.tts_pcm(text)
    for i in range(0, len(pcm), CHUNK):
        await client.publish(f"doll/{DOLL}/audio/up", pcm[i:i + CHUNK])
        await asyncio.sleep(0.02)
    for _ in range(45):                                   # silence, so the server detects the end
        await client.publish(f"doll/{DOLL}/audio/up", bytes(CHUNK))
        await asyncio.sleep(0.02)


async def typed_mode(client):
    while True:
        text = await asyncio.to_thread(input, "You > ")
        if text.strip():
            await send_text(client, text)


async def mic_mode(client):
    import sounddevice as sd
    loop = asyncio.get_running_loop()
    q = asyncio.Queue()

    def callback(indata, frames, t, status):
        if not playing:
            loop.call_soon_threadsafe(q.put_nowait, bytes(indata))

    print("Listening on the microphone. Use headphones, or the doll will hear herself.")
    with sd.RawInputStream(samplerate=16000, channels=1, dtype="int16",
                           blocksize=512, callback=callback):
        while True:
            await client.publish(f"doll/{DOLL}/audio/up", await q.get())


async def main(use_mic):
    async with aiomqtt.Client(HOST, 1883, username="doll1", password=PASSWORD) as client:
        await client.subscribe(f"doll/{DOLL}/audio/down")
        await client.subscribe(f"doll/{DOLL}/cmd")
        await client.publish(f"doll/{DOLL}/status", "online", retain=True)
        tasks = [receiver(client), player(), mic_mode(client) if use_mic else typed_mode(client)]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mic", action="store_true", help="use the real microphone")
    asyncio.run(main(ap.parse_args().mic))