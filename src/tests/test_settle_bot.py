"""Test runner for the settle bot orchestrator.

Usage::

    cd src
    python3 tests/test_settle_bot.py sample5.json
    python3 tests/test_settle_bot.py sample5.json --ai-cutoff 3
    python3 tests/test_settle_bot.py sample5.json --provider openai --model gpt-4.1-mini
    python3 tests/test_settle_bot.py sample5.json --debug
    python3 tests/test_settle_bot.py sample5.json --x 4 --ai-cutoff 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add src directory to path if not already there
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the settle bot orchestrator")
    parser.add_argument("json_file", help="Path to sample JSON file")
    parser.add_argument(
        "--x", type=int, default=4,
        help="Number of settle options to evaluate (default: 6)",
    )
    parser.add_argument(
        "--ai-cutoff", type=int, default=None,
        help="Top N placeouts per option scored by AI (default: uses AI_CUTOFF from settle_bot)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        default=None,
        help="AI provider override",
    )
    parser.add_argument("--model", default=None, help="Model override")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--debug", action="store_true", help="Print AI prompts and responses")
    args = parser.parse_args()

    path = Path(args.json_file)
    if not path.exists():
        path = Path("src") / args.json_file

    with open(path) as f:
        data = json.load(f)

    from settle_process.settle_bot import find_best_settle

    bot_kwargs = {}
    if args.provider:
        from ai import AIProvider

        provider_map = {
            "openai": AIProvider.OPENAI,
            "anthropic": AIProvider.ANTHROPIC,
            "google": AIProvider.GOOGLE,
        }
        bot_kwargs["provider"] = provider_map[args.provider]
    if args.model:
        bot_kwargs["model"] = args.model

    if args.ai_cutoff is not None:
        bot_kwargs["ai_cutoff"] = args.ai_cutoff

    t0 = time.time()

    (best_settle, best_road), breakdown = asyncio.run(
        find_best_settle(
            data,
            x=args.x,
            verbose=not args.quiet,
            debug=args.debug,
            **bot_kwargs,
        )
    )

    elapsed = time.time() - t0

    # Show the board with the best settle option placed
    from base_computes.game_state import GameState
    from base_computes.settle_sim import simulate_settle

    gs = GameState.from_json(data)
    sim_results = simulate_settle(gs, x=args.x)

    # Find the placeout board for the winning option
    best_board = None
    for (spot, road), placeouts in sim_results:
        if spot == best_settle and road == best_road:
            placeouts.sort(key=lambda x: x[1], reverse=True)
            best_board = placeouts[0][0]
            break

    if best_board is not None:
        _project_root = _src_dir.parent
        _manual_dir = _project_root / "manual_processing"
        if str(_manual_dir) not in sys.path:
            sys.path.insert(0, str(_manual_dir))
        from visualize_board import render_board

        print()
        render_board(best_board)

    print("\n" + "=" * 60)
    print("SETTLE BOT RECOMMENDATION")
    print("=" * 60)
    print(f"  Settlement : {best_settle}")
    print(f"  Road       : {best_road}")
    print(f"  Score      : {breakdown[0][2]:.6f}")
    print(f"  Time       : {elapsed:.1f}s")
    print()
    print("Full ranking:")
    for rank, (s, r, sc) in enumerate(breakdown, 1):
        marker = " ★" if rank == 1 else ""
        print(f"  #{rank}  {s}  road={r}  score={sc:.6f}{marker}")


if __name__ == "__main__":
    main()
