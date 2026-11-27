import os
import asyncio
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from routes import router
import aiomqtt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(title="Smart Doll", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

import db

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "server"
MQTT_PASS = os.environ["MQTT_PASS"]

mqtt_client = None
audio_received = {}


async def handle_message(message):
    parts = str(message.topic).split("/")
    doll_id = parts[1]
    kind = "/".join(parts[2:])
    payload_text = message.payload.decode(errors="ignore") if kind != "audio/up" else ""

    if kind == "audio/up":
        audio_received[doll_id] = audio_received.get(doll_id, 0) + len(message.payload)
    elif kind == "event":
        print(f"[{doll_id}] event: {payload_text}")
        await asyncio.to_thread(db.log_event, doll_id, "event", payload_text)
    elif kind == "status":
        print(f"[{doll_id}] status: {payload_text}")
        await asyncio.to_thread(db.log_event, doll_id, "status", payload_text)


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
    task = asyncio.create_task(mqtt_loop())
    yield
    task.cancel()


app = FastAPI(title="Smart Doll", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True, "mqtt_connected": mqtt_client is not None}


@app.get("/events")
def list_events(limit: int = 50):
    return db.fetch_all("SELECT * FROM events ORDER BY id DESC LIMIT %s", (limit,))


@app.post("/doll/{doll_id}/led/{color}")
async def set_led(doll_id: str, color: str):
    if mqtt_client is None:
        raise HTTPException(503, "MQTT not connected")
    await mqtt_client.publish(f"doll/{doll_id}/cmd",
                              f'{{"type":"led","color":"{color}"}}', qos=1)
    return {"sent": True}