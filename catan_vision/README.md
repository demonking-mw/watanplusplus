# `catan_vision/` – Catan Board Detection & Parsing

This folder contains the **computer-vision pipeline** for Watan++:

- Train a YOLOv8-segmentation model to detect a Colonist.io Catan board.
- Run inference on screenshots and convert detections into a structured board JSON.
- Produce debug visualizations for inspection.

The output JSON is consumed by the rest of the Watan++ stack as the visual front‑end.

---

## 1. Folder Overview

Key files and directories:

- `config.py`  
  Global paths and constants (model path, input image, class mappings, etc.).
  Any changes to board attribute (i.e. settlement colours, resources, ports etc.) index mapping would require editing this file

- `data.yaml`  
  YOLOv8 dataset configuration. **You must edit this to point to your local dataset.**

- `train_catan.py`  
  Training script for YOLOv8m segmentation on the Catan dataset.

- `main.py`  
  Entry point for running inference on a single board image and exporting JSON + visuals.

- `dataset/`  
  YOLOv8-style dataset (images + labels). This is **not** committed fully to the repo.

- `models/`  
  Base YOLO weights, e.g. `yolov8m-seg.pt`.

- `runs/`  
  YOLO output directory. Trained models go here, in particular:
  - `runs/catan_yolo8m/weights/best.pt` (used by `config.MODEL_PATH`).

- `outputs/`  
  Code for saving JSON and visualizations (used by `main.py`).

- `processing/`  
  Core logic for parsing YOLO detections and projecting them onto the Catan grid:
  - `board_processor.py`
  - `detection_parser.py`
  - (and related helpers)

- `visualizations/`  
  Generated debug images and exported JSON (e.g. `catan_map.json`).

---

## 2. Installation & Environment

From the **project root** (the folder that contains `requirements.txt`):

```bash
# Create / activate your virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate

# Install dependencies for the whole repo (includes catan_vision)
pip install -r requirements.txt
```

`catan_vision` uses:

- `ultralytics` (YOLOv8)
- `torch`
- standard Python scientific / CV stack

Make sure you have a working PyTorch install for your platform (CPU, CUDA, or MPS).

---

## 3. Dataset Setup (`data.yaml`)

The file `catan_vision/data.yaml` must point to the **local path** of your dataset.

Open `data.yaml` and replace the current hard‑coded paths (which point to the original author’s machine) with your own. A typical `data.yaml` looks like:

```yaml
# filepath: /Users/jocex/Projects/watanplusplus/catan_vision/data.yaml
# ...existing code...
path: /ABSOLUTE/PATH/TO/YOUR/catan_vision/dataset  # <-- CHANGE THIS

train: train/images
val: val/images
test: test/images

names:
  0: brick
  1: city_blue
  # ...
# ...existing code...
```
