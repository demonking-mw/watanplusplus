"""Seeded RNG wrapper for reproducible games."""
from __future__ import annotations

import random


class GameRandom:
    """Deterministic randomness keyed by an integer seed.

    Wrapping random.Random keeps every game reproducible from its seed, which
    matters for debugging and for replaying logged games.
    """

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def roll_dice(self) -> tuple[int, int]:
        """Return two six sided dice."""
        return self._rng.randint(1, 6), self._rng.randint(1, 6)

    def shuffle(self, items: list) -> list:
        """Return a shuffled copy of items."""
        copy = list(items)
        self._rng.shuffle(copy)
        return copy
