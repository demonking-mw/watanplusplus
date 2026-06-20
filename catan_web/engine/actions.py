"""Authoritative state transitions.

apply_action validates and applies a single action, returning the new state.
Phase 3 implements the minimal game, Phase 7 adds dev cards, awards, trades.
"""
from __future__ import annotations


def apply_action(state: dict, action: dict) -> dict:
    """Apply one action and return the resulting state.

    To be implemented in Phase 3.
    """
    raise NotImplementedError("Phase 3: apply action")
