import asyncio
import json
import os
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

from src.core.brain import JarvisBrain
from src.voice.piper_tts import tts

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
ECHO_DIR = os.path.join(STATIC_DIR, "echo")
os.makedirs(AUDIO_DIR, exist_ok=True)

brain = None


def get_brain():
    global brain
    if brain is None:
        print("[SERVER] Lazy loading JarvisBrain...")
        brain = JarvisBrain()
    return brain


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/echo")
async def echo():
    return FileResponse(os.path.join(ECHO_DIR, "index.html"))


@app.get("/echo/style.css")
async def echo_css():
    return FileResponse(os.path.join(ECHO_DIR, "style.css"), media_type="text/css")


@app.get("/echo/script.js")
async def echo_js():
    return FileResponse(os.path.join(ECHO_DIR, "script.js"), media_type="application/javascript")


@app.get("/style.css")
async def css():
    return FileResponse(os.path.join(STATIC_DIR, "style.css"), media_type="text/css")


@app.get("/script.js")
async def js():
    return FileResponse(os.path.join(STATIC_DIR, "script.js"), media_type="application/javascript")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    return {"error": "Audio file not found"}


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[UI] Client connected.")

    try:
        active_brain = get_brain()

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            user_text = data.get("text", "").strip()
            tts_requested = bool(data.get("tts", True))
            if not user_text:
                continue

            request_started = time.perf_counter()
            print(f"[UI] User: {user_text}")

            await websocket.send_text(json.dumps({
                "type": "status",
                "status": "thinking",
                "text": "JARVIS is Thinking...",
            }))

            loop = asyncio.get_running_loop()
            llm_started = time.perf_counter()

            try:
                answer = await loop.run_in_executor(
                    None,
                    active_brain.respond,
                    user_text,
                )
            except Exception as error:
                answer = f"Entschuldigung, Sir. Ein Fehler ist aufgetreten: {error}"

            llm_seconds = time.perf_counter() - llm_started
            print(f"[UI] JARVIS: {answer}")
            print(f"[PERF] LLM: {llm_seconds:.2f}s")

            # Send the text immediately. The browser no longer waits for TTS
            # generation before showing the answer.
            await websocket.send_text(json.dumps({
                "type": "message",
                "text": answer,
                "audio_url": None,
                "tts_pending": tts_requested,
                "timing": {
                    "llm_seconds": round(llm_seconds, 3),
                    "tts_seconds": 0.0,
                    "total_seconds": round(time.perf_counter() - request_started, 3),
                },
            }))

            if not tts_requested:
                await websocket.send_text(json.dumps({
                    "type": "audio",
                    "text": answer,
                    "audio_url": None,
                    "timing": {
                        "llm_seconds": round(llm_seconds, 3),
                        "tts_seconds": 0.0,
                        "total_seconds": round(time.perf_counter() - request_started, 3),
                    },
                }))
                continue

            await websocket.send_text(json.dumps({
                "type": "status",
                "status": "speaking",
                "text": "JARVIS is Speaking...",
            }))

            audio_filename = None
            tts_seconds = 0.0

            if tts.is_available():
                tts_started = time.perf_counter()
                audio_filename = await loop.run_in_executor(
                    None,
                    tts.synthesize,
                    answer,
                )
                tts_seconds = time.perf_counter() - tts_started
                print(f"[PERF] TTS: {tts_seconds:.2f}s")
            else:
                print("[TTS] Provider unavailable; browser fallback will be used.")

            audio_url = f"/audio/{audio_filename}" if audio_filename else None
            total_seconds = time.perf_counter() - request_started
            print(f"[PERF] Total: {total_seconds:.2f}s")

            await websocket.send_text(json.dumps({
                "type": "audio",
                "text": answer,
                "audio_url": audio_url,
                "timing": {
                    "llm_seconds": round(llm_seconds, 3),
                    "tts_seconds": round(tts_seconds, 3),
                    "total_seconds": round(total_seconds, 3),
                },
            }))

    except WebSocketDisconnect:
        print("[UI] Client disconnected.")
    except Exception as error:
        print(f"[UI] WebSocket error: {error}")


def start_server():
    print("=" * 50)
    print("  JARVIS V3 — UI Server")
    print("=" * 50)
    print("  PC:   http://127.0.0.1:8000")
    print("  LAN:  http://<PC-IP>:8000")
    print("  Echo: http://<PC-IP>:8000/echo")
    print("=" * 50)
    get_brain()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    start_server()
