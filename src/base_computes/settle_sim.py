"""Settlement setup-phase simulator.

Simulates the full Catan 4-player snake-draft (8 placements) to produce
placeout scenarios for each of the current player's settlement options.

Uses:
  - ``top_settle_spots`` to generate the player's own candidate spots.
  - ``settle_decision`` to predict where every other player will settle.
  
python3 src/tests/test_settle_sim.py src/sample.json

Output is a comparison structure: one entry per candidate option, each
paired with up to *max_window* placeout board states and their
combined probabilities.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from base_computes.game_state import GameState
from base_computes.settle_eval_simple import (
    settle_decision,
    rank_all_spots,
    _pick_road,
)
from base_computes.settle_options import top_settle_spots


# ── Tunable Parameters ──────────────────────────────────────────────────────

MAX_WINDOW: int = 20  # PARAMETER: max placeout cases retained per settle option

# ── Standard 4-player snake draft order ─────────────────────────────────────
# Round 1: 0 → 1 → 2 → 3
# Round 2: 3 → 2 → 1 → 0
SETTLE_ORDER: List[int] = [0, 1, 2, 3, 3, 2, 1, 0]


# ── Internal helpers ────────────────────────────────────────────────────────


def _apply_placement(
    gs: GameState,
    settle_spot: str,
    road_spot: str,
    player_id: int,
) -> GameState:
    """Return a deep copy of *gs* with a settlement + road added.

    The new settlement is recorded as ``[player_id, 1]`` (type 1 =
    settlement) in ``map.nodes`` and the road as ``player_id`` in
    ``map.edges``.
    """
    new_gs = gs.model_copy(deep=True)
    new_gs.map.nodes[settle_spot] = [player_id, 1]
    new_gs.map.edges[road_spot] = player_id
    return new_gs


def _prune_and_normalize(
    cases: List[Tuple[GameState, float]],
    max_window: int,
) -> List[Tuple[GameState, float]]:
    """Keep the top *max_window* cases by probability, then re-normalize.

    If the list is already within the window, it is returned unchanged.
    After pruning, probabilities are rescaled so they sum to 1.
    """
    if len(cases) <= max_window:
        return cases

    cases.sort(key=lambda x: x[1], reverse=True)
    cases = cases[:max_window]

    total = sum(prob for _, prob in cases)
    if total > 0:
        cases = [(gs, prob / total) for gs, prob in cases]

    return cases


# ── Public entry point ──────────────────────────────────────────────────────


def simulate_settle(
    gs: GameState,
    x: int = 4,
    max_window: int = MAX_WINDOW,
) -> List[Tuple[Tuple[str, str], List[Tuple[GameState, float]]]]:
    """Simulate the entire setup draft for each of the player's options.

    Parameters
    ----------
    gs : GameState
        Current board state.  ``meta.p_curr`` identifies whose turn it
        is ("me").  The phase is expected to be ``"settle"``.
    x : int
        Number of top settlement spots to evaluate — same *x* that
        ``top_settle_spots`` uses.  Do **not** redefine here; it is
        forwarded directly.
    max_window : int
        Maximum number of placeout scenarios retained per settlement
        option.  After each simulated placement, if the case count
        exceeds this value, only the top *max_window* by combined
        probability are kept and re-normalized.

    Returns
    -------
    list of ``((settle_spot, road_spot), [(GameState, probability), ...])``

    *   One entry per candidate option (up to *x*).
    *   ``settle_spot``: node key ``"T1_T2_T3"`` for the player's pick.
    *   ``road_spot``: edge key ``"T1_T2"`` for the accompanying road.
    *   The inner list contains up to *max_window* fully-resolved
        placeout board states (all 8 settlements placed) and the
        combined probability of that placeout occurring.

    Notes
    -----
    *   The probability of the player's own initial placement is treated
        as **1.0** (we are comparing options, not weighting them).
    *   Combined probabilities are computed by multiplication across
        successive settle_decision predictions.
    *   The function does **not** estimate the relative likelihood of the
        player's *own* options; that comparison is the caller's job.
    """

    # Where are we in the 8-placement snake draft?
    current_placement = len(gs.map.nodes)
    remaining = len(SETTLE_ORDER) - current_placement

    if remaining <= 0:
        return []

    my_player = gs.meta.p_curr

    # ── Step 1: my settlement options via top_settle_spots ───────────
    my_options = top_settle_spots(gs, x=x)
    if not my_options:
        return []

    # Pre-compute score lookup + top-12 exclusion set for road picking
    ranked = rank_all_spots(gs)
    score_lookup: Dict[str, float] = {node: score for node, score in ranked}
    top12_keys = {node for node, _ in ranked[:12]}

    results: List[Tuple[Tuple[str, str], List[Tuple[GameState, float]]]] = []

    for settle_spot, _ in my_options:
        # Pick the road for my placement
        road = _pick_road(gs, settle_spot, score_lookup, top12_keys)

        # Apply my placement (probability = 1.0)
        state_after_mine = _apply_placement(gs, settle_spot, road, my_player)

        # Prepare for subsequent placements
        cases: List[Tuple[GameState, float]] = [(state_after_mine, 1.0)]

        # ── Steps 2+: simulate the remaining 7 (or fewer) placements ─
        for step in range(1, remaining):
            placement_idx = current_placement + step
            if placement_idx >= len(SETTLE_ORDER):
                break

            acting_player = SETTLE_ORDER[placement_idx]
            new_cases: List[Tuple[GameState, float]] = []

            for case_gs, case_prob in cases:
                # Set the acting player so settle_decision works on
                # the correct perspective
                sim_gs = case_gs.model_copy(deep=True)
                sim_gs.meta.p_curr = acting_player

                # settle_decision returns up to 3 options with softmax probs
                decisions = settle_decision(sim_gs)

                if not decisions:
                    # No valid spots left — carry forward as-is
                    new_cases.append((case_gs, case_prob))
                    continue

                for (s_spot, r_spot), d_prob in decisions:
                    new_state = _apply_placement(sim_gs, s_spot, r_spot, acting_player)
                    combined_prob = case_prob * d_prob
                    new_cases.append((new_state, combined_prob))

            # Prune to max_window and re-normalize
            cases = _prune_and_normalize(new_cases, max_window)

        results.append(((settle_spot, road), cases))

    return results
