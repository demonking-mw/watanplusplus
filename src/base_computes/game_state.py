from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Set, Tuple, Union


# --- Positional Array Indices ---
# Resource: 0=Wood, 1=Brick, 2=Wool, 3=Grain, 4=Ore
# DevCard:  0=Knight, 1=VP, 2=RoadBuilding, 3=YearOfPlenty, 4=Monopoly
# Tile Resource: same as Resource + 5=Desert, 6=Ocean

# Per-card probability of being each resource type
# [P_Wood, P_Brick, P_Wool, P_Grain, P_Ore]
ResTuple = List[float]

# Per-card dev info: [Age, P_Knight, P_VP, P_Road, P_Year, P_Mono]
DevTuple = List[Union[int, float]]

# --- Board Topology Constants ---
# Fixed mapping: port ocean tile ID -> (access_node_a, access_node_b)
# Derived from the Vertex-Face Dual Graph. Each port tile has exactly
# two settlement spots that grant port access. These 9 ocean tile
# positions are the only ones that ever carry ports.
PORT_TILE_TO_NODES: Dict[int, Tuple[str, str]] = {
    0: ("0_1_5", "0_4_5"),
    2: ("1_2_6", "2_6_7"),
    8: ("7_8_13", "8_13_14"),
    9: ("4_9_10", "9_10_16"),
    21: ("14_20_21", "20_21_27"),
    22: ("16_22_23", "22_23_28"),
    32: ("26_27_32", "26_31_32"),
    33: ("28_29_33", "29_33_34"),
    35: ("30_31_35", "30_34_35"),
}

# --- Hex-grid layout (row-major, top-to-bottom) ---
# Row 0: 4 tiles (0-3)    Row 1: 5 tiles (4-8)
# Row 2: 6 tiles (9-14)   Row 3: 7 tiles (15-21)
# Row 4: 6 tiles (22-27)  Row 5: 5 tiles (28-32)
# Row 6: 4 tiles (33-36)
ROW_SIZES: List[int] = [4, 5, 6, 7, 6, 5, 4]
NUM_TILES: int = 37  # sum(ROW_SIZES)


def _tile_to_rowcol(tile_id: int) -> Tuple[int, int]:
    """Convert linear tile ID (0-36) to (row, col)."""
    cumulative = 0
    for row, size in enumerate(ROW_SIZES):
        if tile_id < cumulative + size:
            return row, tile_id - cumulative
        cumulative += size
    raise ValueError(f"Invalid tile_id: {tile_id}")


def _rowcol_to_tile(row: int, col: int) -> int:
    """Convert (row, col) to linear tile ID."""
    return sum(ROW_SIZES[:row]) + col


def get_adjacent_tiles(tile_id: int) -> Set[int]:
    """Return the set of tile IDs sharing a hex edge with *tile_id*.

    Adjacency rules for the [4,5,6,7,6,5,4] grid:
      - Same row: col ± 1.
      - Adjacent row that is *wider*:  cols c and c+1.
      - Adjacent row that is *narrower*: cols c-1 and c.
    """
    row, col = _tile_to_rowcol(tile_id)
    neighbors: Set[int] = set()
    this_size = ROW_SIZES[row]

    # Same-row neighbours
    if col > 0:
        neighbors.add(_rowcol_to_tile(row, col - 1))
    if col < this_size - 1:
        neighbors.add(_rowcol_to_tile(row, col + 1))

    # Upper / lower rows
    for adj_row in (row - 1, row + 1):
        if 0 <= adj_row < len(ROW_SIZES):
            adj_size = ROW_SIZES[adj_row]
            if adj_size > this_size:
                # Adjacent row is wider → offsets c, c+1
                for c in (col, col + 1):
                    if 0 <= c < adj_size:
                        neighbors.add(_rowcol_to_tile(adj_row, c))
            else:
                # Adjacent row is narrower → offsets c-1, c
                for c in (col - 1, col):
                    if 0 <= c < adj_size:
                        neighbors.add(_rowcol_to_tile(adj_row, c))

    return neighbors


def is_valid_node(
    tile_triple: Tuple[int, int, int],
    tiles: List[List[int]] = None,
) -> bool:
    """Check whether three tile IDs form a valid settlement node.

    Uses a pre-computed set of all 54 valid nodes on the standard
    Catan board ([4,5,6,7,6,5,4] hex grid).  A node is the intersection
    of exactly 3 mutually-adjacent tiles where not all three are ocean.

    The *tiles* argument is accepted for API compatibility but ignored;
    the valid set is fixed by the board topology.

    Args:
        tile_triple: Three tile IDs (any order; will be sorted).
        tiles:       Unused (kept for backward compat).

    Returns:
        True if the triple is a valid settlement intersection.
    """
    key = "_".join(str(t) for t in sorted(tile_triple))
    return key in VALID_NODES


# --- Pre-computed set of all 54 valid settlement nodes ---
# Derived by enumerating every triple of mutually-adjacent tiles in the
# [4,5,6,7,6,5,4] hex grid, excluding all-ocean triples (none exist).
#
# Between rows r and r+1 there are two kinds of vertex:
#   ∨ (downward): one tile in row r, two in row r+1
#   ∧ (upward):   one tile in row r+1, two in row r
#
# Row sizes  →  nodes between rows:
#   4,5  → 4∨ + 3∧ =  7
#   5,6  → 5∨ + 4∧ =  9
#   6,7  → 6∨ + 5∧ = 11
#   7,6  → 5∨ + 6∧ = 11
#   6,5  → 4∨ + 5∧ =  9
#   5,4  → 3∨ + 4∧ =  7
#   Total            54
VALID_NODES: Set[str] = {
    # ── rows 0↔1 (7 nodes) ──────────────────────────────────
    "0_4_5",
    "0_1_5",  # left edge
    "1_5_6",
    "1_2_6",
    "2_6_7",
    "2_3_7",
    "3_7_8",  # right edge
    # ── rows 1↔2 (9 nodes) ──────────────────────────────────
    "4_9_10",
    "4_5_10",
    "5_10_11",
    "5_6_11",
    "6_11_12",
    "6_7_12",
    "7_12_13",
    "7_8_13",
    "8_13_14",
    # ── rows 2↔3 (11 nodes) ─────────────────────────────────
    "9_15_16",
    "9_10_16",
    "10_16_17",
    "10_11_17",
    "11_17_18",
    "11_12_18",
    "12_18_19",
    "12_13_19",
    "13_19_20",
    "13_14_20",
    "14_20_21",
    # ── rows 3↔4 (11 nodes) ─────────────────────────────────
    "15_16_22",
    "16_22_23",
    "16_17_23",
    "17_23_24",
    "17_18_24",
    "18_24_25",
    "18_19_25",
    "19_25_26",
    "19_20_26",
    "20_26_27",
    "20_21_27",
    # ── rows 4↔5 (9 nodes) ──────────────────────────────────
    "22_23_28",
    "23_28_29",
    "23_24_29",
    "24_29_30",
    "24_25_30",
    "25_30_31",
    "25_26_31",
    "26_31_32",
    "26_27_32",
    # ── rows 5↔6 (7 nodes) ──────────────────────────────────
    "28_29_33",
    "29_33_34",
    "29_30_34",
    "30_34_35",
    "30_31_35",
    "31_35_36",
    "31_32_36",
}


def generate_ports(tiles: List[List[int]]) -> Dict[str, int]:
    """Build the ports dict from tile data.

    Scans *tiles* for port entries (NumberToken == -1) and maps each to
    its two access-node keys using the fixed board topology.

    Args:
        tiles: List of [ResourceID, NumberToken] indexed by tile ID (0-36).

    Returns:
        Dict mapping node keys ("T1_T2_T3") to port type
        (0-4 = 2:1 specific resource, 5 = 3:1 any).
    """
    ports: Dict[str, int] = {}
    for tile_id, (res_id, number_token) in enumerate(tiles):
        if number_token == -1 and tile_id in PORT_TILE_TO_NODES:
            node_a, node_b = PORT_TILE_TO_NODES[tile_id]
            ports[node_a] = res_id
            ports[node_b] = res_id
    return ports


# Standard Catan port distribution: 4x 3:1 general + one each 2:1 specific
EXPECTED_PORT_COUNTS: Dict[int, int] = {
    5: 4,  # 3:1 any
    0: 1,  # 2:1 wood
    1: 1,  # 2:1 brick
    2: 1,  # 2:1 wool
    3: 1,  # 2:1 grain
    4: 1,  # 2:1 ore
}


def validate_ports(tiles: List[List[int]], ports: Dict[str, int]) -> List[str]:
    """Validate port data for consistency and correctness.

    Checks:
        1. **Pair consistency** – Both access nodes of the same physical
           port must have the same port type in *ports*.
        2. **Distribution** – Standard Catan has 9 ports: 4 general (3:1)
           and one of each 2:1 resource (wood/brick/wool/grain/ore).
           The ports dict should have exactly 18 entries (9 ports x 2 nodes).
        3. **Tiles ↔ ports agreement** – The port types derived from
           *tiles* (NumberToken == -1) must match those in *ports*.

    Args:
        tiles: List of [ResourceID, NumberToken] indexed by tile ID (0-36).
        ports: The ports dict mapping node keys to port type.

    Returns:
        List of error strings. Empty list means valid.
    """
    errors: List[str] = []

    # --- Check 1: pair consistency ---
    for tile_id, (node_a, node_b) in PORT_TILE_TO_NODES.items():
        a_present = node_a in ports
        b_present = node_b in ports
        if a_present and b_present:
            if ports[node_a] != ports[node_b]:
                errors.append(
                    f"Pair mismatch at port tile {tile_id}: "
                    f"{node_a}={ports[node_a]}, {node_b}={ports[node_b]}"
                )
        elif a_present != b_present:
            present = node_a if a_present else node_b
            missing = node_b if a_present else node_a
            errors.append(
                f"Incomplete port pair at tile {tile_id}: "
                f"{present} present but {missing} missing"
            )

    # --- Check 2: port count / distribution ---
    # Count physical ports (each port = 2 node entries with identical type)
    if len(ports) != 18:
        errors.append(
            f"Expected 18 port node entries (9 ports x 2 nodes), got {len(ports)}"
        )

    # Count each port type (deduplicate by tile to count physical ports)
    type_counts: Dict[int, int] = {}
    for tile_id, (node_a, _node_b) in PORT_TILE_TO_NODES.items():
        if node_a in ports:
            ptype = ports[node_a]
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

    for ptype, expected in EXPECTED_PORT_COUNTS.items():
        actual = type_counts.get(ptype, 0)
        if actual != expected:
            label = {
                0: "Wood",
                1: "Brick",
                2: "Wool",
                3: "Grain",
                4: "Ore",
                5: "3:1 Any",
            }.get(ptype, str(ptype))
            errors.append(
                f"Port distribution: expected {expected} {label} port(s), "
                f"got {actual}"
            )

    # --- Check 3: tiles ↔ ports agreement ---
    tiles_ports = generate_ports(tiles)
    for node_key, tile_type in tiles_ports.items():
        if node_key in ports and ports[node_key] != tile_type:
            errors.append(
                f"Tiles/ports conflict at {node_key}: "
                f"tiles says {tile_type}, ports says {ports[node_key]}"
            )
    for node_key in ports:
        if node_key not in tiles_ports:
            errors.append(
                f"Port node {node_key} in ports dict has no "
                f"corresponding port tile in tiles"
            )
    for node_key in tiles_ports:
        if node_key not in ports:
            errors.append(
                f"Port node {node_key} derived from tiles "
                f"is missing from ports dict"
            )

    return errors


class Meta(BaseModel):
    t: int  # current turn number
    p_curr: int  # active player id
    phase: str  # "main" or "settle"
    dice: List[int]  # last 8 rolls, newest first
    dev_rem: List[int]  # unplayed dev cards globally: [Knight, VP, RB, YOP, MONO]


class Board(BaseModel):
    robber: int  # tile id where robber sits (0-36)

    # --- Static ---
    # [ResourceID, NumberToken] indexed by tile id (0-36)
    # NumberToken: 2-12 = dice number, 0 = desert/ocean, -1 = port
    # When NumberToken is -1, ResourceID indicates port type (0-4 = 2:1, 5 = 3:1)
    tiles: List[List[int]]

    # "T1_T2_T3" (sorted tile ids) -> port type (0-4 = 2:1 resource, 5 = 3:1 any)
    ports: Dict[str, int]

    # --- Dynamic ---
    # "T1_T2_T3" (sorted) -> [player_id, building_type] where 1=settlement, 2=city
    nodes: Dict[str, List[int]] = Field(default_factory=dict)

    # "T1_T2" (sorted) -> player_id
    edges: Dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _fill_ports_from_tiles(self) -> "Board":
        """Auto-populate ports from tiles when ports is empty."""
        if not self.ports and self.tiles:
            self.ports = generate_ports(self.tiles)
        return self


class Player(BaseModel):
    id: int
    public: List[int]  # [VP, Army, RoadLength, ResCount]
    res_k: List[int]  # known resource counts: [Wood, Brick, Wool, Grain, Ore]
    res_u: List[
        ResTuple
    ]  # unknown cards, each [P_Wood, P_Brick, P_Wool, P_Grain, P_Ore]
    devs: List[
        DevTuple
    ]  # dev cards in hand, each [Age, P_Knight, P_VP, P_Road, P_Year, P_Mono]


class GameState(BaseModel):
    meta: Meta
    map: Board
    players: List[Player]

    # Optional augmentation: node_key -> score (populated by evaluate_all_settlements)
    settle_scores: Optional[Dict[str, float]] = None

    @model_validator(mode="after")
    def _validate_settlements(self) -> "GameState":
        """Ensure no settlements overlap or violate the distance rule.

        Runs automatically when a ``GameState`` is constructed.
        Raises ``ValueError`` on any conflict.
        """
        errors = self.validate_settlements()
        if errors:
            raise ValueError(
                "Settlement validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )
        return self

    def validate_settlements(self) -> List[str]:
        """Check settlement placement for overlaps and adjacency violations.

        Validates two sources:

        1. **``map.nodes``** — the canonical settlement registry.
           - Every node key must be a valid node (in ``VALID_NODES``).
           - No two settlements may occupy the same node (dict enforces
             uniqueness, but player IDs referenced must exist in
             ``self.players``).
           - No two settlements may be directly adjacent (share 2 of
             their 3 tile IDs).

        2. **``players`` cross-check** — every player ID referenced in
           ``map.nodes`` must correspond to an actual player in the
           ``players`` list.

        Returns:
            List of error strings.  Empty means valid.
        """
        errors: List[str] = []
        node_keys = list(self.map.nodes.keys())
        valid_player_ids = {p.id for p in self.players}

        # ── Check each node is valid and player ID exists ────────────
        for node_key, (pid, btype) in self.map.nodes.items():
            if node_key not in VALID_NODES:
                errors.append(f"Settlement at {node_key} is not a valid node")
            if pid not in valid_player_ids:
                errors.append(
                    f"Settlement at {node_key} references player {pid} "
                    f"who does not exist in the players list"
                )

        # ── Check no two settlements are directly adjacent ───────────
        # Two nodes are adjacent when they share exactly 2 of their
        # 3 tile IDs.
        for i in range(len(node_keys)):
            tiles_i = set(node_keys[i].split("_"))
            for j in range(i + 1, len(node_keys)):
                tiles_j = set(node_keys[j].split("_"))
                if len(tiles_i & tiles_j) == 2:
                    errors.append(
                        f"Settlements at {node_keys[i]} and {node_keys[j]} "
                        f"are directly adjacent (distance rule violation)"
                    )

        return errors

    def evaluate_all_settlements(
        self,
    ) -> Dict[str, float]:
        """Score every valid settlement spot and cache the result.

        Iterates over all 54 ``VALID_NODES``, runs the evaluation
        algorithm from ``settle_eval_simple.score_settlement`` on each,
        and stores the mapping in ``self.settle_scores``.

        Returns:
            Dict mapping each node key to its score (also stored on
            ``self.settle_scores``).
        """
        from base_computes.settle_eval_simple import score_settlement

        scores: Dict[str, float] = {}
        for node_key in sorted(VALID_NODES):
            scores[node_key] = score_settlement(self, node_key)
        self.settle_scores = scores
        return scores

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)

    @classmethod
    def from_json(cls, data: dict) -> "GameState":
        """Parse a raw HDCS JSON dict, repair missing ports, validate, and return.

        Steps:
            1. If ``data["map"]["ports"]`` is empty/missing, generate it
               from tile data.
            2. Validate port info (pair consistency, distribution, tiles ↔ ports).
            3. If ``data["players"]`` is empty, initialize 4 default players.
            4. Return a validated ``GameState`` or raise ``ValueError``.
        """
        map_data = data.get("map", {})
        tiles = map_data.get("tiles", [])
        ports = map_data.get("ports", {})

        # Step 1: repair missing ports
        if not ports and tiles:
            map_data["ports"] = generate_ports(tiles)

        # Step 2: validate
        errors = validate_ports(
            map_data.get("tiles", []),
            map_data.get("ports", {}),
        )
        if errors:
            raise ValueError(
                "Port validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        # Step 3: repair missing players
        if not data.get("players"):
            data["players"] = [
                {
                    "id": i,
                    "public": [0, 0, 0, 0],  # [VP, Army, Road_Len, Res_Count]
                    "res_k": [0, 0, 0, 0, 0],  # [Wood, Brick, Wool, Grain, Ore]
                    "res_u": [],
                    "devs": [],
                }
                for i in range(4)
            ]

        # Step 4: build validated object
        return cls.model_validate(data)


def compute_starting_hands(gs: GameState) -> List[List[int]]:
    """Compute each player's starting resource cards after board setup.

    In Catan, each player receives **one resource card** for every
    resource-producing tile adjacent to their **second** settlement.

    Assumes the iteration order of ``gs.map.nodes`` matches the
    physical placement order (Python dicts preserve insertion order
    since 3.7).  The *second* node listed for a given player ID
    is treated as their second settlement.

    Parameters
    ----------
    gs : GameState
        A board state where all (or most) setup settlements have been
        placed.  Players with fewer than 2 settlements get an empty hand.

    Returns
    -------
    List of ``num_players`` lists, each ``[Wood, Brick, Wool, Grain, Ore]``
    (integer counts).
    """
    num_players = len(gs.players)
    hands: List[List[int]] = [[0, 0, 0, 0, 0] for _ in range(num_players)]

    # Track per-player settlement count to identify the second one
    settle_count: Dict[int, int] = {}
    second_settle: Dict[int, str] = {}  # player_id → node_key of 2nd settle

    for node_key, (player_id, _btype) in gs.map.nodes.items():
        settle_count[player_id] = settle_count.get(player_id, 0) + 1
        if settle_count[player_id] == 2:
            second_settle[player_id] = node_key

    # Award one resource card per adjacent resource tile
    for player in gs.players:
        if player.id not in second_settle:
            continue
        node_key = second_settle[player.id]
        for tid_str in node_key.split("_"):
            tid = int(tid_str)
            if tid < len(gs.map.tiles):
                res_id, num_token = gs.map.tiles[tid]
                # Resource tile (not desert/ocean) with a valid number token
                if 0 <= res_id <= 4 and num_token >= 2:
                    hands[player.id][res_id] += 1

    return hands
