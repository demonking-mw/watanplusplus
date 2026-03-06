# `catan_vision/` – Catan Board Detection & Parsing

This folder contains the **computer-vision pipeline** for Watan++. It uses a YOLOv8m segmentation model to detect and parse a Colonist.io Catan board from a screenshot, converting raw pixel data into a structured JSON board representation consumed by the rest of the Watan++ AI stack.

**Pipeline summary:**

```
Screenshot → YOLOv8 Segmentation → Detection Parser → Board Processor → catan_map.json
```

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Installation & Environment](#2-installation--environment)
3. [Git LFS – Dataset Images](#3-git-lfs--dataset-images)
4. [Dataset Setup (`data.yaml`)](#4-dataset-setup-datayaml)
5. [Model Setup](#5-model-setup)
6. [Training the Model](#6-training-the-model-train_catanpy)
7. [Running Inference](#7-running-inference-mainpy)
8. [Output & Visualizations](#8-output--visualizations)
9. [End-to-End Quick Start](#9-end-to-end-quick-start)
10. [Configuration Reference (`config.py`)](#10-configuration-reference-configpy)
11. [How `catan_vision` Fits Into Watan++](#11-how-catan_vision-fits-into-watan)

---

## 1. Folder Structure

```
catan_vision/
├── config.py               # Global paths, class index mappings, constants
├── data.yaml               # YOLOv8 dataset config — YOU MUST EDIT THIS
├── train_catan.py          # Training script (YOLOv8m segmentation)
├── main.py                 # Inference entry point → exports JSON + visuals
│
├── dataset/                # YOLOv8-format labeled dataset
│   ├── train/
│   │   ├── images/
│   │   └── labels/
│   ├── val/
│   │   ├── images/
│   │   └── labels/
│   └── test/               # (optional)
│
├── runs/                   # Created by YOLO during training (gitignored)
│   └── catan_yolo8m/
│       └── weights/
│           ├── best.pt     ← model used by main.py
│           └── last.pt
│
├── processing/             # Core detection → board-state logic
│   ├── board_processor.py  # Orchestrates YOLO inference + grid projection
│   ├── detection_parser.py # Converts raw YOLO masks to tile/node/edge data
│   └── ...
│
├── outputs/                # Writers called by main.py
│   ├── json_writer.py      # Saves catan_map.json
│   └── visualizer.py       # Saves debug images
│
└── visualizations/         # Generated output directory (gitignored)
    ├── catan_map.json       ← structured board JSON
    └── *.png               ← debug overlay images
```

### Key file notes

| File | Purpose |
|---|---|
| `config.py` | Single source of truth for paths (`MODEL_PATH`, `VIZ_DIR`, `JSON_DIR`) and all class-index mappings (resources, settlements, roads, ports, etc.). Edit here if class indices change or new player colours/mappings etc. **Note that data.yaml will also need changing if so.** |
| `data.yaml` | Tells YOLO where your dataset lives. **Must be updated to your local path before training.** |
| `train_catan.py` | Runs YOLOv8m segmentation training. Saves weights under `runs/catan_yolo8m/weights/`. |
| `main.py` | Accepts `--image` path, runs the full pipeline, writes JSON + visuals. |

---

## 2. Installation & Environment

All dependencies for the entire Watan++ project live in a **single `requirements.txt`** at the project root.

```bash
# From the project root
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

Key dependencies used by `catan_vision`:

- `ultralytics` — YOLOv8 framework (also installs `torch` automatically)
- `opencv-python` — image I/O and processing
- `numpy` — array operations

> **PyTorch device support:**
> - **macOS (Apple Silicon):** Metal (MPS) is used automatically.
> - **Linux/Windows with NVIDIA GPU:** Install the CUDA-enabled PyTorch wheel for best performance — see [pytorch.org/get-started](https://pytorch.org/get-started/locally/).
> - **CPU fallback:** Works on any machine, but training will be slow.

---

## 3. Git LFS – Dataset Images

The dataset images in `dataset/` are tracked with **Git LFS** (Large File Storage). Without it, you will only download pointer files instead of the actual images.

```bash
# Install Git LFS (once per machine)
# macOS
brew install git-lfs

# Ubuntu/Debian
sudo apt install git-lfs

# Windows — download installer from https://git-lfs.com

# Enable LFS in the repo (once per clone)
git lfs install

# Pull all LFS files
git lfs pull
```

Verify images downloaded correctly — files in `dataset/.../images` should be `.jpg` files, not tiny text pointer files.

More info: [https://git-lfs.com](https://git-lfs.com)

---

## 4. Dataset Setup (`data.yaml`)

**Before training**, you must update `data.yaml` to point to your local dataset path. The current file contains a hard-coded path from the original author's machine.

Open `catan_vision/data.yaml` and update the `path` field:

```yaml
# catan_vision/data.yaml

path: /ABSOLUTE/PATH/TO/watanplusplus/catan_vision/dataset   # <-- CHANGE THIS

train: train/images
val:   val/images
test:  test/images

nc: 38   # number of classes

names:
  0: wood_tile
  1: brick_tile
  # ... (do not change names/indices — they must match config.py)
```

**Rules:**
- `path` must be an **absolute path** to the directory containing `train/`, `val/`, `test/`.
- `train`, `val`, `test` values are **relative** to `path`.
- Labels directory must mirror the images directory (`.txt` files with matching names).
- **Do not change class indices or names** — they are tightly coupled to `config.py`.

---

## 5. Model Setup

At runtime, `main.py` loads a trained model from:

```
catan_vision/runs/catan_yolo8m/weights/best.pt
```

This path is defined in [`config.py`](config.py):

```python
PROJECT_ROOT = Path(__file__).parent
MODEL_PATH = PROJECT_ROOT / "runs" / "catan_yolo8m" / "weights" / "best.pt"
```

> **Note:** `runs/` is gitignored. You must either train the model yourself (§6) or manually place a downloaded `best.pt` at this path (see below).

---

### Option A — Train the model yourself (see §6)

After training completes, YOLO automatically saves to:
```
catan_vision/runs/catan_yolo8m/weights/best.pt
```
No extra steps needed if `RUN_NAME = "catan_yolo8m"` in `train_catan.py` (this is the default).

---

### Option B — Use a downloaded / pre-trained model

If you received a `best.pt` file externally:

```bash
# Create the expected directory structure
mkdir -p catan_vision/runs/catan_yolo8m/weights

# Copy your model into place
cp /path/to/your/best.pt catan_vision/runs/catan_yolo8m/weights/best.pt
```

The file **must** be named `best.pt` at that exact path, or update `MODEL_PATH` in `config.py` accordingly.

---

## 6. Training the Model (`train_catan.py`)

> ⏱ **Training typically takes 1–4 hours** depending on your hardware and epoch count.  
> Default: **175 epochs** on YOLOv8m segmentation.

### Prerequisites

- `data.yaml` updated with your local dataset path (§4).
- No base model download needed — `train_catan.py` uses `MODEL_SIZE = "yolov8m-seg.pt"` (a built-in Ultralytics alias). On first run Ultralytics will automatically download `yolov8m-seg.pt` into its global cache.

### Run training

```bash
# From the project root, with your venv active
cd /path/to/watanplusplus
python -m catan_vision.train_catan
```

Or from inside `catan_vision/`:

```bash
cd catan_vision
python train_catan.py
```

### What happens

1. Loads `yolov8m-seg.pt` (base segmentation model).
2. Trains on the dataset described in `data.yaml`.
3. Saves checkpoints every 10 epochs under `runs/catan_yolo8m/`.
4. On completion, prints final mAP metrics and the path to `best.pt`.

### Training configuration

Edit these constants at the top of [`train_catan.py`](train_catan.py) to adjust:

```python
EPOCHS     = 175    # number of training epochs
IMAGE_SIZE = 640    # input resolution (px)
BATCH_SIZE = 4      # lower if you run out of memory
RUN_NAME   = "catan_yolo8m"   # must match MODEL_PATH in config.py
```

> If you change `RUN_NAME`, also update `MODEL_PATH` in `config.py` to match, otherwise `main.py` won't find the model.

### Expected output

```
✅ Training Complete!
mAP50 (Box):       0.XXX
mAP50-95 (Box):    0.XXX
mAP50 (Mask):      0.XXX
mAP50-95 (Mask):   0.XXX
💾 Model saved to: catan_vision/runs/catan_yolo8m/weights/best.pt
```

---

## 7. Running Inference (`main.py`)

Once you have a trained model at `runs/catan_yolo8m/weights/best.pt`, run the full vision pipeline on any board screenshot.

### Usage

```bash
# From the project root (recommended)
python -m catan_vision.main --image /path/to/your/board_screenshot.png
```

Or from inside `catan_vision/`:

```bash
cd catan_vision
python main.py --image /path/to/your/board_screenshot.png
```

### Example

```bash
# Using an absolute path
python -m catan_vision.main --image /Users/yourname/Desktop/catan_board.png

# Using a relative path from project root
python -m catan_vision.main --image catan_vision/dataset/test/images/board10.png
```

### What `main.py` does step by step

1. Validates the input image path exists.
2. Loads the trained YOLO model from `config.MODEL_PATH`.
3. Runs YOLOv8 segmentation inference on the image.
4. Passes detections to `BoardProcessor`, which:
   - Parses tile types, number tokens, and positions.
   - Projects detections onto the 37-hex Catan grid topology.
   - Identifies settlements, cities, roads, and robber position.
5. Writes `catan_map.json` to `output_json/`.
6. Saves debug overlay images to `visualizations/`.

### Expected output

```
Loading model from: catan_vision/runs/catan_yolo8m/weights/best.pt
Processing image: /path/to/board_screenshot.png
✅ Board JSON saved → catan_vision/visualizations/catan_map.json
✅ Visualizations saved → catan_vision/visualizations/
```

---

## 8. Output & Visualizations

All output is written to two directories under `catan_vision/` (both gitignored — safe to delete and regenerate).

| Directory | Contents |
|---|---|
| `output_json/` | `catan_map.json` — structured HDCS board JSON consumed by the AI engine |
| `output_visualizations/` | Debug images (see table below) |

| Image file | Description |
|---|---|
| `board_overview.jpg` | Full board with **all** detection overlays |
| `hexes_only.jpg`, `roads_only.jpg`, etc. | Per-class group detection images |
| `ocean_tiles_debug.jpg` | Geometric hex-grid projection overlay |

### `catan_map.json` structure

The JSON represents the Catan board state in HDCS format:
- **37 hex tiles** (IDs 0–36, row-major) — each with `[ResourceID, NumberToken]`
- **Nodes** (settlement intersections) — keyed by sorted tile-triple `"T1_T2_T3"`
- **Edges** (roads) — keyed by sorted tile-pair `"T1_T2"`
- **Ports** — node IDs mapped to port type
- **Robber** tile ID

See [`info/WPP+Planning.md`](../info/WPP+Planning.md) for full HDCS schema documentation.

---

## 9. End-to-End Quick Start

Follow these steps in order for a clean setup from scratch.

### Step 1 — Clone and install

```bash
git clone <repo-url>
cd watanplusplus

# Pull dataset images via Git LFS
git lfs install
git lfs pull

# Set up Python environment
python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Configure dataset path

Edit `catan_vision/data.yaml`:

```yaml
path: /absolute/path/to/watanplusplus/catan_vision/dataset
```

### Step 3 — Get a model

**Option A: Train from scratch** *(1–4 hours)*

```bash
python -m catan_vision.train_catan
```

**Option B: Use a downloaded model**

```bash
mkdir -p catan_vision/runs/catan_yolo8m/weights
cp /path/to/downloaded/best.pt catan_vision/runs/catan_yolo8m/weights/best.pt
```

### Step 4 — Run inference

```bash
python -m catan_vision.main --image /path/to/board_screenshot.png
```

### Step 5 — Check output

```bash
ls catan_vision/output_json/
# catan_map.json

ls catan_vision/output_visualizations/
# board_overview.jpg   hexes_only.jpg   roads_only.jpg   ...
```

### Step 6 — Visualize the board JSON in the terminal

`manual_processing/visualize_board.py` renders the parsed board as a colour-coded ASCII map directly in your terminal. Pass it the path to `catan_map.json` output by Step 4.

```bash
# Basic board view
python manual_processing/visualize_board.py catan_vision/output_json/catan_map.json
```

```bash
# With settlement evaluation scores overlaid on every valid node
python manual_processing/visualize_board.py catan_vision/output_json/catan_map.json --scores
```

What you'll see:
- Every tile colour-coded by resource (green = wood, red = brick, yellow = grain, etc.)
- Number tokens shown on each land tile (red for 6/8, white otherwise)
- Port locations and trade ratios (2:1 or 3:1)
- Robber position highlighted
- `--scores`: settlement desirability score on every valid intersection node

---

## 10. Configuration Reference (`config.py`)

[`config.py`](config.py) is the single source of truth for all paths and class mappings. Edit this file if:

- You move the model to a different path.
- You retrain with a different run name.
- Class indices in `data.yaml` change (requires retraining too).

Key constants:

```python
PROJECT_ROOT = Path(__file__).parent

# Model
MODEL_PATH = PROJECT_ROOT / "runs" / "catan_yolo8m" / "weights" / "best.pt"

# Output directories
VIZ_DIR  = PROJECT_ROOT / "output_visualizations"
JSON_DIR = PROJECT_ROOT / "output_json"

# Class index mappings (must match data.yaml)
# e.g. TILE_CLASS_MAP, PORT_CLASS_MAP, SETTLEMENT_CLASS_MAP, etc.
```

---

## 11. How `catan_vision` Fits Into Watan++

```
Colonist.io Screenshot
        ↓
  catan_vision/main.py
  ┌─────────────────────────────────────┐
  │  YOLOv8 segmentation                │
  │    → tiles, numbers, ports          │
  │    → settlements, cities            │
  │    → roads, robber                  │
  │  processing/ (grid projection)      │
  │    → 37-hex board topology          │
  └─────────────────────────────────────┘
        ↓
  visualizations/catan_map.json  (HDCS board state)
        ↓
  Watan++ AI Engine
  (HDCS state → Bayesian updates → decision making)
```

- **`catan_vision`** is the CV front-end that converts images to machine-readable board state.
- The output `catan_map.json` feeds into the `/update_state` Flask endpoint and the AI decision engine.
- The sniffer (`src/colonist_sniffer.js`) handles live game-state events; `catan_vision` handles the visual board layout (tile resources, numbers, port positions) which are typically read once at game start.
