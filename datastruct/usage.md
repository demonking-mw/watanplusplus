# Catan Model Usage Guide

> **Purpose**: This document is for frontend developers integrating with the Catan data model for **data input** and **AI/ML model development**.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Classes Overview](#core-classes-overview)
3. [Tensor Dimensions Reference](#tensor-dimensions-reference)
4. [Action Space Encoding](#action-space-encoding)
5. [Input/Output Interfaces](#inputoutput-interfaces)
6. [GameTracker API](#gametracker-api)
7. [Data Collection for Training](#data-collection-for-training)
8. [Adjacency Matrices for GNNs](#adjacency-matrices-for-gnns)
9. [Code Examples](#code-examples)

---

## Quick Start

```python
from datastruct import GameTracker, TensorEncoder, ActionGenerator

# Initialize game tracker
tracker = GameTracker(num_players=4)
tracker.board.setup_random_board()
tracker.start_ghost_mode()

# Get state tensor for neural network
state_tensor = TensorEncoder.to_full_tensor(
    tracker.board,
    tracker.players,
    tracker.game_state,
    observer_id=1  # Player 1's perspective (partial observation)
)

# Get legal action mask
action_mask = ActionGenerator.get_legal_action_mask(
    tracker.board,
    tracker.players,
    tracker.game_state,
    player_id=1
)
```

---

## Core Classes Overview

| Class | Purpose | Primary Use |
|-------|---------|-------------|
| `GameTracker` | Main orchestrator | Data input, state management |
| `TensorEncoder` | State → Tensor conversion | Neural network input |
| `ActionGenerator` | Legal action computation | Action masking for RL |
| `Board` | Graph structure | Topology, adjacency matrices |
| `Player` | Player state | Resources, buildings, VPs |
| `GameState` | Turn/phase tracking | Game flow control |
| `Action` | Action encoding | Discrete action space |

---

## Tensor Dimensions Reference

### Full State Tensor

**Total Dimension**: `1170` floats

| Component | Shape | Flattened Size | Description |
|-----------|-------|----------------|-------------|
| Board (Tiles) | `(19, 8)` | 152 | Terrain + token + robber |
| Vertices | `(54, 15)` | 810 | Owner + building + port |
| Edges | `(72, 5)` | 360 | Road ownership |
| Players (×4) | `(4, 15)` | 60 | Resources, VPs, buildings |
| Game State | `(20,)` | 20 | Phase, turn, awards |

### Board Tensor — `(19, 8)`

| Index | Feature | Range | Notes |
|-------|---------|-------|-------|
| 0-5 | Terrain one-hot | {0, 1} | forest, hill, pasture, field, mountain, desert |
| 6 | Token number | [0, 1] | Normalized: `token_num / 12.0` |
| 7 | Has robber | {0, 1} | Binary flag |

### Vertex Tensor — `(54, 15)`

| Index | Feature | Range | Notes |
|-------|---------|-------|-------|
| 0-4 | Owner one-hot | {0, 1} | [unoccupied, P1, P2, P3, P4] |
| 5-7 | Building one-hot | {0, 1} | [none, settlement, city] |
| 8-14 | Port one-hot | {0, 1} | [none, 3:1, wood, brick, sheep, wheat, ore] |

### Edge Tensor — `(72, 5)`

| Index | Feature | Range | Notes |
|-------|---------|-------|-------|
| 0-4 | Owner one-hot | {0, 1} | [unoccupied, P1, P2, P3, P4] |

### Player Tensor — `(15,)` per player

| Index | Feature | Normalization | Notes |
|-------|---------|---------------|-------|
| 0-4 | Resources | `/19.0` | [wood, brick, sheep, wheat, ore] |
| 5-9 | Dev cards | `/25.0` | [knight, vp, road_build, year_plenty, monopoly] |
| 10 | Victory Points | `/10.0` | Public VP only |
| 11 | Knights played | `/14.0` | For Largest Army |
| 12 | Settlement count | `/5.0` | MAX_SETTLEMENTS = 5 |
| 13 | City count | `/4.0` | MAX_CITIES = 4 |
| 14 | Road count | `/15.0` | MAX_ROADS = 15 |

### GameState Tensor — `(20,)`

| Index | Feature | Range | Notes |
|-------|---------|-------|-------|
| 0-7 | Phase one-hot | {0, 1} | 8 phases |
| 8-11 | Current player one-hot | {0, 1} | P1-P4 |
| 12 | Turn number | `/100.0` | Normalized |
| 13-14 | Dice result | `/6.0` | Die 1 and Die 2 |
| 15 | Longest road holder | `/4.0` | Player ID or 0 |
| 16 | Longest road length | `/15.0` | Max 15 roads |
| 17 | Largest army holder | `/4.0` | Player ID or 0 |
| 18 | Largest army size | `/14.0` | Max 14 knights |
| 19 | Game over flag | {0, 1} | Binary |

---

## Action Space Encoding

**Total Action Space Size**: `300`

### Action Index Mapping

| Action Type | Index Range | Count | `target_id` Meaning |
|-------------|-------------|-------|---------------------|
| `ROLL_DICE` | 0 | 1 | — |
| `BUILD_SETTLE` | 1–54 | 54 | Vertex index (0-53) |
| `BUILD_ROAD` | 55–126 | 72 | Edge index (0-71) |
| `BUILD_CITY` | 127–180 | 54 | Vertex index (owned) |
| `BUY_DEV` | 181 | 1 | — |
| `MOVE_ROBBER` | 182–200 | 19 | Tile index (0-18) |
| `END_TURN` | 201 | 1 | — |
| `STEAL` | 202–205 | 4 | Player ID (1-4) |
| `PLAY_KNIGHT` | 206 | 1 | — |
| `PLAY_ROAD_BUILD` | 207 | 1 | — |
| `PLAY_YEAR_PLENTY` | 208 | 1 | — |
| `PLAY_MONOPOLY` | 209 | 1 | — |
| `DISCARD` | 210 | 1 | — |
| `TRADE_BANK` | 211 | 1 | — |
| `TRADE_OFFER` | 212 | 1 | — |
| `TRADE_ACCEPT` | 213 | 1 | — |
| `TRADE_REJECT` | 214 | 1 | — |

### Action Encoding/Decoding

```python
from datastruct import Action, ActionType

# Encode action → index
action = Action(ActionType.BUILD_SETTLE, target_id=10)
action_id = action.to_index()  # Returns 11 (1 + 10)

# Decode index → action
action = Action.from_index(55)  # BUILD_ROAD at edge 0
```

### Legal Action Mask

```python
# Returns np.array of shape (300,) with 1s for legal actions
mask = ActionGenerator.get_legal_action_mask(board, players, game_state, player_id)

# Use with policy network output
logits = model(state_tensor)
masked_logits = logits * mask - 1e9 * (1 - mask)  # Mask illegal actions
action_probs = softmax(masked_logits)
```

---

## Input/Output Interfaces

### State Input Interface

| Method | Output Shape | Use Case |
|--------|--------------|----------|
| `TensorEncoder.to_full_tensor(...)` | `(1170,)` | Full state vector |
| `TensorEncoder.board_to_tensor(board)` | `(19, 8)` | Board-only features |
| `TensorEncoder.vertices_to_tensor(board)` | `(54, 15)` | Vertex features |
| `TensorEncoder.edges_to_tensor(board)` | `(72, 5)` | Edge features |
| `TensorEncoder.player_to_tensor(player)` | `(15,)` | Single player |
| `TensorEncoder.gamestate_to_tensor(gs)` | `(20,)` | Game phase/turn |

### Observation vs Full State

```python
# God's view (full information) — for MCTS simulation
full_state = TensorEncoder.to_full_tensor(board, players, game_state, observer_id=None)

# Player's view (partial observation) — for training
observation = TensorEncoder.to_full_tensor(board, players, game_state, observer_id=1)
```

> **Note**: Opponent hands use `UFloat` mean values (probabilistic estimates) when `observer_id` is set.

---

## GameTracker API

### Initialization

```python
tracker = GameTracker(num_players=4)
tracker.board.setup_random_board()  # Random tile/token placement
tracker.start_ghost_mode()           # Begin tracking
```

### Data Input Methods

| Method | Parameters | Returns | Phase |
|--------|------------|---------|-------|
| `enter_dice_roll(die1, die2)` | Two ints (1-6) | Dict with resources | ROLL |
| `enter_build_settlement(player_id, vertex_idx)` | Player (1-4), Vertex (0-53) | bool | SETUP/MAIN |
| `enter_build_road(player_id, edge_idx)` | Player (1-4), Edge (0-71) | bool | SETUP/MAIN |
| `enter_build_city(player_id, vertex_idx)` | Player (1-4), Vertex (0-53) | bool | MAIN |
| `enter_move_robber(tile_idx, steal_from?, resource?)` | Tile (0-18), optional steal | bool | ROBBER |

### Phase Flow

```
SETUP_SETTLE → SETUP_ROAD → ... (repeat for all players)
    ↓
ROLL → [DISCARD if 7] → [ROBBER if 7] → MAIN → END
```

### Phase Enum Values

```python
from datastruct.enums import Phase

Phase.SETUP_SETTLE   # Initial settlement placement
Phase.SETUP_ROAD     # Initial road placement
Phase.ROLL           # Must roll dice
Phase.DISCARD        # Must discard (>7 cards on 7)
Phase.ROBBER         # Must move robber
Phase.MAIN           # Build, trade, play dev
Phase.TRADE          # Active trade negotiation
Phase.END            # Turn complete
```

---

## Data Collection for Training

### Action History

```python
# After game, retrieve all actions taken
for record in tracker.action_history:
    print(f"Turn {record.turn}: Player {record.player_id} → {record.action.action_type}")
    if record.dice_result:
        print(f"  Dice: {record.dice_result}")
```

### ActionRecord Structure

```python
@dataclass
class ActionRecord:
    turn: int                              # Turn number
    player_id: int                         # Player who acted
    action: Action                         # Action taken
    dice_result: Optional[Tuple[int, int]] # Dice if ROLL_DICE
    timestamp: Optional[float]             # Optional timestamp
```

### Training Data Pipeline

```python
# Collect (state, action, reward) tuples
training_data = []

for step in game_steps:
    state = TensorEncoder.to_full_tensor(board, players, game_state, observer_id=step.player)
    action_mask = ActionGenerator.get_legal_action_mask(board, players, game_state, step.player)
    action_id = step.action.to_index()
    
    training_data.append({
        'state': state,           # (1170,)
        'action_mask': action_mask,  # (300,)
        'action': action_id,      # int
        'reward': step.reward     # float
    })
```

---

## Adjacency Matrices for GNNs

### Pre-computed Topologies

```python
board = tracker.board

# Tile-to-Tile adjacency — shape (19, 19)
tile_adj = board.tile_adj

# Vertex-to-Vertex adjacency — shape (54, 54)
vertex_adj = board.vertex_adj

# Tile-Vertex incidence — shape (19, 54)
tile_vertex = board.tile_vertex_inc

# Vertex-Edge incidence — shape (54, 72)
vertex_edge = board.vertex_edge_inc
```

### GNN Input Example

```python
import torch
from torch_geometric.data import Data

# Node features (vertices)
x = TensorEncoder.vertices_to_tensor(board)  # (54, 15)

# Edge index from adjacency
edge_index = torch.tensor(board.vertex_adj.nonzero(), dtype=torch.long)

data = Data(x=torch.tensor(x), edge_index=edge_index)
```

---

## Code Examples

### Example 1: Setup Game and Input Moves

```python
from datastruct import GameTracker

tracker = GameTracker(num_players=4)
tracker.board.setup_random_board()
tracker.start_ghost_mode()

# Setup phase: Player 1 places settlement at vertex 20
tracker.enter_build_settlement(player_id=1, vertex_idx=20)
tracker.game_state.phase = Phase.SETUP_ROAD

# Player 1 places road at edge 30
tracker.enter_build_road(player_id=1, edge_idx=30)
```

### Example 2: Generate State Tensor for Model

```python
from datastruct import TensorEncoder

# Get normalized state tensor
state = TensorEncoder.to_full_tensor(
    tracker.board,
    tracker.players,
    tracker.game_state,
    observer_id=1
)

print(f"State shape: {state.shape}")  # (1170,)
print(f"State dtype: {state.dtype}")  # float32
```

### Example 3: Get Legal Actions and Apply Mask

```python
from datastruct import ActionGenerator
import numpy as np

# Get legal action mask
mask = ActionGenerator.get_legal_action_mask(
    tracker.board,
    tracker.players, 
    tracker.game_state,
    player_id=1
)

# Get legal action objects
legal_actions = ActionGenerator.get_legal_actions(
    tracker.board,
    tracker.players,
    tracker.game_state,
    player_id=1
)

print(f"Legal actions count: {mask.sum()}")
for action in legal_actions[:5]:
    print(f"  {action.action_type.value} → index {action.to_index()}")
```

### Example 4: Compute Longest Road

```python
# After roads are built, compute longest road
for player_id in range(1, 5):
    length = tracker.board.compute_longest_road(player_id)
    print(f"Player {player_id} longest road: {length}")
```

---

## Constants Reference

```python
from datastruct.constants import (
    NUM_TILES,          # 19
    NUM_VERTICES,       # 54
    NUM_EDGES,          # 72
    ACTION_SPACE_SIZE,  # 300
    
    RESOURCE_TYPES,     # ['wood', 'brick', 'sheep', 'wheat', 'ore']
    DEV_TYPES,          # ['knight', 'vp', 'road_build', 'year_plenty', 'monopoly']
    
    COST_ROAD,          # {'wood': 1, 'brick': 1}
    COST_SETTLE,        # {'wood': 1, 'brick': 1, 'sheep': 1, 'wheat': 1}
    COST_CITY,          # {'wheat': 2, 'ore': 3}
    COST_DEV,           # {'sheep': 1, 'wheat': 1, 'ore': 1}
    
    MAX_SETTLEMENTS,    # 5
    MAX_CITIES,         # 4
    MAX_ROADS,          # 15
)
```

---

## Summary: Integration Checklist

- [ ] Import `GameTracker`, `TensorEncoder`, `ActionGenerator`
- [ ] Initialize tracker with `GameTracker(num_players=4)`
- [ ] Setup board via `tracker.board.setup_random_board()` or `setup_fixed_board()`
- [ ] Use `enter_*` methods for data input
- [ ] Get state tensor: `TensorEncoder.to_full_tensor()` → shape `(1170,)`
- [ ] Get action mask: `ActionGenerator.get_legal_action_mask()` → shape `(300,)`
- [ ] Access adjacency matrices via `board.tile_adj`, `board.vertex_adj`, etc.
- [ ] Retrieve training data from `tracker.action_history`
