"""Catan web app server.

Serves the thin client and the image assets, exposes the asset manifest, and
provides a temporary WebSocket echo endpoint that the real game protocol
replaces in a later phase.

Run from the repository root:
    uvicorn catan_web.server:app --host 127.0.0.1 --port 8000 --reload
"""
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from catan_web import assets_manifest

WEB_DIR = Path(__file__).parent / "web"
ASSETS_DIR = Path(__file__).parent / "assets" / "imgs"

app = FastAPI(title="Catan Web")

# Serve the thin client files and the game image assets as static content.
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
def index() -> FileResponse:
    """Serve the thin client entry page."""
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.get("/manifest.json")
def manifest() -> JSONResponse:
    """Asset manifest the frontend uses to locate images."""
    return JSONResponse(assets_manifest.manifest())


@app.websocket("/ws")
async def ws_echo(websocket: WebSocket) -> None:
    """Temporary echo endpoint, replaced by the game protocol later."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")
    except WebSocketDisconnect:
        return
