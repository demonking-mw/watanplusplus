#!/usr/bin/env python3
"""Test init board state evaluator via settle simulation pipeline.

Workflow:
  1. Load JSON → GameState
  2. Run settle simulation (full 8-placement draft)
  3. Pick the most likely placeout from the first settle option
  4. Run init_eval on that completed board
  5. Print the evaluation results
  6. Print the board visualization
"""

import json
import os
import sys

# Add src/ and manual_processing/ to path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_dir = os.path.dirname(src_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
manual_dir = os.path.join(repo_dir, "manual_processing")
if manual_dir not in sys.path:
    sys.path.insert(0, manual_dir)

from base_computes.game_state import GameState
from base_computes.init_eval import evaluate_init_board
from base_computes.settle_sim import simulate_settle
from visualize_board import render_board

path = sys.argv[1] if len(sys.argv) > 1 else "sample1.json"
with open(path) as f:
    data = json.load(f)

gs = GameState.from_json(data)

# ── Step 1: Run settle simulation ────────────────────────────────────
print("Running settle simulation...")
sim_results = simulate_settle(gs)

if not sim_results:
    print("No simulation results (board may already be full).")
    sys.exit(0)

# ── Step 2: Pick most likely placeout from first option ──────────────
first_option, placeouts = sim_results[0]
settle_spot, road_spot = first_option

# Sort by probability descending, pick the top one
placeouts.sort(key=lambda x: x[1], reverse=True)
best_board, best_prob = placeouts[0]

print(f"First settle option: {settle_spot} (road: {road_spot})")
print(f"Most likely placeout probability: {best_prob:.4f}")
print(f"Total placeout cases for this option: {len(placeouts)}")

# ── Step 3: Run init_eval on the completed board ─────────────────────
scores, results = evaluate_init_board(best_board)

print("\n" + "=" * 70)
print("INIT BOARD STATE EVALUATION  (most likely placeout, option #1)")
print("=" * 70)
print(f"\nNormalised scores (sum=1): {tuple(round(s, 4) for s in scores)}")

for ev in results:
    print(f"\nPlayer {ev.player_id}:  score = {ev.total_score:.4f}")
    print(f"  Raw prod   (W/B/Sh/Wh/O): {['%.2f' % v for v in ev.raw_prod]}")
    print(f"  Base prod  (W/B/Sh/Wh/O): {['%.2f' % v for v in ev.base_prod]}")
    print(f"  Paired prod(W/B/Sh/Wh/O): {['%.2f' % v for v in ev.paired_prod]}")
    print(f"  Strategy index: {ev.strategy_index:.4f}  (0=WB, 1=OWS)")
    print(f"  Prod pairs: {ev.prod_pairs}")
    print(f"  Port access: {ev.has_port_access}")
    print(f"  Target: Player {ev.target}")
    print(f"  Breakdown:")
    for k, v in ev.breakdown.items():
        print(f"    {k:25s} = {v:.4f}")

print(f"\n>> Normalised scores: {tuple(round(s, 4) for s in scores)}")

# ── Step 4: Validation ───────────────────────────────────────────────
print("\n" + "-" * 70)
print("Validation:")
assert len(results) == len(best_board.players), "Result count != player count"
assert len(scores) == 4, f"Expected 4-tuple, got {len(scores)}"
assert abs(sum(scores) - 1.0) < 1e-6, f"Scores sum to {sum(scores)}, not 1.0"
for ev in results:
    assert (
        0 <= ev.strategy_index <= 1
    ), f"Player {ev.player_id}: strat index out of [0,1]"
    assert len(ev.raw_prod) == 5, "raw_prod must have 5 elements"
    assert len(ev.base_prod) == 5, "base_prod must have 5 elements"
    assert len(ev.paired_prod) == 5, "paired_prod must have 5 elements"
    for r in range(5):
        assert (
            ev.raw_prod[r] >= ev.base_prod[r] - 1e-9
        ), f"Player {ev.player_id}: raw_prod[{r}] < base_prod[{r}]"
        assert (
            ev.paired_prod[r] >= ev.base_prod[r] - 1e-9
        ), f"Player {ev.player_id}: paired_prod[{r}] < base_prod[{r}]"
print("All checks passed.\n")

# ── Step 5: Print the board ──────────────────────────────────────────
print("=" * 70)
print("BOARD STATE  (after all 8 settlements)")
print("=" * 70)
render_board(best_board)
