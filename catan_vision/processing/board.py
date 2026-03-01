from .. import config


class CatanBoard:
    def __init__(self):
        # Initialize 37 tiles with Ocean
        self.tiles = [[config.RES_ID_OCEAN, 0] for _ in range(37)]
        self.nodes = {}  # Key: "tile1_tile2_tile3", Value: [player_id, type]
        self.edges = {}  # Key: "tile1_tile2", Value: player_id
        self.centers = {}  # Key: tile_id, Value: (cx, cy)
        self.players_detected = set()

    def get_player_id(self, class_name):
        """Extracts color and returns the ID based on the strict mapping."""
        # Splits 'settlement_red' or 'road_blue' to get the color
        if "_" in class_name:
            color = class_name.split("_")[-1].lower()
        else:
            color = "unknown"

        pid = config.PLAYER_COLOR_MAP.get(color, 99)  # 99 for unknown

        if pid != 99:
            self.players_detected.add(color)

        return pid
