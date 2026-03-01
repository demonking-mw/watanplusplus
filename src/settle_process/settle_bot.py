"""Settle-bot orchestrator — picks the best initial settlement.

Workflow
--------
1. Ingest a raw JSON dict → ``GameState`` data object.
2. Run ``simulate_settle`` → up to *max_window* placeout boards per
   candidate settlement option.
3. Score each option asynchronously:
   - Top *ai_cutoff* placeouts (by probability): scored via the full
     AI analysis pipeline (``analyze_init_board``), run concurrently.
   - Remaining placeouts: scored via the fast algorithmic evaluator
     (``evaluate_init_board``).
   - Option score = Σ (placeout_probability × player_0_win_chance).
4. Return the settlement+road with the highest score.

Usage::

    import asyncio, json
    from settle_process.settle_bot import find_best_settle

    with open("sample5.json") as f:
        data = json.load(f)

    best, breakdown = asyncio.run(find_best_settle(data))
    # best = ("10_16_17", "10_17")
    # breakdown = [("10_16_17", "10_17", 0.2731), ...]
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

from ai import AIProvider
from base_computes.game_state import GameState
from base_computes.init_eval import evaluate_init_board
from base_computes.settle_sim import simulate_settle
from settle_process.init_analysis import analyze_init_board


# ── Tunable Parameters ──────────────────────────────────────────────────────

AI_CUTOFF: int = 8  # PARAMETER: top X placeouts per option scored by AI


# ── Internal helpers ────────────────────────────────────────────────────────


def _algo_score_p0(gs: GameState) -> float:
    """Return player 0's normalised win likelihood from the algorithmic evaluator."""
    scores, _ = evaluate_init_board(gs)
    return scores[0]


async def _ai_score_p0(
    gs: GameState,
    *,
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None,
    debug: bool = False,
) -> float:
    """Return player 0's win probability from the full AI pipeline."""
    ai_kwargs: Dict[str, Any] = {}
    if provider is not None:
        ai_kwargs["provider"] = provider
    if model is not None:
        ai_kwargs["model"] = model

    probs, _report = await analyze_init_board(
        gs,
        verbose=False,
        debug=debug,
        **ai_kwargs,
    )
    return probs[0]


async def _score_option(
    settle_spot: str,
    road_spot: str,
    placeouts: List[Tuple[GameState, float]],
    ai_cutoff: int,
    *,
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None,
    debug: bool = False,
    verbose: bool = False,
) -> float:
    """Score a single settle option by weighting all its placeouts.

    The top *ai_cutoff* placeouts (sorted by probability descending) are
    scored with the AI pipeline; the rest use the algorithmic evaluator.

    Returns the weighted score: Σ prob_i × player_0_win_chance_i.
    """
    # Sort placeouts by probability, descending
    ordered = sorted(placeouts, key=lambda x: x[1], reverse=True)
    ai_boards = ordered[:ai_cutoff]
    algo_boards = ordered[ai_cutoff:]

    total_score = 0.0

    # ── AI-scored placeouts (run concurrently) ───────────────────────
    if ai_boards:
        if verbose:
            print(
                f"  [{settle_spot}] Launching {len(ai_boards)} AI analyses "
                f"(cutoff={ai_cutoff})…"
            )

        ai_tasks = [
            _ai_score_p0(gs, provider=provider, model=model, debug=debug)
            for gs, _prob in ai_boards
        ]
        ai_results = await asyncio.gather(*ai_tasks)

        for (gs, prob), p0_chance in zip(ai_boards, ai_results):
            total_score += prob * p0_chance
            if verbose:
                print(
                    f"    AI  placeout prob={prob:.4f}  p0={p0_chance:.4f}  → +{prob * p0_chance:.6f}"
                )

    # ── Algorithmically-scored placeouts ─────────────────────────────
    for gs, prob in algo_boards:
        p0_chance = _algo_score_p0(gs)
        total_score += prob * p0_chance
        if verbose:
            print(
                f"    Algo placeout prob={prob:.4f}  p0={p0_chance:.4f}  → +{prob * p0_chance:.6f}"
            )

    return total_score


# ── Public entry point ──────────────────────────────────────────────────────


async def find_best_settle(
    data: dict,
    *,
    x: int = 4,
    ai_cutoff: int = AI_CUTOFF,
    provider: Optional[AIProvider] = None,
    model: Optional[str] = None,
    verbose: bool = True,
    debug: bool = False,
) -> Tuple[
    Tuple[str, str],
    List[Tuple[str, str, float]],
]:
    """Find the best initial settlement placement.

    Parameters
    ----------
    data : dict
        Raw HDCS JSON dict (as loaded from file).
    x : int
        Number of top settlement spots to evaluate (forwarded to
        ``simulate_settle`` / ``top_settle_spots``).
    ai_cutoff : int
        Per settle option, how many of the most-likely placeouts are
        scored via the full AI pipeline.  The rest use the fast
        algorithmic evaluator.  Default 5.
    provider : AIProvider, optional
        AI provider override.
    model : str, optional
        Model override.
    verbose : bool
        Print progress to stdout.
    debug : bool
        Forward to AI query layer (prints prompts/responses).

    Returns
    -------
    (best_option, breakdown)
        best_option: ``(settle_spot, road_spot)`` — the recommended
        placement.
        breakdown: sorted list of ``(settle_spot, road_spot, score)``
        for every evaluated option (descending by score).
    """
    # ── Step 1: ingest JSON → GameState ──────────────────────────────
    gs = GameState.from_json(data)
    if verbose:
        print(
            f"[Bot] Parsed board: {len(gs.map.nodes)} settlements, "
            f"{len(gs.map.tiles)} tiles"
        )

    # ── Step 2: simulate settle draft ────────────────────────────────
    if verbose:
        print(f"[Bot] Running settle simulation (x={x})…")

    sim_results = simulate_settle(gs, x=x)
    if not sim_results:
        raise RuntimeError("settle simulation produced no results")

    if verbose:
        print(f"[Bot] {len(sim_results)} settle options generated")
        for (spot, road), placeouts in sim_results:
            print(f"  {spot} (road {road}): {len(placeouts)} placeouts")

    # ── Step 3: async scoring orchestrator ───────────────────────────
    if verbose:
        print(f"[Bot] Scoring options (AI cutoff={ai_cutoff} per option)…\n")

    # ── Collect ALL AI tasks across all options, fire together ────────
    # Each entry: (option_index, placeout_index, gs, prob)
    ai_jobs: List[Tuple[int, int, GameState, float]] = []
    # Per-option algo boards for sync scoring
    algo_per_option: List[List[Tuple[GameState, float]]] = []
    option_keys: List[Tuple[str, str]] = []

    for opt_idx, ((settle_spot, road_spot), placeouts) in enumerate(sim_results):
        option_keys.append((settle_spot, road_spot))
        ordered = sorted(placeouts, key=lambda x: x[1], reverse=True)
        ai_boards = ordered[:ai_cutoff]
        algo_boards = ordered[ai_cutoff:]
        algo_per_option.append(algo_boards)

        for po_idx, (gs, prob) in enumerate(ai_boards):
            ai_jobs.append((opt_idx, po_idx, gs, prob))

        if verbose:
            print(
                f"  [{settle_spot}] {len(ai_boards)} AI + "
                f"{len(algo_boards)} algo placeouts"
            )

    # Fire all AI calls concurrently
    if verbose:
        print(f"\n[Bot] Launching {len(ai_jobs)} AI calls concurrently…")

    ai_tasks = [
        _ai_score_p0(gs, provider=provider, model=model, debug=debug)
        for _, _, gs, _ in ai_jobs
    ]
    ai_results = await asyncio.gather(*ai_tasks) if ai_tasks else []

    # ── Assemble scores per option ───────────────────────────────────
    num_options = len(option_keys)
    option_totals = [0.0] * num_options

    # Add AI-scored contributions
    for job_idx, (opt_idx, _po_idx, _gs, prob) in enumerate(ai_jobs):
        p0_chance = ai_results[job_idx]
        option_totals[opt_idx] += prob * p0_chance
        if verbose:
            print(
                f"    [{option_keys[opt_idx][0]}] AI  prob={prob:.4f}  "
                f"p0={p0_chance:.4f}  → +{prob * p0_chance:.6f}"
            )

    # Add algo-scored contributions
    for opt_idx, algo_boards in enumerate(algo_per_option):
        for gs, prob in algo_boards:
            p0_chance = _algo_score_p0(gs)
            option_totals[opt_idx] += prob * p0_chance
            if verbose:
                print(
                    f"    [{option_keys[opt_idx][0]}] Algo prob={prob:.4f}  "
                    f"p0={p0_chance:.4f}  → +{prob * p0_chance:.6f}"
                )

    option_scores: List[Tuple[str, str, float]] = [
        (s, r, option_totals[i]) for i, (s, r) in enumerate(option_keys)
    ]

    if verbose:
        for s, r, sc in option_scores:
            print(f"  ⇒ {s}: {sc:.6f}")

    # ── Step 4: pick the winner ──────────────────────────────────────
    option_scores.sort(key=lambda x: x[2], reverse=True)
    best_settle, best_road, best_score = option_scores[0]

    if verbose:
        print("=" * 60)
        print("SETTLE BOT RESULTS (ranked)")
        print("=" * 60)
        for rank, (s, r, sc) in enumerate(option_scores, 1):
            marker = " ★" if rank == 1 else ""
            print(f"  #{rank}  {s}  road={r}  score={sc:.6f}{marker}")
        print()

    return (best_settle, best_road), option_scores
