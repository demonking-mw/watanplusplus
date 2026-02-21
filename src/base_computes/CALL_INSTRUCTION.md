# Base Computes Module

This module contains core game logic, state management, and heuristic evaluations.

## Game State Management (`game_state.py`)

The `GameState` class is the central data structure for the Catan board.

### Validation & Parsing

The `from_json` method validates the board state, ensuring no illegal adjacent settlements.

```python
import json
from base_computes.game_state import GameState

# Load from JSON
with open("sample.json") as f:
    data = json.load(f)

# Parse and validate
try:
    gs = GameState.from_json(data)
    print(f"Board loaded. Active player: {gs.meta.p_curr}")
except ValueError as e:
    print(f"Validation failed: {e}")
```

### Starting Hands (`starting_hands.py`)

Computes the initial resources for each player based on their second settlement placement.

```python
from base_computes.game_state import GameState, compute_starting_hands

gs = GameState.from_json(data)
hands = compute_starting_hands(gs)

for pid, hand in enumerate(hands):
    # hand is a list of counts [Wood, Brick, Wool, Grain, Ore]
    print(f"Player {pid} starting resources: {hand}")
```

## Settlement Logic

### Settlement Decision (`settle_eval_simple.py`)

Evaluates available settlement spots using heuristics and returns a list of ranked options.

```python
from base_computes.settle_eval_simple import settle_decision

# Get ranked settlement options
# Returns list of ((settle_node, road_edge), probability)
results = settle_decision(gs)

for (settle, road), prob in results:
    print(f"Spot: {settle}, Road: {road}, Score: {gs.settle_scores.get(settle)}, Prob: {prob}")
```

### Settlement Simulation (`settle_sim.py`)

Simulates the draft phase to predict future board states.

```python
from base_computes.settle_sim import simulate_settle

# Simulate draft (x=top options to consider, max_window=max branches)
# Returns list of (option, placeouts) where placeouts is list of (board, prob)
results = simulate_settle(gs, x=4, max_window=20)

for (option_settle, option_road), placeouts in results:
    print(f"Option {option_settle}: {len(placeouts)} possible future outcomes")
```

## Board Evaluation (`init_eval.py`)

Evaluates a fully settled board state to determine player strength and strategy.

```python
from base_computes.init_eval import evaluate_init_board

# evaluate_init_board expects a GameState where initial placements are done
scores, results = evaluate_init_board(completed_gs)

print(f"Normalized Scores: {scores}")
for r in results:
    print(f"Player {r.player_id}: Raw Prod {r.raw_prod}, Strategy Index {r.strategy_index}")
```

## Robber Prediction (`robber_predict.py`)

Predicts where each player might move the robber.

```python
from base_computes.robber_predict import predict_robber

# Returns list of lists: result[player_id] = list of (tile_id, probability)
predictions = predict_robber(gs)

for pid, prefs in enumerate(predictions):
    print(f"Player {pid} robber preferences:")
    for tile_id, prob in prefs:
        print(f"  Tile {tile_id}: {prob:.2f}")
```
