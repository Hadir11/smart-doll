import asyncio
import io
import os
import wave

import edge_tts
import imageio_ffmpeg
import numpy as np
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from openai import OpenAI

load_dotenv()

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VOICE = "fr-FR-EloiseNeural"          # alternative: fr-FR-DeniseNeural

STT_BACKEND = os.environ.get("STT_BACKEND", "groq")
STT_MODEL = os.environ.get("STT_MODEL", "whisper-large-v3-turbo")
HINT = "Leçon pour enfants : chiffres, additions, couleurs, lettres, animaux."

_local_model = None
_stt_client = None


# ---------- speech to text ----------
def _wav_bytes(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)
    return buf.getvalue()


def transcribe_cloud(pcm: bytes) -> str:
    global _stt_client
    if _stt_client is None:
        _stt_client = OpenAI(api_key=os.environ["LLM_API_KEY"],
                             base_url=os.environ["LLM_BASE_URL"])
    r = _stt_client.audio.transcriptions.create(
        file=("speech.wav", _wav_bytes(pcm)), model=STT_MODEL,
        language="fr", prompt=HINT)
    return r.text.strip()


def get_model():
    global _local_model
    if _local_model is None:
        _local_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _local_model


def transcribe_local(pcm: bytes) -> str:
    x = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segs, _ = get_model().transcribe(x, language="fr", beam_size=1,
                                     vad_filter=False, initial_prompt=HINT)
    return " ".join(s.text.strip() for s in segs).strip()


def transcribe(pcm: bytes) -> str:
    if STT_BACKEND == "groq":
        try:
            return transcribe_cloud(pcm)
        except Exception as e:
            print(f"Cloud STT failed ({e}), falling back to local")
    return transcribe_local(pcm)


# ---------- text to speech ----------
async def tts_pcm(text: str) -> bytes:
    """Text -> 16 kHz, 16-bit, mono raw PCM (the format the ESP32 plays)."""
    mp3 = b""
    async for chunk in edge_tts.Communicate(text, VOICE).stream():
        if chunk["type"] == "audio":
            mp3 += chunk["data"]
    proc = await asyncio.create_subprocess_exec(
        FFMPEG, "-loglevel", "error", "-i", "pipe:0",
        "-f", "s16le", "-ar", "16000", "-ac", "1", "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
    out, _ = await proc.communicate(mp3)
    return out