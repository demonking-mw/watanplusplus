# Board Visualization — Usage Guide

> Source: `manual_processing/visualize_board.py`
> Used by: `src/tests/test_base_data.py`, `src/tests/test_settle_decision.py`, `src/tests/test_robber_pipeline.py`

## Overview

Renders a Catan board state to the terminal as colored ASCII art. Supports two modes:
- **Low-level**: create a `Canvas`, call `draw_board()`, then `canvas.render()`.
- **High-level**: call `render_board()` for a one-shot print (includes legend and player summary).

---

## Imports

```python
from manual_processing.visualize_board import Canvas, draw_board, render_board, Colors
```

If calling from `src/tests/`, add both `src/` and the repo root to `sys.path`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))       # src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..")) # repo root
```

---

## High-Level: `render_board()`

The simplest way to visualize a board. Prints the full board with legend and player table.

```python
from base_computes import GameState
from manual_processing.visualize_board import render_board

gs = GameState.from_json(data)
render_board(gs)
```

### With Settlement Scores

If you've run `gs.evaluate_all_settlements()` first, pass `show_scores=True` to overlay evaluation scores on every valid node:

```python
gs.evaluate_all_settlements()
render_board(gs, show_scores=True)
```

### Parameters

| Parameter     | Type                    | Default | Description                                      |
|---------------|-------------------------|---------|--------------------------------------------------|
| `game_state`  | `GameState` or raw dict | *(req)* | The board state to render.                       |
| `show_scores` | `bool`                  | `False` | Overlay settlement scores (needs `settle_scores`).|

---

## Low-Level: `Canvas` + `draw_board()`

For more control (e.g., custom canvas size or post-processing):

```python
from base_computes import GameState
from manual_processing.visualize_board import Canvas, draw_board, Colors

gs = GameState.from_json(data)

canvas = Canvas(130, 40)       # width=130 chars, height=40 rows
draw_board(canvas, gs)
canvas.render()                # prints to stdout
```

---

## Helper Constants

The module also exports player display constants useful for custom output:

```python
from manual_processing.visualize_board import PLAYER_NAMES, PLAYER_COLORS, Colors

# PLAYER_NAMES = ["Red", "Blue", "White", "Orange"]
# PLAYER_COLORS = [ANSI color codes for each player]
# Colors.BOLD, Colors.RESET, Colors.SCORE_HIGH, etc.
```
