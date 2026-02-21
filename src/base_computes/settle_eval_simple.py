"""Simple settlement spot scoring for initial placement.

Evaluates a settlement spot based on production value, resource scarcity,
port access, and diversity.  All tunable parameters are grouped at the top
of the file for easy adjustment.

python3 src/tests/test_settle_decision.py src/sample.json

"""

from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Optional, Tuple

from base_computes.game_state import GameState, VALID_NODES, get_adjacent_tiles


# ── Tunable Parameters ──────────────────────────────────────────────────────

# Intrinsic value multiplier per resource type.
# Index order: [Wood, Brick, Wool, Grain, Ore].
BASE_RESOURCE_STRENGTH: List[float] = [1.0, 1.0, 0.9, 1.27, 1.2]

# Controls how aggressively relative-strength is clamped.
# Applied as ``strength ** dampening_factor`` (values < 1 compress,
# values > 1 amplify).  0.5 is a square-root dampener.
DAMPENING_FACTOR: float = 0.8

# Multiplier applied to port strength when the spot has port access.
PORT_BONUS: float = 3

# Flat bonus added when a spot has total production >= 10 *and*
# at least 3 distinct resource types.
PRIME_VARIATE_BONUS: float = 4

# Multiplier for the complement-parity bonus.  For each
# complement pair (Wood/Brick, Grain/Ore), if the spot produces
# both, the bonus is ``parity_preference × min(prod_a, prod_b)``.
PARITY_PREFERENCE: float = 1.3

# Five floats that scale the five evaluation metrics before summing:
# [raw_production, scarcity_weighted, port, prime_variate, parity].
EVAL_WEIGHTS: List[float] = [1.0, 1.5, 1.0, 1.0, 1.0]

# Score spread controller for settle_decision softmax.
# Controls probability distribution: higher K = more different probabilities (more peaked),
# lower K = more similar probabilities (more uniform). K=1.0 is standard softmax.
# ALREADY TUNED
K: float = 1.5


# ── Dice-number → pip mapping ───────────────────────────────────────────────

# Number of dots on a standard Catan probability card.
# 2→1, 3→2, 4→3, 5→4, 6→5, 8→5, 9→4, 10→3, 11→2, 12→1
# 7 and 0 produce nothing.
_PIPS: Dict[int, int] = {
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    8: 5,
    9: 4,
    10: 3,
    11: 2,
    12: 1,
}


def _number_to_pips(number_token: int) -> int:
    """Return pip count for a dice number token (0 for desert/ocean/port)."""
    return _PIPS.get(number_token, 0)


# ── Helper: board-wide production totals ────────────────────────────────────


def _total_production_by_resource(gs: GameState) -> List[float]:
    """Sum pip production for each resource across all land tiles.

    Returns a 5-element list indexed by resource ID (0-4).
    """
    totals = [0.0] * 5
    for res_id, number_token in gs.map.tiles:
        if 0 <= res_id <= 4 and number_token >= 2:
            totals[res_id] += _number_to_pips(number_token)
    return totals


# ── Helper: complement pairs ────────────────────────────────────────────────

# Wood(0)↔Brick(1), Grain(3)↔Ore(4).  Wool(2) has no complement.
_COMPLEMENT = {0: 1, 1: 0, 3: 4, 4: 3}


def _compute_relative_strengths(
    total_prod: List[float],
    dampening: Optional[float] = None,
) -> List[float]:
    """Compute dampened relative strength for each resource.

    For each resource *r*:
        raw_strength = base_strength[r]
                     + (1 / total_prod[r])           # overall scarcity
                     + (prod[complement] / prod[r])   # pairwise ratio (bottleneck bonus)
    Then apply dampening:  dampened = raw ** dampening_factor

    Wool (no complement) uses pairwise ratio = 1.
    If a resource has zero total production, treat its scarcity as a large
    constant (20) to avoid division by zero.

    Args:
        total_prod:  5-element list of total pip production per resource.
        dampening:   Override for ``DAMPENING_FACTOR``.  When ``None``
                     (default), the module-level constant is used.
    """
    df = dampening if dampening is not None else DAMPENING_FACTOR
    strengths: List[float] = []
    for r in range(5):
        base = BASE_RESOURCE_STRENGTH[r]

        # overall scarcity
        if total_prod[r] > 0:
            overall = 1.0 / total_prod[r]
        else:
            overall = 20.0  # very scarce → high value

        # pairwise strength (complement's prod / this resource's prod)
        # → scarce resource with abundant complement gets a higher score
        comp = _COMPLEMENT.get(r)
        if comp is not None and total_prod[r] > 0:
            pairwise = total_prod[comp] / total_prod[r]
        else:
            pairwise = 1.0

        raw = base + overall + pairwise
        # dampen so the model doesn't overvalue rare resources
        dampened = math.pow(raw, df) if raw > 0 else 0.0
        strengths.append(dampened)

    return strengths


# ── Helper: port strengths ──────────────────────────────────────────────────


def _compute_port_strengths(
    total_prod: List[float],
) -> Dict[int, float]:
    """Compute per-port-type strength.

    For 2:1 ports (types 0-4):
        Apply dampening to the resource's total production, then normalize
        so the *second-highest* dampened value equals 1.
    3:1 port (type 5) always has strength 1.

    Returns dict mapping port type (0-5) → strength.
    """
    # dampened total yields for each resource
    dampened_yields = [
        math.pow(p, DAMPENING_FACTOR) if p > 0 else 0.0 for p in total_prod
    ]

    # normalise: second-highest dampened yield → 1
    sorted_yields = sorted(dampened_yields, reverse=True)
    second_highest = sorted_yields[1] if len(sorted_yields) > 1 else 1.0
    norm = second_highest if second_highest > 0 else 1.0

    port_str: Dict[int, float] = {}
    for r in range(5):
        port_str[r] = dampened_yields[r] / norm
    port_str[5] = 1.0  # 3:1 always 1

    return port_str


# ── Helper: spot production ─────────────────────────────────────────────────


def _spot_production(gs: GameState, node_key: str) -> List[float]:
    """Per-resource pip production for a settlement spot.

    *node_key* is ``"T1_T2_T3"``; each T is a tile ID.
    Returns a 5-element list of pip counts by resource (0-4).
    """
    tile_ids = [int(t) for t in node_key.split("_")]
    prod = [0.0] * 5
    for tid in tile_ids:
        res_id, number_token = gs.map.tiles[tid]
        if 0 <= res_id <= 4 and number_token >= 2:
            # Don't count production if the robber is on this tile
            if tid != gs.map.robber:
                prod[res_id] += _number_to_pips(number_token)
    return prod


# ── Public API ──────────────────────────────────────────────────────────────


def score_settlement(
    gs: GameState,
    node_key: str,
) -> float:
    """Score a single settlement spot.

    Args:
        gs:        Current game state.
        node_key:  Settlement node key (``"T1_T2_T3"``).

    Returns:
        A float score — higher is better.

    Metrics (each multiplied by its eval_weight):
        1. **Raw production** – sum of pips across the spot's tiles.
        2. **Scarcity-weighted production** – dot-product of spot production
           with dampened resource relative-strengths.
        3. **Port bonus** – if the spot is a port access node,
           ``port_strength × port_bonus``.
        4. **Prime variate** – bonus when total pips ≥ 10 and the spot
           touches ≥ 3 distinct resource types.
        5. **Parity** – for each complement pair (Wood/Brick, Grain/Ore),
           if the spot produces both, adds
           ``parity_preference × min(pair_production)``.
    """
    # Pre-compute board-wide data
    total_prod = _total_production_by_resource(gs)
    rel_strengths = _compute_relative_strengths(total_prod)
    port_strengths = _compute_port_strengths(total_prod)

    # Spot-level production
    prod = _spot_production(gs, node_key)

    # Metric 1: raw production
    raw_prod = sum(prod)

    # Metric 2: scarcity-weighted production
    scarcity_weighted = sum(p * s for p, s in zip(prod, rel_strengths))

    # Metric 3: port bonus
    port_bonus_val = 0.0
    if node_key in gs.map.ports:
        port_type = gs.map.ports[node_key]
        port_bonus_val = port_strengths.get(port_type, 0.0) * PORT_BONUS

    # Metric 4: prime variate bonus
    prime_variate_val = 0.0
    distinct_resources = sum(1 for p in prod if p > 0)
    if raw_prod >= 10 and distinct_resources >= 3:
        prime_variate_val = PRIME_VARIATE_BONUS

    # Metric 5: complement parity bonus
    # Wood(0)↔Brick(1), Grain(3)↔Ore(4)
    parity_val = 0.0
    for a, b in ((0, 1), (3, 4)):
        if prod[a] > 0 and prod[b] > 0:
            parity_val += PARITY_PREFERENCE * min(prod[a], prod[b])

    # Weighted sum
    metrics = [
        raw_prod,
        scarcity_weighted,
        port_bonus_val,
        prime_variate_val,
        parity_val,
    ]
    score = sum(m * w for m, w in zip(metrics, EVAL_WEIGHTS))
    return score


def rank_all_spots(
    gs: GameState,
    top_n: Optional[int] = None,
) -> List[tuple[str, float]]:
    """Score every valid, unoccupied settlement spot and return ranked list.

    Uses the canonical ``VALID_NODES`` set (54 spots) from game_state.

    Args:
        gs:     Current game state.
        top_n:  If set, return only the top *n* results.

    Returns:
        List of ``(node_key, score)`` sorted descending by score.
    """

    all_nodes = sorted(VALID_NODES)

    # Remove occupied spots and spots adjacent to existing settlements
    # "Distance rule": no settlement can be adjacent to another.
    # Two nodes are adjacent if they share exactly 2 of their 3 tile IDs.
    blocked: set[str] = set()
    for occ_key in gs.map.nodes:
        blocked.add(occ_key)
        occ_tiles = set(occ_key.split("_"))
        for node in all_nodes:
            node_tiles = set(node.split("_"))
            if len(occ_tiles & node_tiles) == 2:
                blocked.add(node)

    open_spots = [n for n in all_nodes if n not in blocked]

    results = [(n, score_settlement(gs, n)) for n in open_spots]
    results.sort(key=lambda x: x[1], reverse=True)
    if top_n is not None:
        results = results[:top_n]
    return results


# ── Settlement Decision Algorithm ───────────────────────────────────────────


# ── Road / edge helpers ─────────────────────────────────────────────────────


def _is_land_tile(tiles: List[List[int]], tile_id: int) -> bool:
    """True when *tile_id* is a land tile (not ocean, not a port)."""
    res_id, num_token = tiles[tile_id]
    return res_id != 6 and num_token != -1


def _is_valid_road_edge(tiles: List[List[int]], edge_key: str) -> bool:
    """True when at least one tile in the edge pair is a land tile."""
    t1, t2 = (int(t) for t in edge_key.split("_"))
    return _is_land_tile(tiles, t1) or _is_land_tile(tiles, t2)


def _get_node_edges(node_key: str) -> List[str]:
    """Return the 3 edge keys (``"Ta_Tb"``) adjacent to a settlement node."""
    tile_ids = [int(t) for t in node_key.split("_")]
    edges: List[str] = []
    for i in range(3):
        for j in range(i + 1, 3):
            a, b = sorted([tile_ids[i], tile_ids[j]])
            edges.append(f"{a}_{b}")
    return edges


def _get_other_node(edge_key: str, from_node: str) -> Optional[str]:
    """Find the valid node on the opposite side of *edge_key* from *from_node*.

    Returns ``None`` when the edge sits on the board boundary (no valid
    node on the other side).
    """
    edge_tiles = {int(t) for t in edge_key.split("_")}
    from_tiles = {int(t) for t in from_node.split("_")}
    third_tile = (from_tiles - edge_tiles).pop()

    t1, t2 = sorted(edge_tiles)
    common = get_adjacent_tiles(t1) & get_adjacent_tiles(t2)
    common.discard(third_tile)

    for other_tile in common:
        key = "_".join(str(t) for t in sorted([t1, t2, other_tile]))
        if key in VALID_NODES:
            return key
    return None


# ── BFS for road targeting ──────────────────────────────────────────────────


def _bfs_from_node(
    gs: GameState,
    start: str,
    max_dist: int,
) -> Dict[str, Tuple[int, Optional[str]]]:
    """BFS over the node-edge graph from *start*.

    Returns ``{node_key: (distance, first_edge)}`` for every reachable
    node within *max_dist* road-edges.  *first_edge* is the edge leaving
    *start* on the shortest path (``None`` for *start* itself).

    Only traverses edges that are valid road placements and not already
    occupied.
    """
    visited: Dict[str, Tuple[int, Optional[str]]] = {start: (0, None)}
    queue: deque = deque([(start, 0, None)])

    while queue:
        current, dist, first_edge = queue.popleft()
        if dist >= max_dist:
            continue

        for edge in _get_node_edges(current):
            if not _is_valid_road_edge(gs.map.tiles, edge):
                continue
            if edge in gs.map.edges:
                continue

            neighbor = _get_other_node(edge, current)
            if neighbor is None or neighbor in visited:
                continue

            fe = first_edge if first_edge is not None else edge
            visited[neighbor] = (dist + 1, fe)
            queue.append((neighbor, dist + 1, fe))

    return visited


# ── Softmax utility ─────────────────────────────────────────────────────────


def _softmax(values: List[float], spread_factor: float = 1.0) -> List[float]:
    """Numerically-stable softmax with spread control.

    Args:
        values: List of floats to apply softmax to.
        spread_factor: Controls distribution spread. Higher = more different probabilities,
                      lower = more uniform probabilities. Uses inverse temperature scaling.
    """
    # Convert spread_factor to temperature (inverse relationship)
    # Higher spread_factor → lower temperature → more peaked
    # Lower spread_factor → higher temperature → more uniform
    temperature = 1.0 / spread_factor if spread_factor > 0 else 1.0

    # Scale by temperature
    scaled = [v / temperature for v in values]
    # Numerically stable softmax
    m = max(scaled)
    exps = [math.exp(v - m) for v in scaled]
    s = sum(exps)
    return [e / s for e in exps]


# ── Road selection ──────────────────────────────────────────────────────────


def _pick_road(
    gs: GameState,
    settle_spot: str,
    score_lookup: Dict[str, float],
    excluded_keys: set,
) -> str:
    """Select the best road edge adjacent to *settle_spot*.

    Targets open settlement spots within road-distance < 4, excluding
    the top-12 scoring nodes and any spot that is occupied or adjacent
    to an occupied spot (distance rule).  Picks the highest-scoring
    remainder.  Returns the first edge on the shortest path from
    *settle_spot* to that target.

    Falls back to any valid, unoccupied adjacent edge when no qualifying
    target is found.
    """
    reachable = _bfs_from_node(gs, settle_spot, max_dist=3)

    # Build set of nodes that cannot be settled: occupied + distance-rule blocked
    blocked: set = set()
    for occ_key in gs.map.nodes:
        blocked.add(occ_key)
        occ_tiles = set(occ_key.split("_"))
        for node_key in reachable:
            node_tiles = set(node_key.split("_"))
            if len(occ_tiles & node_tiles) == 2:
                blocked.add(node_key)

    best_edge: Optional[str] = None
    best_score = -float("inf")

    for node, (dist, first_edge) in reachable.items():
        if dist == 0:
            continue
        if node in excluded_keys:
            continue
        if node in blocked:
            continue
        if node not in score_lookup:
            continue
        if score_lookup[node] > best_score:
            best_score = score_lookup[node]
            best_edge = first_edge

    if best_edge is not None:
        return best_edge

    # Fallback: any valid, unoccupied road adjacent to the settlement
    for edge in _get_node_edges(settle_spot):
        if _is_valid_road_edge(gs.map.tiles, edge) and edge not in gs.map.edges:
            return edge

    # Ultimate fallback (should never fire on a normal board)
    return _get_node_edges(settle_spot)[0]


# ── Public entry point ──────────────────────────────────────────────────────


def settle_decision(
    gs: GameState,
) -> List[Tuple[Tuple[str, str], float]]:
    """Choose up to 3 settlement + road placements with softmax probabilities.

    Algorithm
    ---------
    1. Score every open settlement spot (via ``rank_all_spots``).
    2. Pick the top 3.
    3. Apply softmax with spread factor K to convert scores to probabilities.
       Higher K → more peaked distribution (larger differences).
       Lower K → more uniform distribution (smaller differences).
    4. For each settlement pick a road edge adjacent to it that points
       toward the best expansion target.

    Road target selection
    ---------------------
    BFS from the settlement up to 3 edges.  Among reachable open spots,
    exclude the top-12 scoring nodes, then pick the highest-scoring
    remainder.  The road returned is the first edge on the shortest path
    from the settlement to the chosen target.

    Parameters
    ----------
    gs : GameState
        Current game state.

    Returns
    -------
    list of ``((settle_spot, road_spot), probability)``
        *settle_spot*: node key ``"T1_T2_T3"``
        *road_spot*:   edge key ``"T1_T2"``
        *probability*: softmax-derived float (sums to ≈ 1).
    """
    # 1. Score every open spot
    ranked = rank_all_spots(gs)

    if not ranked:
        return []

    # 2. Top 3 (or fewer if the board is nearly full)
    n = min(3, len(ranked))
    top = ranked[:n]

    # Top-12 keys for road-target exclusion
    top12_keys = {node for node, _ in ranked[:12]}

    # 3. Apply softmax with spread factor K
    scores = [score for _, score in top]
    probs = _softmax(scores, spread_factor=K)

    # 4. Pair each settlement with the best road
    score_lookup: Dict[str, float] = {node: score for node, score in ranked}

    results: List[Tuple[Tuple[str, str], float]] = []
    for i, (settle_spot, _) in enumerate(top):
        road = _pick_road(gs, settle_spot, score_lookup, top12_keys)
        results.append(((settle_spot, road), probs[i]))

    return results
