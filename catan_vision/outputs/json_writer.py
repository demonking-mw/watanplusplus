import json
import os
from .. import config

class JsonWriter:
    @staticmethod
    def save(board, robber_id, output_path):
        output_data = {
            "map": {
                "robber": robber_id,
                "tiles": board.tiles,
                "nodes": board.nodes,
                "edges": board.edges,
            },
            "players": [
                {
                    "id": config.PLAYER_COLOR_MAP[c],
                    "color": c,
                    "public": [0, 0, 0, 0],
                    "res_k": [0, 0, 0, 0, 0],
                    "res_u": [],
                    "devs": [],
                }
                for c in sorted(board.players_detected, 
                                key=lambda x: config.PLAYER_COLOR_MAP[x])
            ],
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)