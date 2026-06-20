"""Board generation: resources, number tokens, ports, robber start.

Phase 2 fills the board using a seeded RNG so each game is reproducible.
"""
from __future__ import annotations

from .rng import GameRandom


def generate_board(rng: GameRandom) -> dict:
    """Return a freshly generated board state.

    To be implemented in Phase 2.
    """
    raise NotImplementedError("Phase 2: board generation")
