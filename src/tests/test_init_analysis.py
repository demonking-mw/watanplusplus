"""Test runner for the AI init board analysis agent.

Usage::

    cd src
    python3 tests/test_init_analysis.py sample5.json
    python3 tests/test_init_analysis.py sample5.json --provider anthropic
    python3 tests/test_init_analysis.py sample5.json --provider google --model gemini-2.5-flash
    python3 tests/test_init_analysis.py sample5.json --debug

Always runs settle simulation to produce a complete board, then analyses it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src directory to path if not already there
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI init board analysis")
    parser.add_argument("json_file", help="Path to sample JSON file")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        default=None,
        help="AI provider override",
    )
    parser.add_argument("--model", default=None, help="Model override")
    parser.add_argument("--save", default=None, help="Save full report to file")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument(
        "--debug", action="store_true", help="Print AI prompts and responses"
    )
    args = parser.parse_args()

    path = Path(args.json_file)
    if not path.exists():
        path = Path("src") / args.json_file

    with open(path) as f:
        data = json.load(f)

    from base_computes.game_state import GameState
    from base_computes.settle_sim import simulate_settle

    gs = GameState.from_json(data)

    # Always run settle simulation to get a complete board
    if not args.quiet:
        print(
            f"Board has {len(gs.map.nodes)} settlements. Running settle simulation..."
        )

    results = simulate_settle(gs)
    if not results:
        print("ERROR: settle simulation produced no results", file=sys.stderr)
        sys.exit(1)

    # Extract the most probable placeout from the first settle option
    option_settle, option_road = results[0][0]
    placeouts = results[0][1]
    placeouts.sort(key=lambda x: x[1], reverse=True)
    best_board, best_prob = placeouts[0]

    if not args.quiet:
        print(
            f"Using settle option {option_settle}, "
            f"most likely placeout (prob={best_prob:.4f})"
        )
        print(f"Board now has {len(best_board.map.nodes)} settlements")
        print()

    gs = best_board

    # Set up provider
    ai_kwargs = {}
    if args.provider:
        from ai import AIProvider

        provider_map = {
            "openai": AIProvider.OPENAI,
            "anthropic": AIProvider.ANTHROPIC,
            "google": AIProvider.GOOGLE,
        }
        ai_kwargs["provider"] = provider_map[args.provider]
    if args.model:
        ai_kwargs["model"] = args.model

    # Run the analysis
    from settle_process import analyze_init_board

    probs, report = asyncio.run(
        analyze_init_board(gs, verbose=not args.quiet, debug=args.debug, **ai_kwargs)
    )

    # Print the board
    # Add manual_processing to path for the visualizer
    _project_root = _src_dir.parent
    _manual_dir = _project_root / "manual_processing"
    if str(_manual_dir) not in sys.path:
        sys.path.insert(0, str(_manual_dir))
    from visualize_board import render_board

    render_board(gs)

    # Print AI agent results
    print("\n" + "=" * 72)
    print("AI AGENT WIN PROBABILITIES")
    print("=" * 72)
    for i in range(4):
        bar = "█" * int(probs[i] * 40)
        print(f"  Player {i}: {probs[i]:.4f}  {bar}")
    print(f"  Sum: {sum(probs):.4f}")
    print()

    # Print algorithmic init_eval baseline
    from base_computes.init_eval import evaluate_init_board as eval_board

    algo_scores, _ = eval_board(gs)
    print("ALGORITHMIC (init_eval) WIN LIKELIHOOD")
    print("=" * 72)
    for i in range(4):
        bar = "█" * int(algo_scores[i] * 40)
        print(f"  Player {i}: {algo_scores[i]:.4f}  {bar}")
    print(f"  Sum: {sum(algo_scores):.4f}")
    print()

    if args.save:
        save_path = Path(args.save)
        save_path.write_text(report, encoding="utf-8")
        print(f"Full report saved to {save_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()
