"""Catan web app server (scaffold).

Isolated FastAPI app. Serves the thin client and exposes a temporary WebSocket
echo endpoint so end to end connectivity can be verified before any game logic
exists. No game rules live here yet. The echo handler is replaced by the real
game protocol in a later phase.

Run from the repository root:
    uvicorn catan_web.server:app --host 0.0.0.0 --port 8000 --reload
"""
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).parent / "web"

app = FastAPI(title="Catan Web (scaffold)")

# Serve static assets (js, css, images) from the web folder.
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the thin client entry page."""
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.websocket("/ws")
async def ws_echo(websocket: WebSocket) -> None:
    """Temporary echo endpoint.

    Accepts a connection and echoes back any text message. This will be
    replaced by the real game protocol (join, start, action, state, error)
    in the networking phase.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")
    except WebSocketDisconnect:
        return
