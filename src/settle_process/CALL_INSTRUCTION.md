# Settlement Process Module

This module handles higher-level orchestration for settlement analysis and bot decision making, often using AI.

## Initialization Analysis (`init_analysis.py`)

Analyzes the initial board state using an LLM to provide strategic insights.

```python
from settle_process import analyze_init_board
from base_computes.game_state import GameState
from ai import AIProvider

# Load game state (should be fully settled for analysis)
gs = GameState.from_json(data)

# Run analysis
report = analyze_init_board(
    gs, 
    provider=AIProvider.OPENAI, 
    model="gpt-4"
)
print(report)
```

## Settlement Bot (`settle_bot.py`)

Orchestrates the process of finding the best settlement spot. It combines:
1.  Heuristic evaluation (`settle_decision`)
2.  Simulation of future turns (`simulate_settle`)
3.  LLM-based evaluation of the resulting board states

```python
import asyncio
from settle_process.settle_bot import find_best_settle

async def run_bot():
    with open("sample.json") as f:
        data = json.load(f)

    # Find best move
    # Returns ((best_settle, best_road), breakdown_text)
    (best_move, breakdown) = await find_best_settle(
        data,
        x=4,            # Number of heuristic options to consider
        ai_cutoff=3,    # Top N outcomes per option to send to AI
        verbose=True
    )
    
    print(f"Best Move: {best_move}")
    print(f"Reasoning:\n{breakdown}")

asyncio.run(run_bot())
```
