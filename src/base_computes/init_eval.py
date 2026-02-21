"""Non-AI initial board state evaluator.

Scores every player's starting position by combining post-robber
production quality, strategy alignment, port accessibility, and
positional advantages (road/city potential, number pairing).

All tunable parameters are top-level constants.  They are NEVER
overwritten internally — adjust them freely.

Usage::

    from base_computes.init_eval import evaluate_init_board
    scores, details = evaluate_init_board(gs)
    # scores is a 4-tuple normalised to sum to 1
    print(scores)  # e.g. (0.15, 0.35, 0.30, 0.20)
    for ev in details:
        print(f"Player {ev.player_id}: raw={ev.total_score:.2f} norm={scores[ev.player_id]:.4f}")
        for k, v in ev.breakdown.items():
            print(f"    {k}: {v}")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from base_computes.game_state import (
    GameState,
    VALID_NODES,
    PORT_TILE_TO_NODES,
)
from base_computes.robber_predict import predict_robber
from base_computes.settle_eval_simple import (
    _number_to_pips,
    _compute_relative_strengths,
    _bfs_from_node,
    BASE_RESOURCE_STRENGTH,
)


# ══════════════════════════════════════════════════════════════════════════════
# Tunable Parameters — NEVER overwritten below.  Adjust freely.
# ══════════════════════════════════════════════════════════════════════════════

# --- Strategy-alignment bonuses (flat additions to total score) ---
WB_BONUS: float = 2.0  # most wood/brick-focused player (lowest strategy index)
OWS_BONUS: float = 2.0  # most ore/wheat/sheep-focused player (highest strategy index)
EXTREME_BONUS: float = 1.5  # most polarised strategy (furthest from 0.5)

# --- Production-pair multiplier ---
# When a player has both halves of a complement pair (wood+brick OR
# wheat+ore) on the SAME dice number, those tiles' effective production
# is multiplied by this value FOR THAT PLAYER ONLY.
PROD_PAIR_BONUS: float = 1.3

# --- Aggregate-production scoring weights ---
TOTAL_MULTIPLIER: float = 0.5  # × sum(player's paired production)
TOTAL_VALUED_MULTIPLIER: float = 0.8  # × strength-weighted paired production

# --- Port-accessibility bonus ---
PORTABILITY_BONUS: float = 2.0

# --- Positional-advantage bonuses ---
BEST_ROAD_BONUS: float = 1.5  # player with highest wood+brick production
BEST_CITY_BONUS: float = 1.5  # player with highest ore+grain production

# --- No-wheat penalty ---
# Applied when a player's pre-robber, pre-pair-bonus wheat (grain)
# production is ≤ 2 pips.  Removed entirely if the player already
# sits on a 3:1 port; reduced to 1× if a 3:1 port is reachable
# within PORT_REACH_MIN .. PORT_REACH_MAX road hops.
NO_WHEAT: float = 1.0

# --- Targeting penalty ---
# Each player targets a rival; subtract this from the target's score.
# If multiple players target the same rival, penalty stacks.
TARGET_PENALTY: float = 1.5

# --- Relative-strength dampening (separate from settle/robber models) ---
INIT_EVAL_DAMPENING: float = 0.7

# --- Port reachability BFS distance limits (inclusive) ---
PORT_REACH_MIN: int = 2
PORT_REACH_MAX: int = 3


# ══════════════════════════════════════════════════════════════════════════════
# Result data class
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class PlayerEval:
    """Evaluation result for one player."""

    player_id: int
    total_score: float
    raw_prod: List[float]  # 5-elem pre-robber (no robber, no pair bonus)
    base_prod: List[float]  # 5-elem post-robber (no pair bonus)
    paired_prod: List[float]  # 5-elem post-robber with prod-pair bonus
    strategy_index: float  # 0 = pure WB, 1 = pure OWS
    prod_pairs: List[Tuple[int, int]]  # complement pairs detected
    has_port_access: bool  # portability bonus awarded?
    target: int = -1  # player ID this player targets
    breakdown: Dict[str, float] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════


def _find_prod_pairs(
    gs: GameState,
    player_id: int,
) -> Tuple[List[Tuple[int, int]], Set[int]]:
    """Detect complement pairs sharing a dice number for a player.

    A production pair exists when a player's settlements touch both
    halves of a complement pair (wood+brick OR wheat+ore) on tiles
    that carry the **same** number token.

    Returns
    -------
    (pairs_found, pair_tile_ids)
        pairs_found:  list of ``(resource_a, resource_b)`` tuples
        pair_tile_ids: set of tile IDs eligible for ``PROD_PAIR_BONUS``
    """
    # number_token → set of resource IDs the player touches
    number_resources: Dict[int, Set[int]] = {}
    # (resource, number_token) → set of tile IDs
    res_num_tiles: Dict[Tuple[int, int], Set[int]] = {}

    for node_key, (pid, _btype) in gs.map.nodes.items():
        if pid != player_id:
            continue
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num_token = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num_token >= 2:
                number_resources.setdefault(num_token, set()).add(res_id)
                res_num_tiles.setdefault((res_id, num_token), set()).add(tid)

    pairs_found: List[Tuple[int, int]] = []
    pair_tile_ids: Set[int] = set()

    # Complement pairs: Wood(0)/Brick(1), Grain(3)/Ore(4)
    for a, b in [(0, 1), (3, 4)]:
        for num_token, resources in number_resources.items():
            if a in resources and b in resources:
                pairs_found.append((a, b))
                pair_tile_ids.update(res_num_tiles.get((a, num_token), set()))
                pair_tile_ids.update(res_num_tiles.get((b, num_token), set()))

    return pairs_found, pair_tile_ids


def _compute_player_production(
    gs: GameState,
    player_id: int,
    tile_actual_prod: Dict[int, float],
    pair_tile_ids: Optional[Set[int]] = None,
) -> List[float]:
    """Per-resource actual production for a player.

    Each settlement/city adjacent to a resource tile contributes::

        tile_actual_prod[tid] × building_mult × pair_mult

    where building_mult is 2 for cities and 1 for settlements,
    and pair_mult is ``PROD_PAIR_BONUS`` for tiles in *pair_tile_ids*.

    If a tile is adjacent to multiple settlements of the same player,
    it is counted once per settlement (correct Catan mechanics —
    each settlement collects independently).

    Args:
        gs:              Game state.
        player_id:       Player to compute for.
        tile_actual_prod: tile_id → post-robber pip production.
        pair_tile_ids:   Tile IDs receiving ``PROD_PAIR_BONUS``
                         (``None`` → no pair bonus applied).

    Returns:
        5-element list indexed by resource ID (0-4).
    """
    prod = [0.0] * 5
    for node_key, (pid, btype) in gs.map.nodes.items():
        if pid != player_id:
            continue
        building_mult = 2 if btype == 2 else 1
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            res_id, num_token = gs.map.tiles[tid]
            if 0 <= res_id <= 4 and num_token >= 2:
                base = tile_actual_prod.get(tid, 0.0)
                pair_mult = (
                    PROD_PAIR_BONUS if pair_tile_ids and tid in pair_tile_ids else 1.0
                )
                prod[res_id] += base * building_mult * pair_mult
    return prod


def _check_portability(
    gs: GameState,
    player_id: int,
    player_base_prod: List[float],
) -> bool:
    """Check whether a player qualifies for the portability bonus.

    Criteria (ALL must hold):
      1. An **open** (unoccupied) port settlement node exists within
         ``PORT_REACH_MIN`` .. ``PORT_REACH_MAX`` road hops of one
         of the player's settlements.
      2. That port is either **3:1 any** (type 5), OR the player
         produces **≥ 5 pips** of the port's resource type
         (base production, ignoring prod-pair bonus).

    Note:
        The BFS traverses unoccupied valid-road edges only.  It does
        **not** block on opponent settlements (minor approximation,
        acceptable at init-phase sparsity).
    """
    occupied_nodes = set(gs.map.nodes.keys())
    port_nodes = set(gs.map.ports.keys())
    open_ports = port_nodes - occupied_nodes

    if not open_ports:
        return False

    # Gather player's settlement nodes
    player_settlements = [
        nk for nk, (pid, _) in gs.map.nodes.items() if pid == player_id
    ]

    for settle in player_settlements:
        reachable = _bfs_from_node(gs, settle, max_dist=PORT_REACH_MAX)
        for port_node in open_ports:
            if port_node not in reachable:
                continue
            dist, _ = reachable[port_node]
            if dist < PORT_REACH_MIN or dist > PORT_REACH_MAX:
                continue
            port_type = gs.map.ports[port_node]
            # 3:1 any → always qualifies
            if port_type == 5:
                return True
            # 2:1 specific → qualifies when player produces ≥ 5 pips
            if 0 <= port_type <= 4 and player_base_prod[port_type] >= 5.0:
                return True

    return False


def _strategy_index(paired_prod: List[float]) -> float:
    """Compute strategy index ∈ [0, 1].  0 = pure WB, 1 = pure OWS.

    Uses the min-of-complement idea::

        wb_power  = min(wood, brick)
        ows_power = min(ore, wheat, sheep)
        index     = ows_power / (wb_power + ows_power)

    Returns 0.5 (neutral) when total power is zero.
    """
    wb = min(paired_prod[0], paired_prod[1])  # min(wood, brick)
    ows = min(paired_prod[4], paired_prod[3], paired_prod[2])  # min(ore, wheat, sheep)
    total = wb + ows
    if total <= 0:
        return 0.5
    return ows / total


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


def evaluate_init_board(
    gs: GameState,
) -> Tuple[Tuple[float, float, float, float], List[PlayerEval]]:
    """Evaluate every player's initial board position.

    Algorithm
    ---------
    1. Run ``predict_robber``; divide each probability by 4.
    2. For each tile, sum the divided probabilities across all players
       → **rob attractiveness**.
    3. Tile actual production = ``(1 − rob_attractiveness) × pips``.
    4. Per-player **base** production (no prod-pair bonus) → 4 × 5-arrays.
    5. Board total = sum of the 4 base arrays.
    6. WB/OWS relative power =
       ``((min(wood, brick) + 2) / (min(ore, wheat, sheep) + 2)) × 1.1``
    7. Relative strengths via ``_compute_relative_strengths`` on the
       board total (dampened by ``INIT_EVAL_DAMPENING``).

    Per-player scoring components
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    - **Production pairs** detected → paired production computed.
    - **Strategy index** (0 = WB, 1 = OWS) from paired production.
    - ``sum(paired) × TOTAL_MULTIPLIER``
    - ``dot(paired, rel_strengths) × TOTAL_VALUED_MULTIPLIER``
    - ``WB_BONUS`` for the most WB-focused player (lowest strat index).
    - ``OWS_BONUS`` for the most OWS-focused player (highest strat index).
    - ``EXTREME_BONUS`` for the most polarised strategy (also covers
      "unique guy" — the player whose strategy differs most from neutral).
    - ``BEST_ROAD_BONUS`` for highest wood + brick production.
    - ``BEST_CITY_BONUS`` for highest ore + grain production.
    - ``PORTABILITY_BONUS`` if qualifying port is 2–3 roads away.

    Returns
    -------
    (scores, details)
        scores:  4-tuple of floats (player 0 … 3), normalised to sum to 1.
        details: list of ``PlayerEval`` (one per player, in player-ID order).
    """
    num_players = len(gs.players)
    if num_players == 0:
        return (0.25, 0.25, 0.25, 0.25), []

    # ── Step 1: rob prediction, each probability ÷ 4 ────────────────
    rob_predictions = predict_robber(gs)

    # ── Step 2: tile rob attractiveness ──────────────────────────────
    tile_rob_attr: Dict[int, float] = {}
    for player_preds in rob_predictions:
        for tile_id, prob in player_preds:
            tile_rob_attr[tile_id] = tile_rob_attr.get(tile_id, 0.0) + prob / 4.0

    # ── Step 3: tile actual production = (1 − rob_attr) × pips ──────
    tile_actual_prod: Dict[int, float] = {}
    for tid in range(len(gs.map.tiles)):
        res_id, num_token = gs.map.tiles[tid]
        if 0 <= res_id <= 4 and num_token >= 2:
            pips = _number_to_pips(num_token)
            rob = tile_rob_attr.get(tid, 0.0)
            tile_actual_prod[tid] = (1.0 - rob) * pips

    # ── Pre-robber raw pip production per tile (for raw_prod output) ─
    tile_raw_prod: Dict[int, float] = {}
    for tid in range(len(gs.map.tiles)):
        res_id, num_token = gs.map.tiles[tid]
        if 0 <= res_id <= 4 and num_token >= 2:
            tile_raw_prod[tid] = _number_to_pips(num_token)

    # ── Per-player RAW production (pre-robber, no pair bonus) ───────
    player_raw_prods: List[List[float]] = []
    for player in gs.players:
        raw = _compute_player_production(gs, player.id, tile_raw_prod)
        player_raw_prods.append(raw)

    # ── Step 4: per-player BASE production (no pair bonus) ──────────
    player_base_prods: List[List[float]] = []
    for player in gs.players:
        base = _compute_player_production(gs, player.id, tile_actual_prod)
        player_base_prods.append(base)

    # Detect production pairs and compute PAIRED production
    player_pairs_list: List[List[Tuple[int, int]]] = []
    player_pair_tids: List[Set[int]] = []
    player_paired_prods: List[List[float]] = []
    for player in gs.players:
        pairs, ptids = _find_prod_pairs(gs, player.id)
        player_pairs_list.append(pairs)
        player_pair_tids.append(ptids)
        paired = _compute_player_production(
            gs, player.id, tile_actual_prod, ptids if ptids else None
        )
        player_paired_prods.append(paired)

    # ── Step 5: total board production (from base, NOT paired) ──────
    total_board_prod = [
        sum(player_base_prods[p][r] for p in range(num_players)) for r in range(5)
    ]

    # ── Step 6: WB / OWS relative power ─────────────────────────────
    wb_min = min(total_board_prod[0], total_board_prod[1])
    ows_min = min(total_board_prod[4], total_board_prod[3], total_board_prod[2])
    wb_ows_power = ((wb_min + 2.0) / (ows_min + 2.0)) * 1.1

    # ── Step 7: relative strengths (dampened) ────────────────────────
    rel_strengths = _compute_relative_strengths(
        total_board_prod, dampening=INIT_EVAL_DAMPENING
    )

    # ── Strategy indices (from paired production) ────────────────────
    strat_indices = [_strategy_index(pp) for pp in player_paired_prods]

    # ── Determine bonus recipients ───────────────────────────────────
    min_strat = min(strat_indices)
    max_strat = max(strat_indices)
    extremes = [abs(s - 0.5) for s in strat_indices]
    max_extreme = max(extremes)

    # Road potential: paired wood(0) + brick(1)
    road_scores = [pp[0] + pp[1] for pp in player_paired_prods]
    max_road = max(road_scores) if road_scores else 0.0

    # City potential: paired ore(4) + grain(3)
    city_scores = [pp[4] + pp[3] for pp in player_paired_prods]
    max_city = max(city_scores) if city_scores else 0.0

    # ── Build per-player evaluations ─────────────────────────────────
    results: List[PlayerEval] = []

    for i, player in enumerate(gs.players):
        breakdown: Dict[str, float] = {}
        score = 0.0

        paired = player_paired_prods[i]
        base = player_base_prods[i]

        # ─ Total raw production × TOTAL_MULTIPLIER ───────────────
        total_raw = sum(paired)
        comp = total_raw * TOTAL_MULTIPLIER
        breakdown["total_prod"] = total_raw
        breakdown["total_prod_score"] = comp
        score += comp

        # ─ Strength-weighted production × TOTAL_VALUED_MULTIPLIER ─
        valued = sum(p * s for p, s in zip(paired, rel_strengths))
        comp = valued * TOTAL_VALUED_MULTIPLIER
        breakdown["valued_prod"] = valued
        breakdown["valued_prod_score"] = comp
        score += comp

        # ─ Strategy-alignment bonuses ────────────────────────────
        if strat_indices[i] == min_strat:
            breakdown["wb_bonus"] = WB_BONUS
            score += WB_BONUS

        if strat_indices[i] == max_strat:
            breakdown["ows_bonus"] = OWS_BONUS
            score += OWS_BONUS

        if extremes[i] == max_extreme:
            breakdown["extreme_bonus"] = EXTREME_BONUS
            score += EXTREME_BONUS

        # ─ Road advantage (best wood + brick) ────────────────────
        if max_road > 0 and road_scores[i] == max_road:
            breakdown["road_bonus"] = BEST_ROAD_BONUS
            score += BEST_ROAD_BONUS

        # ─ City advantage (best ore + grain) ─────────────────────
        if max_city > 0 and city_scores[i] == max_city:
            breakdown["city_bonus"] = BEST_CITY_BONUS
            score += BEST_CITY_BONUS

        # ─ Portability ───────────────────────────────────────────
        has_port = _check_portability(gs, player.id, base)
        if has_port:
            breakdown["port_bonus"] = PORTABILITY_BONUS
            score += PORTABILITY_BONUS

        # ─ No-wheat penalty ──────────────────────────────────────
        raw_wheat = player_raw_prods[i][3]  # grain = index 3
        if raw_wheat <= 2.0:
            # Check if player already sits on a 3:1 port
            player_nodes = [
                nk for nk, (pid, _) in gs.map.nodes.items() if pid == player.id
            ]
            has_major_port = any(
                nk in gs.map.ports and gs.map.ports[nk] == 5 for nk in player_nodes
            )

            if has_major_port:
                # Penalty fully removed
                breakdown["no_wheat_penalty"] = 0.0
            else:
                # Check for incoming 3:1 port (open, 2-3 roads away)
                occupied_nodes = set(gs.map.nodes.keys())
                port_nodes = set(gs.map.ports.keys())
                open_ports_31 = {
                    pn for pn in (port_nodes - occupied_nodes) if gs.map.ports[pn] == 5
                }
                has_incoming_major = False
                if open_ports_31:
                    for settle in player_nodes:
                        reachable = _bfs_from_node(
                            gs,
                            settle,
                            max_dist=PORT_REACH_MAX,
                        )
                        for pn in open_ports_31:
                            if pn in reachable:
                                dist, _ = reachable[pn]
                                if PORT_REACH_MIN <= dist <= PORT_REACH_MAX:
                                    has_incoming_major = True
                                    break
                        if has_incoming_major:
                            break

                if has_incoming_major:
                    penalty = 1.0 * NO_WHEAT
                else:
                    penalty = 3.0 * NO_WHEAT
                breakdown["no_wheat_penalty"] = round(-penalty, 4)
                score -= penalty

        # ─ Informational fields (not scored directly) ────────────
        breakdown["wb_ows_power"] = wb_ows_power
        breakdown["strategy_index"] = strat_indices[i]
        breakdown["total_pips"] = sum(base)  # total pips (base, no pairs)

        results.append(
            PlayerEval(
                player_id=player.id,
                total_score=round(score, 4),
                raw_prod=[round(v, 4) for v in player_raw_prods[i]],
                base_prod=[round(v, 4) for v in base],
                paired_prod=[round(v, 4) for v in paired],
                strategy_index=round(strat_indices[i], 4),
                prod_pairs=player_pairs_list[i],
                has_port_access=has_port,
                breakdown={k: round(v, 4) for k, v in breakdown.items()},
            )
        )

    # ── Targeting: each player picks a rival to pressure ─────────
    # Pre-target scores for comparison
    pre_target_scores = [ev.total_score for ev in results]

    # Classify players into WB (strat < 0.5) and OWS (strat >= 0.5)
    for i in range(num_players):
        my_strat = strat_indices[i]
        my_score = pre_target_scores[i]
        is_wb = my_strat < 0.5

        # 1. Strongest player with the same strategy (excluding self)
        same_strat_candidates = []
        for j in range(num_players):
            if j == i:
                continue
            j_is_wb = strat_indices[j] < 0.5
            if is_wb == j_is_wb and pre_target_scores[j] > my_score:
                same_strat_candidates.append((j, pre_target_scores[j]))

        if same_strat_candidates:
            # Pick the strongest same-strategy rival
            target_id = max(same_strat_candidates, key=lambda x: x[1])[0]
        else:
            # 2. Fallback: player with the highest eval outcome (excluding self)
            others = [(j, pre_target_scores[j]) for j in range(num_players) if j != i]
            target_id = max(others, key=lambda x: x[1])[0]

        results[i].target = gs.players[target_id].id
        results[i].breakdown["target"] = float(gs.players[target_id].id)

    # Subtract TARGET_PENALTY from each targeted player's score
    target_counts: Dict[int, int] = {}  # player_index → times targeted
    for ev in results:
        t_idx = next(j for j, p in enumerate(gs.players) if p.id == ev.target)
        target_counts[t_idx] = target_counts.get(t_idx, 0) + 1

    for j, count in target_counts.items():
        penalty = TARGET_PENALTY * count
        results[j].total_score = round(results[j].total_score - penalty, 4)
        results[j].breakdown["target_penalty"] = round(-penalty, 4)

    # ── Normalise to a 4-tuple summing to 1 ─────────────────────────
    raw = [ev.total_score for ev in results]
    total = sum(raw)
    if total > 0:
        normed = tuple(r / total for r in raw)
    else:
        normed = tuple(1.0 / num_players for _ in raw)

    # Pad to exactly 4 entries if fewer players (shouldn't happen)
    while len(normed) < 4:
        normed = normed + (0.0,)
    normed = normed[:4]  # type: ignore[assignment]

    return normed, results
