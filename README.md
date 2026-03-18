# Watan++ (WPP)

A hybrid AI/ML Catan solver for Colonist.io.

Watan++ combines:
- logic-heavy Catan simulation and evaluation
- LLM-based multi-agent analysis for high-context strategic decisions
- computer vision (YOLOv8 segmentation) to parse board screenshots
- browser-side packet sniffing and extraction utilities for Colonist.io

## What This Project Does

At a high level, the workflow is:

1. Capture game state from Colonist.io (browser sniffer, DOM/WS hooks).
2. Represent the game in a compact HDCS (High-Density Catan State) JSON format.
3. Simulate settlement drafts and evaluate candidate lines.
4. Use fast heuristics plus optional LLM analysis to score and rank settle options.
5. Optionally parse screenshots with the CV pipeline to generate structured board JSON.

## Core Tech Stack

### Languages
- Python (primary)
- JavaScript (browser sniffer)

### AI / LLM
- OpenAI API (default model config: gpt-5-mini)
- Anthropic API
- Google Gemini API

### ML / Vision
- Ultralytics YOLOv8 segmentation
- PyTorch (via ultralytics)
- OpenCV + NumPy + Pillow

### Data Modeling / Validation
- Pydantic v2 for HDCS schemas and invariants

### Networking / Utilities
- requests, httpx, websockets
- python-dotenv

### Testing
- pytest
- script-style test runners in src/tests

## Repository Overview

- src/
  - ai/: provider abstraction and sync/async AI query layer
  - base_computes/: core game state, simulation, settle evaluation, robber prediction
  - settle_process/: orchestrators for init analysis and settle recommendations
  - tests/: script runners and validation tests for core pipelines
  - colonist_sniffer.js: in-browser Colonist.io extractor (exposes window.colonistSniffer)
- catan_vision/
  - training and inference pipeline for board detection/parsing
  - dataset/ in YOLO format
  - processing/ for geometric parsing and projection
  - outputs/ for JSON and debug visualizations
- manual_processing/
  - terminal visualization and board rendering helpers
- info/
  - planning docs and HDCS schema/context notes

## HDCS Data Model (Project Contract)

The project uses a compact, positional JSON schema for game state with strict index conventions:
- resources: [Wood, Brick, Wool, Grain, Ore] => [0..4]
- dev cards: [Knight, VP, Road Building, Year of Plenty, Monopoly]
- map modeled as a tile/node/edge dual-graph for Catan topology

See these docs for full details:
- info/WPP+Planning.md
- info/context.md

## Quick Start

## 1) Install dependencies

From repository root:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## 2) Configure API keys (for LLM-enabled workflows)

You can use environment variables directly, or place them in a root .env file.

Required variables by provider:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GOOGLE_API_KEY

Example .env:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
```

## 3) Sanity-check AI provider wiring

```bash
python test_ai.py
```

## Running the Settlement Solver Pipeline

The most practical entrypoint is the settle bot test runner.

### Recommend best settle + road from sample state

```bash
python src/tests/test_settle_bot.py src/sample5.json
```

Useful options:

```bash
python src/tests/test_settle_bot.py src/sample5.json --provider openai --model gpt-5-mini
python src/tests/test_settle_bot.py src/sample5.json --ai-cutoff 3
python src/tests/test_settle_bot.py src/sample5.json --debug
```

What it does:
- simulates settlement placeouts
- scores top-N placeouts with AI analysis
- scores remaining placeouts with fast algorithmic evaluator
- returns ranked settle+road options

### Run AI init-board analysis directly

```bash
python src/tests/test_init_analysis.py src/sample5.json --provider openai --model gpt-5-mini
```

## Running the Vision Pipeline (catan_vision)

### Train YOLOv8 segmentation model

Before training, update catan_vision/data.yaml path to your local dataset directory.

```bash
python -m catan_vision.train_catan
```

### Run inference on a board screenshot

```bash
python -m catan_vision.main --image /path/to/board.png
```

Expected outputs:
- catan_vision/output_json/catan_map.json
- catan_vision/output_visualizations/*

## Colonist.io Sniffer Usage

File: src/colonist_sniffer.js

Typical usage:
1. Open Colonist.io game in browser.
2. Paste the full script into DevTools Console.
3. Run helper commands from window.colonistSniffer, for example:

```javascript
colonistSniffer.scan()
colonistSniffer.getState()
colonistSniffer.getWSMessages()
colonistSniffer.printState()
```

The sniffer includes multiple extraction strategies:
- WebSocket interception
- Socket/Global state discovery
- DOM probing
- debug helpers for protocol exploration

## Testing

Pytest is available, but this repository also uses script-driven test runners.

Typical commands:

```bash
pytest -q
python src/tests/test_settle_sim.py src/sample5.json
python src/tests/test_robber_pipeline.py src/sample5.json
python src/tests/test_starting_hands.py src/sample5.json
```

Note: some tests/scripts rely on optional API keys or local visualization dependencies.

## Design Notes and Current Scope

Implemented strongly:
- HDCS game-state modeling and validation
- settle simulation/evaluation stack
- AI provider abstraction with async orchestration
- CV-based board parsing workflow
- Colonist browser extraction tooling

Documented/planned in design notes:
- local Flask update_state service for continuous Bayesian state updates
- broader multi-agent game-time orchestration around full turns

## Troubleshooting

- Missing API key errors:
  - ensure provider-specific env vars are set or present in root .env
- Vision model not found:
  - train first or place best.pt at catan_vision/runs/catan_yolo8m/weights/best.pt
- Empty or poor vision outputs:
  - verify catan_vision/data.yaml path and class alignment with catan_vision/config.py
- Sniffer captures no messages:
  - reload game tab and re-inject script early, then trigger game actions and inspect colonistSniffer.getWSMessages()

## License / Attribution

This repository includes an embedded copy of a computer-use preview example under src/gemini-test/computer-use-preview with its own LICENSE and docs.
