import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.core.brain import JarvisBrain
from src.voice.piper_tts import tts

app = FastAPI()

# Enable CORS for local webview & browser connections
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

# Global Brain Instance
brain = None

def get_brain():
    global brain
    if brain is None:
        print("[SERVER] Lazy loading JarvisBrain...")
        brain = JarvisBrain()
    return brain

# ── Health check endpoint ─────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ── Serve index.html at root ──────────────────────────────────────────
@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ── Echo Show terminal ────────────────────────────────────────────────
@app.get("/echo")
async def echo():
    return FileResponse(os.path.join(ECHO_DIR, "index.html"))

@app.get("/echo/style.css")
async def echo_css():
    return FileResponse(os.path.join(ECHO_DIR, "style.css"), media_type="text/css")

@app.get("/echo/script.js")
async def echo_js():
    return FileResponse(os.path.join(ECHO_DIR, "script.js"), media_type="application/javascript")

# ── Serve static files & audio ────────────────────────────────────────
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

# ── WebSocket ─────────────────────────────────────────────────────────
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
            if not user_text:
                continue

            print(f"[UI] User: {user_text}")

            # Notify: thinking
            await websocket.send_text(json.dumps({
                "type": "status",
                "status": "thinking",
                "text": "JARVIS is Thinking..."
            }))

            # Run brain in thread pool so we never block the async loop
            loop = asyncio.get_event_loop()
            try:
                answer = await loop.run_in_executor(None, active_brain.respond, user_text)
            except Exception as e:
                answer = f"Entschuldigung, Sir. Ein Fehler ist aufgetreten: {e}"

            print(f"[UI] JARVIS: {answer}")

            # Generate Piper TTS audio with Thorsten voice
            audio_filename = None
            if tts.is_available():
                audio_filename = await loop.run_in_executor(None, tts.synthesize, answer)

            audio_url = f"/audio/{audio_filename}" if audio_filename else None

            # Send response with optional Piper audio_url
            await websocket.send_text(json.dumps({
                "type": "message",
                "text": answer,
                "audio_url": audio_url
            }))

    except WebSocketDisconnect:
        print("[UI] Client disconnected.")
    except Exception as e:
        print(f"[UI] WebSocket error: {e}")


def start_server():
    print("=" * 50)
    print("  JARVIS V3 — UI Server")
    print("=" * 50)
    print("  PC:   http://127.0.0.1:8000")
    print("  LAN:  http://<PC-IP>:8000")
    print("  Echo: http://<PC-IP>:8000/echo")
    print("=" * 50)
    # Pre-initialize brain
    get_brain()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    start_server()
