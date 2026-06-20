"""Room and lobby management.

Phase 5 implements room codes, seat assignment, player tokens, and reconnect.
"""
from __future__ import annotations


class RoomManager:
    """Tracks active game rooms keyed by room code.

    To be implemented in Phase 5.
    """

    def __init__(self) -> None:
        self.rooms: dict = {}
