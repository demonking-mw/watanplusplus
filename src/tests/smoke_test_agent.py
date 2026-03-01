"""Quick smoke test: verify settle_process imports and helpers work."""
from settle_process.init_analysis import analyze_init_board, _parse_probabilities

# Test probability parser
assert _parse_probabilities("PROBABILITIES: [0.25, 0.30, 0.20, 0.25]") is not None
p = _parse_probabilities("PROBABILITIES: [0.25, 0.30, 0.20, 0.25]")
assert abs(sum(p) - 1.0) < 1e-6
print(f"Parser OK: {p}")

# Test with messy text
text = "blah blah\nPROBABILITIES: [0.22, 0.31, 0.19, 0.28]\nmore text"
p2 = _parse_probabilities(text)
assert p2 is not None
assert abs(sum(p2) - 1.0) < 1e-6
print(f"Parser messy OK: {p2}")

# Test data preparation helpers
import json
from pathlib import Path
from base_computes.game_state import GameState
from settle_process.init_analysis import (
    _settlement_details, _production_by_number,
    _trade_synergies, _open_spots_summary,
    _format_eval_results, _format_starting_hands,
)
from base_computes.init_eval import evaluate_init_board
from base_computes.game_state import compute_starting_hands

# Use sample5 which has 7 settlements
with open("sample5.json") as f:
    gs = GameState.from_json(json.load(f))

print("\n--- Settlement Details ---")
print(_settlement_details(gs))

scores, results = evaluate_init_board(gs)
hands = compute_starting_hands(gs)

print("\n--- Starting Hands ---")
print(_format_starting_hands(hands))

print("\n--- Eval Summary ---")
print(_format_eval_results(scores, results)[:500])

print("\n--- Production by Number ---")
print(_production_by_number(gs))

print("\n--- Trade Synergies ---")
print(_trade_synergies(gs))

print("\n--- Open Spots ---")
print(_open_spots_summary(gs)[:500])

print("\nAll smoke tests passed!")
