"""Game state model and turn phases.

Phase 2 and 3 flesh out the full GameState. For now this defines the phase
labels the engine and protocol will share.
"""
from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    LOBBY = "lobby"
    SETUP = "setup"
    ROLL = "roll"
    MAIN = "main"
    DISCARD = "discard"
    ROBBER = "robber"
    GAME_OVER = "game_over"


def new_game_state(seed: int, player_names: list[str]) -> dict:
    """Create the initial game state for four players.

    To be implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: initial state")
