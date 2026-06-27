"""Room and lobby management for catan_web.

The RoomManager owns every active game. It seats up to four players per room,
issues reconnect tokens, holds the authoritative GameState and its rng, and
applies validated actions. It knows nothing about WebSockets beyond storing an
opaque connection handle per seat, so it can be unit tested without a transport.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from catan_web.engine.actions import apply_action
from catan_web.engine.rng import GameRandom
from catan_web.engine.state import new_game_state

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4


class GameError(Exception):
    pass


@dataclass
class Seat:
    seat: int
    name: str
    token: str
    ws: object | None = None
    connected: bool = False


@dataclass
class Room:
    code: str
    seats: list = field(default_factory=list)
    host: int = 0
    started: bool = False
    state: object | None = None
    rng: object | None = None
    game_id: str = ""
    seq: int = 0
    names: list = field(default_factory=list)
    history: list = field(default_factory=list)


class RoomManager:
    def __init__(self):
        self.rooms: dict = {}
        self.conn: dict = {}

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self.rooms:
                return code

    def create(self, name, ws):
        code = self._new_code()
        seat = Seat(0, name, secrets.token_urlsafe(8), ws, True)
        room = Room(code=code, seats=[seat])
        self.rooms[code] = room
        if ws is not None:
            self.conn[ws] = (code, 0)
        return room, seat

    def join(self, code, name, token, ws):
        room = self.rooms.get(code)
        if room is None:
            raise GameError("No such room")
        if token:
            for s in room.seats:
                if s.token == token:
                    s.ws = ws
                    s.connected = True
                    if ws is not None:
                        self.conn[ws] = (code, s.seat)
                    return room, s
        if room.started:
            raise GameError("Game already started")
        if len(room.seats) >= 4:
            raise GameError("Room is full")
        s = Seat(len(room.seats), name, secrets.token_urlsafe(8), ws, True)
        room.seats.append(s)
        if ws is not None:
            self.conn[ws] = (code, s.seat)
        return room, s

    def start(self, code, seat):
        room = self.rooms.get(code)
        if room is None:
            raise GameError("No such room")
        if seat != room.host:
            raise GameError("Only the host can start")
        if room.started:
            raise GameError("Game already started")
        if len(room.seats) != 4:
            raise GameError("Need four players to start")
        room.names = [s.name for s in room.seats]
        seed = secrets.randbelow(2 ** 31)
        room.state = new_game_state(seed, room.names)
        room.rng = GameRandom(seed)
        room.game_id = f"{code}-{seed}"
        room.started = True
        return room

    def apply(self, code, seat, action):
        room = self.rooms.get(code)
        if room is None or not room.started:
            raise GameError("Game not started")
        apply_action(room.state, seat, action, room.rng)
        room.seq += 1
        return room

    def chat(self, code, seat, text):
        room = self.rooms.get(code)
        if room is None:
            raise GameError("No such room")
        if seat >= len(room.seats):
            raise GameError("Invalid seat")
        msg = text.strip()
        if not msg:
            raise GameError("Empty message")
        if len(msg) > 200:
            raise GameError("Message too long")
        return room, seat, msg

    def disconnect(self, ws):
        info = self.conn.pop(ws, None)
        if info is None:
            return None
        code, seat = info
        room = self.rooms.get(code)
        if room is not None and seat < len(room.seats):
            room.seats[seat].connected = False
            room.seats[seat].ws = None
        return room
