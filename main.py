import os
import asyncio
from contextlib import asynccontextmanager

import aiomqtt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

import db
import voice
from auth import current_parent
from routes import router

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "server"
MQTT_PASS = os.environ["MQTT_PASS"]

mqtt_client = None


async def handle_message(message):
    parts = str(message.topic).split("/")
    doll_id = parts[1]
    kind = "/".join(parts[2:])

    if kind == "audio/up":
        await voice.on_audio(mqtt_client, doll_id, message.payload)
    elif kind in ("event", "status"):
        text = message.payload.decode(errors="ignore")
        print(f"[{doll_id}] {kind}: {text}")
        asyncio.create_task(asyncio.to_thread(db.log_event, doll_id, kind, text))


async def mqtt_loop():
    global mqtt_client
    while True:
        try:
            async with aiomqtt.Client(MQTT_HOST, MQTT_PORT,
                                      username=MQTT_USER, password=MQTT_PASS) as client:
                mqtt_client = client
                print("MQTT connected")
                await client.subscribe("doll/+/audio/up")
                await client.subscribe("doll/+/event")
                await client.subscribe("doll/+/status")
                async for message in client.messages:
                    await handle_message(message)
        except aiomqtt.MqttError as e:
            mqtt_client = None
            print(f"MQTT error: {e}. Retrying in 3s...")
            await asyncio.sleep(3)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(db.init_db)
    asyncio.create_task(voice.init())
    task = asyncio.create_task(mqtt_loop())
    yield
    task.cancel()


app = FastAPI(title="Smart Doll", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True, "mqtt_connected": mqtt_client is not None}


@app.get("/events")
def list_events(limit: int = 50):
    return db.fetch_all("SELECT * FROM events ORDER BY id DESC LIMIT %s", (limit,))


@app.post("/doll/{doll_id}/led/{color}")
async def set_led(doll_id: str, color: str, pid: int = Depends(current_parent)):
    if mqtt_client is None:
        raise HTTPException(503, "MQTT not connected")
    await mqtt_client.publish(f"doll/{doll_id}/cmd",
                              f'{{"type":"led","color":"{color}"}}', qos=1)
    return {"sent": True}


@app.post("/doll/{doll_id}/start")
async def start_lesson(doll_id: str, topic_id: int | None = None, pid: int = Depends(current_parent)):
    if mqtt_client is None:
        raise HTTPException(503, "MQTT not connected")
    if not db.fetch_one("SELECT id FROM children WHERE doll_id=%s AND parent_id=%s", (doll_id, pid)):
        raise HTTPException(404, "No child of yours is linked to this doll")
    if topic_id and not db.fetch_one("SELECT id FROM topics WHERE id=%s AND parent_id=%s", (topic_id, pid)):
        raise HTTPException(404, "Topic not found")
    return {"started": await voice.start_now(mqtt_client, doll_id, topic_id)}