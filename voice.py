import asyncio
import random
import time
import traceback
from collections import deque

import numpy as np

import audio
import db
import llm

RMS_THRESHOLD = 500          # speech loudness threshold; calibrate on the real hardware
SILENCE_CHUNKS = 25          # 25 chunks x 32 ms = 0.8 s of silence ends a sentence
MIN_UTTERANCE_BYTES = 8000  # ignore sounds shorter than 0.5/2 s
MAX_UTTERANCE_BYTES = 32000 * 10
PRE_ROLL = 5                 # keep the last chunks so the start of a word isn't cut
QUESTIONS_PER_SESSION = 5

GREETINGS = ("bonjour", "salut", "coucou", "hello", "allô", "allo")
STOPWORDS = ("stop", "arrête", "arrete", "au revoir", "j'arrête")
FILLERS = ["Hmm, voyons.", "Alors...", "D'accord !", "Je réfléchis."]
filler_audio = []

dolls = {}


class Doll:
    def __init__(self, doll_id):
        self.id = doll_id
        self.mode = "LISTENING"      # LISTENING or BUSY
        self.session = None
        self.buf = bytearray()
        self.pre = deque(maxlen=PRE_ROLL)
        self.speaking = False
        self.silence = 0

    def feed(self, chunk):
        chunk = chunk[: len(chunk) // 2 * 2]
        if not chunk:
            return None
        rms = float(np.sqrt(np.mean(np.frombuffer(chunk, np.int16).astype(np.float32) ** 2)))
        if rms > RMS_THRESHOLD:
            if not self.speaking:
                self.speaking = True
                self.buf = bytearray(b"".join(self.pre))
            self.buf += chunk
            self.silence = 0
        elif self.speaking:
            self.buf += chunk
            self.silence += 1
        else:
            self.pre.append(chunk)
            return None
        if self.silence > SILENCE_CHUNKS or len(self.buf) > MAX_UTTERANCE_BYTES:
            pcm = bytes(self.buf)
            self.buf = bytearray()
            self.speaking = False
            self.silence = 0
            return pcm if len(pcm) >= MIN_UTTERANCE_BYTES else None
        return None


# ---------- database helpers (run in threads) ----------
def start_session(doll_id, topic_id=None):
    child = db.get_child_by_doll(doll_id)
    if not child:
        return None
    topic = db.get_topic(topic_id) if topic_id else None
    if topic is None:
        topic = db.first_active_topic(child["parent_id"])
    if topic is None:
        return None
    return {"id": db.create_session(child["id"], topic["id"]), "child": child, "topic": topic,
            "level": db.get_level(child["id"], topic["id"]), "age": child["age"] or 6,
            "history": [], "last_question": None, "n": 0, "ok": 0, "ko": 0}


def save_turn(s, child_text, doll_text, attempt, final, level):
    if child_text:
        db.add_message(s["id"], "child", child_text)
    db.add_message(s["id"], "doll", doll_text)
    if attempt:
        db.add_attempt(s["id"], s["topic"]["id"], *attempt)
    if final:
        db.save_level(s["child"]["id"], s["topic"]["id"], level)
        db.end_session(s["id"])


def bg(fn, *args):
    async def run():
        try:
            await asyncio.to_thread(fn, *args)
        except Exception as e:
            print("DB error:", e)
    asyncio.create_task(run())


# ---------- teaching logic ----------
async def run_turn(d, child_text):
    s = d.session
    if s["last_question"] and any(w in child_text.lower() for w in STOPWORDS):
        d.session = None
        reply = "D'accord, on arrête ici. À bientôt !"
        bg(save_turn, s, child_text, reply, None, True, s["level"])
        return reply, None

    turn = await asyncio.to_thread(llm.teach_turn, s["topic"], s["level"], s["age"],
                                   s["history"], s["last_question"], child_text)
    ok = turn.get("is_correct")
    attempt = None
    if s["last_question"] is not None:
        s["n"] += 1
        if ok is not None:
            attempt = (s["last_question"], child_text, bool(ok), s["level"])
            if ok:
                s["ok"] += 1; s["ko"] = 0
                if s["ok"] >= 3 and s["level"] < 3:
                    s["level"] += 1; s["ok"] = 0
            else:
                s["ko"] += 1; s["ok"] = 0
                if s["ko"] >= 2 and s["level"] > 1:
                    s["level"] -= 1; s["ko"] = 0

    feedback = (turn.get("feedback") or "").strip()
    question = (turn.get("next_question") or "").strip()
    final = s["n"] >= QUESTIONS_PER_SESSION
    reply = f"{feedback} Bravo, la leçon est finie. À bientôt !" if final else f"{feedback} {question}".strip()

    s["history"] += [{"role": "user", "content": child_text}, {"role": "assistant", "content": reply}]
    s["last_question"] = None if final else question
    if final:
        d.session = None
    bg(save_turn, s, child_text, reply, attempt, final, s["level"])
    return reply, ok


# ---------- audio out ----------
async def send_audio(client, doll_id, pcm, tail=0.6):
    start = time.time()
    for i in range(0, len(pcm), 1024):
        await client.publish(f"doll/{doll_id}/audio/down", pcm[i:i + 1024])
        await asyncio.sleep(0.02)                       # pacing, so the ESP32 buffer doesn't overflow
    remaining = len(pcm) / 32000 - (time.time() - start)
    await asyncio.sleep(max(0, remaining) + tail)       # wait until playback is over


async def respond(client, d, child_text):
    filler = None
    if filler_audio:
        filler = asyncio.create_task(send_audio(client, d.id, random.choice(filler_audio), tail=0))
    t0 = time.time()
    reply, ok = await run_turn(d, child_text)
    t1 = time.time()
    pcm = await audio.tts_pcm(reply)
    print(f"[{d.id}] doll: {reply!r} (LLM {t1 - t0:.1f}s, TTS {time.time() - t1:.1f}s)")
    if filler:
        await filler
    if ok is not None:
        color = "green" if ok else "red"
        await client.publish(f"doll/{d.id}/cmd", f'{{"type":"led","color":"{color}"}}', qos=1)
    await send_audio(client, d.id, pcm)


async def process(client, d, pcm):
    try:
        t0 = time.time()
        text = await asyncio.to_thread(audio.transcribe, pcm)
        print(f"[{d.id}] child: {text!r} (STT {time.time() - t0:.1f}s)")
        if len(text.strip()) < 1:
            return
        if d.session is None:
            if not any(g in text.lower() for g in GREETINGS):
                return
            d.session = await asyncio.to_thread(start_session, d.id)
            if d.session is None:
                await send_audio(client, d.id, await audio.tts_pcm(
                    "Bonjour ! Demande à tes parents de choisir une leçon."))
                return
        await respond(client, d, text)
    except Exception:
        traceback.print_exc()
    finally:
        d.mode = "LISTENING"


# ---------- entry points used by main.py ----------
async def on_audio(client, doll_id, payload):
    d = dolls.setdefault(doll_id, Doll(doll_id))
    if d.mode != "LISTENING":
        return                                           # ignore the mic while the doll talks/thinks
    pcm = d.feed(payload)
    if pcm:
        d.mode = "BUSY"
        asyncio.create_task(process(client, d, pcm))


async def start_now(client, doll_id, topic_id=None):
    """Called by the parents' app: the doll starts a lesson by itself."""
    d = dolls.setdefault(doll_id, Doll(doll_id))
    if d.mode != "LISTENING" or d.session:
        return False
    d.mode = "BUSY"

    async def go():
        try:
            d.session = await asyncio.to_thread(start_session, doll_id, topic_id)
            if d.session:
                await respond(client, d, "")
        except Exception:
            traceback.print_exc()
        finally:
            d.mode = "LISTENING"
    asyncio.create_task(go())
    return True


async def init():
    for phrase in FILLERS:
        try:
            filler_audio.append(await audio.tts_pcm(phrase))
        except Exception as e:
            print("Filler TTS failed:", e)
    print(f"Voice ready ({len(filler_audio)} fillers)")