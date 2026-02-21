"""Top-X settlement spot picker for the setup phase.

Returns the best *X* open settlement spots ranked by the augmented
scoring algorithm.  Spots must be:
  - valid Catan nodes (from the 54-node canonical set),
  - unoccupied,
  - not adjacent (distance-rule) to any *existing* settlement on the board.

Spots **may** be adjacent to each other in the returned list — this is
intentional because the function simulates candidate generation, not
simultaneous placement.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from base_computes.game_state import GameState, VALID_NODES
from base_computes.settle_eval_simple import (
    rank_all_spots,
    score_settlement,
)


def extend_option(gs: GameState) -> List[Tuple[str, float]]:
    """Return extra settlement spot candidates beyond the scored list.

    This is a **placeholder** for future implementation.  Intended use
    cases include injecting hand-picked strategic spots, ML-suggested
    positions, or situational overrides that the raw scoring algorithm
    might undervalue.

    Args:
        gs: The full game state data object.

    Returns:
        A list of ``(node_key, score)`` tuples.  Currently always empty.
    """
    # TODO: Implement custom extension logic here.
    #       Return a list of (node_key, score) tuples to be merged with
    #       the top-X scored spots.  Duplicates are deduplicated
    #       automatically by top_settle_spots().
    return []


def top_settle_spots(
    gs: GameState,
    x: int = 4,  # PARAMETER: Number of top settlement spots to return
) -> List[Tuple[str, float]]:
    """Return the top *x* open settlement spots for setup placement.

    Algorithm
    ---------
    1. Use ``rank_all_spots`` to score every open (unoccupied and not
       adjacent to an existing settlement) valid node.
    2. Call ``extend_option`` to collect any extra candidates.
    3. Merge the two lists, deduplicate by node key (keeping the higher
       score if a spot appears in both), sort descending by score, and
       return the top *x*.

    Args:
        gs:     Current game state.
        x:      Number of spots to return (default: 6).

    Returns:
        List of ``(node_key, score)`` sorted descending, length ≤ *x*.
    """
    # 1. Score all open spots via the existing ranking engine
    scored = rank_all_spots(gs)  # already sorted descending

    # 2. Collect extended options
    extras = extend_option(gs)

    # 3. Merge & deduplicate (keep the higher score per node)
    best: dict[str, float] = {}
    for node_key, sc in scored:
        best[node_key] = max(best.get(node_key, -float("inf")), sc)
    for node_key, sc in extras:
        best[node_key] = max(best.get(node_key, -float("inf")), sc)

    merged = sorted(best.items(), key=lambda t: t[1], reverse=True)
    return merged[:x]
