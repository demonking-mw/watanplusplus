"""Per-player state views.

Phase 5 produces a redacted view for each player that hides opponents exact
hands and dev cards, exposing only public counts. The server keeps full truth
for logging.
"""
from __future__ import annotations


def view_for_player(state: dict, player: int) -> dict:
    """Return the state as the given player is allowed to see it.

    To be implemented in Phase 5.
    """
    raise NotImplementedError("Phase 5: per-player redaction")
