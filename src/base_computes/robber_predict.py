"""Simple robber placement prediction for each player.

Given the current board state, predicts each player's top-3 preferred
tiles to place the robber on, with softmax-derived probabilities.

python3 src/tests/test_robber_predict.py src/sample1.json
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from base_computes.game_state import GameState, VALID_NODES
from base_computes.settle_eval_simple import (
    _number_to_pips,
    _compute_relative_strengths,
    _softmax,
)
from parameters import (
    BASE_RESOURCE_STRENGTH,
    RAW_POWER_PREFERENCE,
    ROBBER_DAMPENING_FACTOR,
    ROBBER_K,
)


# ── Internals ────────────────────────────────────────────────────────────────


def _tiles_adjacent_to_node(node_key: str) -> List[int]:
    """Return the tile IDs that form a settlement node."""
    return [int(t) for t in node_key.split("_")]


def _count_settlements_on_tile(
    tile_id: int,
    nodes: Dict[str, List[int]],
) -> int:
    """Count how many settlements/cities sit on vertices touching *tile_id*.

    Each entry in *nodes* is ``"T1_T2_T3" -> [player_id, building_type]``.
    A node touches a tile when the tile ID appears in the node key.
    """
    count = 0
    tid_str = str(tile_id)
    for node_key in nodes:
        parts = node_key.split("_")
        if tid_str in parts:
            count += 1
    return count


def _player_has_settlement_on_tile(
    tile_id: int,
    player_id: int,
    nodes: Dict[str, List[int]],
) -> bool:
    """True when *player_id* has a settlement or city adjacent to *tile_id*."""
    tid_str = str(tile_id)
    for node_key, (pid, _btype) in nodes.items():
        parts = node_key.split("_")
        if tid_str in parts and pid == player_id:
            return True
    return False


# ── Public API ───────────────────────────────────────────────────────────────


def get_resource_weights(
    gs: GameState,
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """Compute and return the intermediate resource analysis.

    Returns
    -------
    (resource_prod, resource_weights, relative_strengths, balanced_preferences)
        resource_prod:         total expected production per resource (5-elem)
        resource_weights:      resource_prod normalised so average = 1
        relative_strengths:    dampened scarcity/complement strengths
        balanced_preferences:  relative_strengths + RAW_POWER_PREFERENCE
    """
    tiles = gs.map.tiles
    nodes = gs.map.nodes

    tile_expected: Dict[int, float] = {}
    tile_resource: Dict[int, int] = {}

    for tid in range(len(tiles)):
        res_id, number_token = tiles[tid]
        if 0 <= res_id <= 4 and number_token >= 2:
            pips = _number_to_pips(number_token)
            adj_settles = _count_settlements_on_tile(tid, nodes)
            tile_expected[tid] = pips * adj_settles
            tile_resource[tid] = res_id

    # Total expected production per resource
    resource_prod: List[float] = [0.0] * 5
    for tid, exp in tile_expected.items():
        resource_prod[tile_resource[tid]] += exp

    # Normalise so average weight is 1
    avg = sum(resource_prod) / 5.0 if any(resource_prod) else 1.0
    resource_weights: List[float] = (
        [p / avg for p in resource_prod] if avg > 0 else [0.0] * 5
    )

    # Relative strengths (scarcity + complement ratio, dampened)
    relative_strengths = _compute_relative_strengths(
        resource_prod, dampening=ROBBER_DAMPENING_FACTOR
    )

    # Balanced = relative strengths + raw power preference
    balanced_preferences: List[float] = [
        s + RAW_POWER_PREFERENCE for s in relative_strengths
    ]

    return resource_prod, resource_weights, relative_strengths, balanced_preferences


def predict_robber(
    gs: GameState,
) -> List[List[Tuple[int, float]]]:
    """Predict each player's top-3 robber placement preferences.

    Returns a list of length 4 (one per player).  Each element is a list
    of 3 ``(tile_id, probability)`` tuples whose probabilities sum to 1.

    Algorithm
    ---------
    1. For each land tile, compute ``expected_prod = pips × num_adjacent_settlements``.
    2. Sum production by resource type → resource weights.  Normalise
       so the average weight is 1.
    3. Compute dampened relative strengths (base_strength + scarcity +
       complement ratio, dampened by ``ROBBER_DAMPENING_FACTOR``) — same
       formula as settle scoring with a separate dampening parameter.
    4. Add ``RAW_POWER_PREFERENCE`` to each → ``balanced_preferences``.
    5. Each tile's score = ``expected_prod × balanced_preferences[resource_type]``.
    6. For each player, exclude tiles they have a settlement on, pick the
       top 3 scoring tiles, and convert scores to probabilities via softmax
       with spread factor ``ROBBER_K``.
    """
    tiles = gs.map.tiles
    nodes = gs.map.nodes

    # ── Step 1: expected production per tile ─────────────────────────
    tile_expected: Dict[int, float] = {}
    tile_resource: Dict[int, int] = {}

    for tid in range(len(tiles)):
        res_id, number_token = tiles[tid]
        if 0 <= res_id <= 4 and number_token >= 2:
            pips = _number_to_pips(number_token)
            adj_settles = _count_settlements_on_tile(tid, nodes)
            tile_expected[tid] = pips * adj_settles
            tile_resource[tid] = res_id

    # ── Step 2: resource weights (normalised avg = 1) ────────────────
    resource_prod: List[float] = [0.0] * 5
    for tid, exp in tile_expected.items():
        resource_prod[tile_resource[tid]] += exp

    # ── Step 3: relative strengths (scarcity + complement, dampened) ─
    relative_strengths = _compute_relative_strengths(
        resource_prod, dampening=ROBBER_DAMPENING_FACTOR
    )

    # ── Step 4: balanced preferences ─────────────────────────────────
    balanced_preferences: List[float] = [
        s + RAW_POWER_PREFERENCE for s in relative_strengths
    ]

    # ── Step 5: tile scores ──────────────────────────────────────────
    tile_scores: Dict[int, float] = {}
    for tid, exp in tile_expected.items():
        tile_scores[tid] = exp * balanced_preferences[tile_resource[tid]]

    # ── Step 6: per-player top-3 with softmax probabilities ──────────
    results: List[List[Tuple[int, float]]] = []

    for player in gs.players:
        pid = player.id

        # Eligible tiles: land tiles the player does NOT have a settlement on
        eligible: List[Tuple[int, float]] = []
        for tid, score in tile_scores.items():
            if not _player_has_settlement_on_tile(tid, pid, nodes):
                eligible.append((tid, score))

        # Sort descending by score
        eligible.sort(key=lambda x: x[1], reverse=True)

        # Take top 3
        top3 = eligible[:3]

        if not top3:
            # Edge case: no eligible tiles (shouldn't happen on a real board)
            results.append([])
            continue

        # Pad to 3 if fewer eligible tiles exist
        while len(top3) < 3:
            top3.append(top3[-1])

        # Convert scores → probabilities via softmax
        scores = [s for _, s in top3]
        probs = _softmax(scores, spread_factor=ROBBER_K)

        player_prefs: List[Tuple[int, float]] = [
            (tid, prob) for (tid, _), prob in zip(top3, probs)
        ]
        results.append(player_prefs)

    return results
