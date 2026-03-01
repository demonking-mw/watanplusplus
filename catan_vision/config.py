from pathlib import Path

# ==========================================
# PATHS
# ==========================================
PROJECT_ROOT = Path(__file__).parent
MODEL_PATH = PROJECT_ROOT / "runs" / "catan_yolo8m" / "weights" / "best.pt"
VIZ_DIR = PROJECT_ROOT / "output_visualizations"
JSON_DIR = PROJECT_ROOT / "output_json"

# ==========================================
# DETECTION CONFIG
# ==========================================
CONF_THRESHOLD = 0.5
Y_ROW_THRESHOLD = 60

# ==========================================
# GAME CONSTANTS & MAPPINGS
# ==========================================
# Strict Player Mapping
PLAYER_COLOR_MAP = {"red": 0, "blue": 1, "green": 2, "orange": 3, "black": 4}

RES_ID_OCEAN = 6
PORT_FLAG = -1

# YOLO Class ID to Game Resource ID
YOLO_TO_RES = {0: 1, 6: 5, 17: 4, 35: 2, 36: 3, 37: 0}

# YOLO Class ID to Port Type
YOLO_TO_PORT = {18: 5, 19: 1, 20: 4, 21: 2, 22: 3, 23: 0}

RES_NAMES = {
    0: "Wood",
    1: "Brick",
    2: "Wool",
    3: "Grain",
    4: "Ore",
    5: "Desert",
    6: "Ocean",
}

PORT_NAMES = {
    0: "Port(Wood)",
    1: "Port(Brick)",
    2: "Port(Wool)",
    3: "Port(Grain)",
    4: "Port(Ore)",
    5: "Port(3:1)",
}

CLASS_GROUPS = {
    "hexes": [0, 6, 17, 35, 36, 37],
    "numbers": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    "settlements": [30, 31, 32, 33, 34],
    "cities": [1, 2, 3, 4, 5],
    "roads": [24, 25, 26, 27, 28],
    "robber": [29],
    "ports": [18, 19, 20, 21, 22, 23],
}

# 37-tile Layout Mask (Rows: 4-5-6-7-6-5-4)
TILE_MASK = [
    False,
    False,
    False,
    False,  # Row 0
    False,
    True,
    True,
    True,
    False,  # Row 1
    False,
    True,
    True,
    True,
    True,
    False,  # Row 2
    False,
    True,
    True,
    True,
    True,
    True,
    False,  # Row 3
    False,
    True,
    True,
    True,
    True,
    False,  # Row 4
    False,
    True,
    True,
    True,
    False,  # Row 5
    False,
    False,
    False,
    False,  # Row 6
]
