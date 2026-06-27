"""Catan web app server.

Serves the thin client and image assets, exposes the asset manifest and board
geometry, and runs the authoritative WebSocket game protocol. The endpoint is
thin glue over the RoomManager, which holds all game logic.
"""
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from catan_web import assets_manifest
from catan_web.engine.actions import IllegalAction
from catan_web.engine.board import Resource
from catan_web.engine.legal import Action, ActionType, victory_points
from catan_web.export.logger import log_action, write_meta
from catan_web.geometry import board_geometry
from catan_web.net import protocol as P
from catan_web.net.redact import legal_for, view_for_player
from catan_web.net.rooms import GameError, RoomManager

WEB_DIR = Path(__file__).parent / "web"
ASSETS_DIR = Path(__file__).parent / "assets" / "imgs"

app = FastAPI(title="Catan Web")
manager = RoomManager()

app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(WEB_DIR / "index.html"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/manifest.json")
def manifest() -> JSONResponse:
    return JSONResponse(assets_manifest.manifest())


@app.get("/geometry.json")
def geometry() -> JSONResponse:
    return JSONResponse(board_geometry())


def _parse_action(d: dict) -> Action:
    def res(name):
        v = d.get(name)
        return Resource(v) if v is not None else None

    return Action(
        type=ActionType(d["type"]),
        node=d.get("node"),
        edge=d.get("edge"),
        hex_id=d.get("hex_id"),
        victim=d.get("victim"),
        resource=res("resource"),
        give=res("give"),
        get=res("get"),
    )


async def _send_to(seat, obj):
    if seat.ws is not None and seat.connected:
        try:
            await seat.ws.send_json(obj)
        except Exception:
            seat.connected = False


async def _broadcast_lobby(room):
    payload = {
        "type": P.LOBBY,
        "room": room.code,
        "host": room.host,
        "started": room.started,
        "players": [
            {"seat": s.seat, "name": s.name, "connected": s.connected}
            for s in room.seats
        ],
    }
    for s in room.seats:
        await _send_to(s, payload)


async def _send_state_to(room, seat_no):
    s = room.seats[seat_no]
    await _send_to(s, {"type": P.STATE, "view": view_for_player(room, seat_no)})
    await _send_to(s, {"type": P.LEGAL, "actions": legal_for(room, seat_no)})


async def _broadcast_state(room):
    for s in room.seats:
        await _send_state_to(room, s.seat)


async def _broadcast_game_over(room):
    payload = {
        "type": P.GAME_OVER,
        "winner": room.state.winner,
        "final_vps": [victory_points(p) for p in room.state.players],
    }
    for s in room.seats:
        await _send_to(s, payload)


@app.websocket("/ws")
async def ws_game(websocket: WebSocket) -> None:
    await websocket.accept()
    code = None
    seat = None
    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            try:
                if mtype == P.CREATE:
                    room, s = manager.create(msg.get("name", "Player"), websocket)
                    code, seat = room.code, s.seat
                    await websocket.send_json(
                        {"type": P.JOINED, "room": room.code, "seat": s.seat, "token": s.token}
                    )
                    await _broadcast_lobby(room)
                elif mtype == P.JOIN:
                    room, s = manager.join(
                        msg.get("room", ""), msg.get("name", "Player"),
                        msg.get("token"), websocket,
                    )
                    code, seat = room.code, s.seat
                    await websocket.send_json(
                        {"type": P.JOINED, "room": room.code, "seat": s.seat, "token": s.token}
                    )
                    await _broadcast_lobby(room)
                    if room.started:
                        await _send_state_to(room, s.seat)
                elif mtype == P.START:
                    room = manager.start(code, seat)
                    await _broadcast_lobby(room)
                    await _broadcast_state(room)
                elif mtype == P.ACTION:
                    action = _parse_action(msg.get("action", {}))
                    room = manager.apply(code, seat, action)
                    try:
                        log_action(room.game_id, room.seq, seat, action, room.state)
                    except Exception:
                        pass
                    await _broadcast_state(room)
                    if room.state.phase.value == "game_over":
                        await _broadcast_game_over(room)
                        try:
                            write_meta(room.game_id, room.state, room.names)
                        except Exception:
                            pass
                else:
                    await websocket.send_json({"type": P.ERROR, "message": "Unknown message type"})
            except GameError as e:
                await websocket.send_json({"type": P.ERROR, "message": str(e)})
            except IllegalAction:
                await websocket.send_json({"type": P.ERROR, "message": "Illegal action"})
            except Exception:
                await websocket.send_json({"type": P.ERROR, "message": "Bad request"})
    except WebSocketDisconnect:
        room = manager.disconnect(websocket)
        if room is not None:
            await _broadcast_lobby(room)
