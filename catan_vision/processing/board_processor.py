from .detection_parser import DetectionParser
from .grid_projection import GridProjector
from .board import CatanBoard
import config


class BoardProcessor:
    def __init__(self, model_path):
        self.parser = DetectionParser(model_path)
        self.projector = GridProjector()
        # We store the latest board state here
        self.board = None
        self.dx = 0
        self.dy = 0

    def process_image(self, img_path):
        self.board = CatanBoard()

        # 1. Parse Image
        raw, yolo_results = self.parser.parse(img_path)

        # 2. Build Grid Geometry
        land_rows = self.projector.build_layout(raw["hex"], raw["num"])

        # Fill land tiles into board
        flat_land = [t for r in land_rows for t in r]
        ptr = 0
        for i in range(37):
            if config.TILE_MASK[i] and ptr < len(flat_land):
                t = flat_land[ptr]
                self.board.tiles[i] = [
                    config.YOLO_TO_RES.get(t["yolo_id"], config.RES_ID_OCEAN),
                    t["number"],
                ]
                self.board.centers[i] = t["center"]
                ptr += 1

        # 3. Project Oceans & Ports
        oceans, self.dx, self.dy = self.projector.project_oceans(land_rows)
        self.board.centers.update(oceans)

        self._map_ports(raw["port"], oceans)

        # 4. Map Game Pieces (Settlements/Roads)
        self._map_settlements(raw["build"])
        self._map_roads(raw["road"])

        # 5. Robber
        rid = 18  # Default desert
        if raw["robber"]:
            rid = min(
                self.board.centers,
                key=lambda k: self.projector.get_dist(
                    raw["robber"], self.board.centers[k]
                ),
            )

        return self.board, yolo_results, rid

    def _map_ports(self, raw_ports, oceans):
        avail_oceans = set(oceans.keys())
        # Sort ports by confidence
        sorted_ports = sorted(raw_ports, key=lambda x: x["conf"], reverse=True)

        for p in sorted_ports:
            if not avail_oceans:
                break

            # Find closest available ocean tile
            bid = min(
                avail_oceans,
                key=lambda tid: self.projector.get_dist(p["center"], oceans[tid]),
            )

            if bid is not None:
                self.board.tiles[bid] = [p["res_id"], config.PORT_FLAG]
                avail_oceans.discard(bid)

    def _map_settlements(self, raw_builds):
        for b in raw_builds:
            # Find 3 closest tiles
            dists = sorted(
                [
                    (tid, self.projector.get_dist(b["center"], c))
                    for tid, c in self.board.centers.items()
                ],
                key=lambda x: x[1],
            )
            near = sorted([x[0] for x in dists[:3]])

            # Valid node if adjacent to at least one non-ocean tile? (Game logic)
            # Original code: if any(self.board.tiles[tid][0] != RES_ID_OCEAN for tid in near):
            if any(self.board.tiles[tid][0] != config.RES_ID_OCEAN for tid in near):
                key = "_".join(map(str, near))
                b_type = 2 if "city" in b["name"] else 1
                self.board.nodes[key] = [self.board.get_player_id(b["name"]), b_type]

    def _map_roads(self, raw_roads):
        for r in raw_roads:
            # Find 2 closest tiles
            dists = sorted(
                [
                    (tid, self.projector.get_dist(r["center"], c))
                    for tid, c in self.board.centers.items()
                ],
                key=lambda x: x[1],
            )
            near = sorted([x[0] for x in dists[:2]])

            key = "_".join(map(str, near))
            self.board.edges[key] = self.board.get_player_id(r["name"])
