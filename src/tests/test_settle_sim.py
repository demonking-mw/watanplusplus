#!/usr/bin/env python3
"""Test script for the settlement setup-phase simulator.

Workflow: load JSON → parse into GameState → run simulate_settle → print results.

Usage (from the catana folder):
    python src/tests/test_settle_sim.py src/sample.json
    python src/tests/test_settle_sim.py src/sample.json --x 4 --max-window 20
"""

import argparse
import json
import os
import sys
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from base_computes import GameState
from base_computes.settle_sim import simulate_settle
from parameters import MAX_WINDOW

# Default values
DEFAULT_X = 6  # From top_settle_spots signature


def main():
    parser = argparse.ArgumentParser(
        description="Test settlement simulator on an HDCS JSON board state."
    )
    parser.add_argument("json_path", help="Path to the HDCS JSON file.")
    parser.add_argument(
        "--x",
        type=int,
        default=DEFAULT_X,
        help=f"Number of top settle options (default: {DEFAULT_X}).",
    )
    parser.add_argument(
        "--max-window",
        type=int,
        default=MAX_WINDOW,
        help=f"Max placeout cases per option (default: {MAX_WINDOW}).",
    )
    parser.add_argument(
        "--see-example",
        action="store_true",
        help="Print the GameState dataclass for the most likely case of the first option.",
    )
    args = parser.parse_args()

    # ── Load JSON ────────────────────────────────────────────────────────
    if not os.path.exists(args.json_path):
        print(f"Error: file not found: {args.json_path}")
        sys.exit(1)

    with open(args.json_path, "r") as f:
        data = json.load(f)

    # ── Parse into GameState ─────────────────────────────────────────────
    try:
        gs = GameState.from_json(data)
    except ValueError as e:
        print(f"Validation failed:\n{e}")
        sys.exit(1)

    print(
        f"Board loaded: {len(gs.map.nodes)} settlements, "
        f"{len(gs.map.edges)} roads, phase={gs.meta.phase}"
    )
    print(f"Current player: {gs.meta.p_curr}")
    print(f"Parameters: x={args.x}, max_window={args.max_window}\n")

    # ── Run simulation ───────────────────────────────────
    print("Running settlement simulator...")
    t0 = time.time()

    results = simulate_settle(
        gs,
        x=args.x,
        max_window=args.max_window,
    )

    elapsed = time.time() - t0
    print(f"Done in {elapsed:.2f}s — {len(results)} option(s) evaluated.\n")

    if not results:
        print("No valid settlement options.")
        sys.exit(0)

    # ── Print results ────────────────────────────────────────────────────
    print("=" * 72)
    print(f"  {'SETTLEMENT SIMULATOR RESULTS':^68}")
    print("=" * 72)

    for idx, ((settle, road), placeouts) in enumerate(results, 1):
        print(f"\n{'─' * 72}")
        print(f"  Option {idx}: settle={settle}  road={road}")
        print(f"  Placeouts: {len(placeouts)}")
        print(f"  {'─' * 66}")

        # Sort placeouts by probability descending for display
        sorted_po = sorted(placeouts, key=lambda x: x[1], reverse=True)

        print(f"  {'#':>4}  {'Prob':>10}  {'Settlements placed':>50}")
        print(f"  {'----':>4}  {'----------':>10}  {'-' * 50}")

        for j, (po_gs, prob) in enumerate(sorted_po, 1):
            # Summarize settlements in each placeout
            settles = []
            for node_key, (pid, btype) in sorted(po_gs.map.nodes.items()):
                settles.append(f"P{pid}@{node_key}")
            settle_str = ", ".join(settles)
            if len(settle_str) > 50:
                settle_str = settle_str[:47] + "..."
            print(f"  {j:>4}  {prob:>10.6f}  {settle_str:>50}")

        total_prob = sum(p for _, p in placeouts)
        print(f"\n  sum(prob) = {total_prob:.6f}")

    # ── Summary table ────────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print(f"  {'SUMMARY':^68}")
    print(f"{'=' * 72}")
    print(f"  {'#':>4}  {'Settle':>14}  {'Road':>8}  {'Cases':>6}  {'Top Prob':>10}")
    print(
        f"  {'----':>4}  {'-' * 14:>14}  {'-' * 8:>8}  {'------':>6}  {'----------':>10}"
    )

    for idx, ((settle, road), placeouts) in enumerate(results, 1):
        top_prob = max(p for _, p in placeouts) if placeouts else 0.0
        print(
            f"  {idx:>4}  {settle:>14}  {road:>8}  {len(placeouts):>6}  {top_prob:>10.6f}"
        )

    print()

    # ── Example GameState (if requested) ─────────────────────────────────
    if args.see_example and results:
        print("=" * 72)
        print(f"  {'EXAMPLE: Most Likely Case for Option 1':^68}")
        print("=" * 72)

        # Get first option's placeouts
        (settle, road), placeouts = results[0]

        # Find the most likely placeout
        most_likely_gs, most_likely_prob = max(placeouts, key=lambda x: x[1])

        print(f"\nOption 1: settle={settle}, road={road}")
        print(f"Most likely placeout (prob={most_likely_prob:.6f}):\n")
        print(most_likely_gs)
        print()


if __name__ == "__main__":
    main()
