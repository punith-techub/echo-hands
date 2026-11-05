"""
ECHOHANDS 5.0 - Vercel Serverless Entrypoint
Serves the web portal, Echo-Hands meeting simulator, Manifest V3 extension download,
reverse ISL compiler, and AI verification on Vercel cloud.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

STATIC_DIR = os.path.join(BASE_DIR, "static")
EXTENSION_DIR = os.path.join(BASE_DIR, "extension")

try:
    # Attempt to load full app if torch/cv2 are available
    from CORE.app import app
except Exception as err:
    # Graceful lightweight serverless fallback for Vercel without heavy torch
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import Optional
    import io
    import zipfile
    from CORE.sentence_synthesizer import SentenceSynthesizer
    from CORE.speech_engine import SpeechEngine

    app = FastAPI(
        title="ECHOHANDS ISL Serverless Engine",
        description="Vercel Cloud Serverless Entrypoint",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if os.path.exists(STATIC_DIR):
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    if os.path.exists(EXTENSION_DIR):
        app.mount("/extension", StaticFiles(directory=EXTENSION_DIR), name="extension")

    synthesizer = SentenceSynthesizer()
    speech_engine = SpeechEngine()

    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        idx_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(idx_path):
            with open(idx_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse("<h1>ECHOHANDS Vercel Active</h1>")

    @app.get("/echo-hands.crx")
    @app.get("/api/install-extension")
    async def install_extension_crx():
        if not os.path.exists(EXTENSION_DIR):
            raise HTTPException(status_code=404, detail="Extension directory not found.")
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(EXTENSION_DIR):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, EXTENSION_DIR)
                    zf.write(abs_path, arcname=rel_path)
        mem_zip.seek(0)
        return StreamingResponse(
            mem_zip,
            media_type="application/x-chrome-extension",
            headers={"Content-Disposition": "attachment; filename=echo-hands.crx"}
        )

    @app.get("/api/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": "Vercel Serverless Cloud",
            "version": "1.0.0"
        }

    class TextToIslRequest(BaseModel):
        text: str
        lang: Optional[str] = "auto"

    @app.post("/api/text-to-isl")
    async def compile_text_to_isl(req: TextToIslRequest):
        if not req.text or not req.text.strip():
            raise HTTPException(status_code=400, detail="Text field cannot be empty.")
        return synthesizer.text_to_isl_gloss(req.text)

    # In-memory real-time meeting room event store for cross-device sync
    ROOM_EVENTS = {}

    @app.post("/api/room/{room_id}/event")
    async def post_room_event(room_id: str, payload: dict):
        if room_id not in ROOM_EVENTS:
            ROOM_EVENTS[room_id] = []
        ROOM_EVENTS[room_id].append(payload)
        if len(ROOM_EVENTS[room_id]) > 50:
            ROOM_EVENTS[room_id] = ROOM_EVENTS[room_id][-50:]
        return {"status": "dispatched", "room_id": room_id}

    @app.get("/api/room/{room_id}/events")
    async def get_room_events(room_id: str, since: float = 0):
        events = ROOM_EVENTS.get(room_id, [])
        new_events = [e for e in events if e.get("timestamp", 0) > since]
        return {"room_id": room_id, "events": new_events}

    @app.get("/api/download-extension")
    async def download_extension_zip():
        if not os.path.exists(EXTENSION_DIR):
            raise HTTPException(status_code=404, detail="Extension directory not found.")
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(EXTENSION_DIR):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, EXTENSION_DIR)
                    zf.write(abs_path, arcname=rel_path)
        mem_zip.seek(0)
        return StreamingResponse(
            mem_zip,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=echohands-isl-extension.zip"}
        )
