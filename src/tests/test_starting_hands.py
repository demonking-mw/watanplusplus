"""Test compute_starting_hands against sample board states.

Usage::

    cd src
    PYTHONPATH=. python3 tests/test_starting_hands.py sample5.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from base_computes.game_state import GameState, compute_starting_hands

RESOURCE_NAMES = ["Wood", "Brick", "Wool", "Grain", "Ore"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tests/test_starting_hands.py <sample.json>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        path = Path("src") / sys.argv[1]

    with open(path) as f:
        data = json.load(f)

    gs = GameState.from_json(data)

    # Show settlement listing order
    print("Settlement listing order (from nodes dict):")
    settle_count: dict[int, int] = {}
    for i, (nk, (pid, bt)) in enumerate(gs.map.nodes.items()):
        settle_count[pid] = settle_count.get(pid, 0) + 1
        marker = " ← 2nd" if settle_count[pid] == 2 else ""
        print(f"  #{i}: {nk} → Player {pid} (type={bt}){marker}")

    print()

    hands = compute_starting_hands(gs)

    print("Starting hands:")
    for pid, hand in enumerate(hands):
        total = sum(hand)
        parts = ", ".join(f"{RESOURCE_NAMES[r]}={hand[r]}" for r in range(5) if hand[r])
        if not parts:
            parts = "(none)"
        print(f"  Player {pid}: {parts}  (total={total})")

        # Cross-reference with tiles adjacent to second settlement
        # for manual verification
        second_nodes = []
        cnt = 0
        for nk, (p, _) in gs.map.nodes.items():
            if p == pid:
                cnt += 1
                if cnt == 2:
                    second_nodes.append(nk)
                    break
        if second_nodes:
            nk = second_nodes[0]
            tiles_info = []
            for tid_str in nk.split("_"):
                tid = int(tid_str)
                res_id, num = gs.map.tiles[tid]
                rname = (
                    RESOURCE_NAMES[res_id]
                    if 0 <= res_id <= 4
                    else ("Desert" if res_id == 5 else "Ocean")
                )
                tiles_info.append(f"T{tid}={rname}({num})")
            print(f"    2nd settle {nk} tiles: {', '.join(tiles_info)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
