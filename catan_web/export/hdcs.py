"""Export engine GameState to the project HDCS schema.

HDCS is the native state format used across watanplusplus. Because the server
has full information, this export is ground truth: res_k is exact, res_u is
empty, and dev cards are known.

PROJECT SPECIFIC: the helpers in the RECONCILE block must match
src/base_computes/game_state.py exactly (tile numbering, resource ids, building
and port codes, node and edge key formats). Read that file and the planning doc,
then adjust the helpers and any field names so that GameState.from_json accepts
the output. The test in catan_web/tests/test_hdcs.py is the gate.
"""
from __future__ import annotations

from catan_web.engine import coords
from catan_web.engine.board import RESOURCE_FOR_TERRAIN, Resource
from catan_web.engine.legal import edge_owner, node_building, victory_points
from catan_web.engine.state import DevCard, Phase, VP_DEV_CARDS

# Number of tiles in the HDCS grid, including the ocean ring.
HDCS_TILE_COUNT = 37

# Land tile ids in row-major order matching engine hex ids 0..18.
_LAND_TILE_IDS: tuple[int, ...] = (
    5, 6, 7,
    10, 11, 12, 13,
    16, 17, 18, 19, 20,
    23, 24, 25, 26,
    29, 30, 31,
)
_LAND_TILE_SET = frozenset(_LAND_TILE_IDS)

# HDCS resource ids: 0=Wood, 1=Brick, 2=Wool, 3=Grain, 4=Ore, 5=Desert, 6=Ocean
_RESOURCE_TO_HDCS: dict[Resource, int] = {
    Resource.LUMBER: 0,
    Resource.BRICK: 1,
    Resource.WOOL: 2,
    Resource.GRAIN: 3,
    Resource.ORE: 4,
}

# Precomputed engine node id -> HDCS node key (built once at import).
_NODE_KEY_BY_ID: dict[int, str] = {}


# ----- RECONCILE WITH src/base_computes/game_state.py -----

def _tile_id(hex_id: int) -> int:
    """Map an engine land hex id (0..18) to the HDCS tile id (0..36)."""
    return _LAND_TILE_IDS[hex_id]


def _resource_id(resource: Resource | None) -> int:
    """Map a Resource (or None for desert) to the HDCS resource id."""
    if resource is None:
        return 5
    return _RESOURCE_TO_HDCS[resource]


def _ocean_tile() -> list[int]:
    """The HDCS [resource_id, token] entry for an ocean ring tile."""
    return [6, 0]


def _building_code(kind: str) -> int:
    """Map settlement or city to the project building type code."""
    return 1 if kind == "settlement" else 2


def _port_code(port) -> int:
    """Map a Port to the project port type code (3:1 or 2:1 specific)."""
    if port.resource is None:
        return 5
    return _resource_id(port.resource)


def _build_node_key_map() -> dict[int, str]:
    """Match each engine node to its HDCS node key using land tiles and layout."""
    from src.base_computes.game_state import ROW_SIZES, VALID_NODES

    valid_by_land: dict[frozenset[int], list[str]] = {}
    for key in VALID_NODES:
        land = frozenset(int(t) for t in key.split("_") if int(t) in _LAND_TILE_SET)
        valid_by_land.setdefault(land, []).append(key)

    xs_by_row = {
        0: [26, 42, 58, 74],
        1: [18, 34, 50, 66, 82],
        2: [10, 26, 42, 58, 74, 90],
        3: [2, 18, 34, 50, 66, 82, 98],
        4: [10, 26, 42, 58, 74, 90],
        5: [18, 34, 50, 66, 82],
        6: [26, 42, 58, 74],
    }
    ys_by_row = [3, 9, 14, 19, 24, 29, 34]

    def tile_pos(tid: int) -> tuple[float, float]:
        cumulative = 0
        for row, size in enumerate(ROW_SIZES):
            if tid < cumulative + size:
                col = tid - cumulative
                return xs_by_row[row][col], ys_by_row[row]
            cumulative += size
        raise ValueError(f"Invalid tile id: {tid}")

    def node_pos(key: str) -> tuple[float, float]:
        pts = [tile_pos(int(t)) for t in key.split("_")]
        return sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3

    eng_pts = [n.pos for n in coords.BOARD.nodes]
    min_x = min(p[0] for p in eng_pts)
    max_x = max(p[0] for p in eng_pts)
    min_y = min(p[1] for p in eng_pts)
    max_y = max(p[1] for p in eng_pts)

    def norm_eng(pos: tuple[float, float]) -> tuple[float, float]:
        x = (pos[0] - min_x) / (max_x - min_x) * 80 + 10
        y = (pos[1] - min_y) / (max_y - min_y) * 30 + 3
        return x, y

    out: dict[int, str] = {}
    for node in coords.BOARD.nodes:
        eng_land = frozenset(_tile_id(h) for h in node.hex_ids)
        candidates = valid_by_land.get(eng_land, [])
        if len(candidates) == 1:
            out[node.id] = candidates[0]
            continue
        ex, ey = norm_eng(node.pos)
        best = min(
            candidates,
            key=lambda key: (ex - node_pos(key)[0]) ** 2 + (ey - node_pos(key)[1]) ** 2,
        )
        out[node.id] = best
    return out


def _node_key(node_id: int) -> str:
    """Project node key from sorted adjacent tile ids, for example 5_6_11."""
    if not _NODE_KEY_BY_ID:
        _NODE_KEY_BY_ID.update(_build_node_key_map())
    return _NODE_KEY_BY_ID[node_id]


def _edge_key(edge_id: int) -> str:
    """Project edge key as sorted adjacent tile ids, for example 5_6."""
    from src.base_computes.game_state import get_adjacent_tiles

    a, b = coords.BOARD.edge(edge_id).node_ids
    key_a = _node_key(a)
    key_b = _node_key(b)
    shared = set(key_a.split("_")) & set(key_b.split("_"))
    if len(shared) == 2:
        pair = sorted(int(t) for t in shared)
        return f"{pair[0]}_{pair[1]}"
    land = int(next(iter(shared)))
    all_tiles = set(key_a.split("_")) | set(key_b.split("_"))
    for adj in get_adjacent_tiles(land):
        if adj not in all_tiles and adj not in _LAND_TILE_SET:
            pair = sorted([land, adj])
            return f"{pair[0]}_{pair[1]}"
    raise ValueError(f"Cannot derive edge key for edge {edge_id}")


# ----- Engine side assembly (should need little change) -----

def _phase_code(phase) -> str:
    return "settle" if phase is Phase.SETUP else "main"


def _dev_rem(state) -> list[int]:
    pool = list(state.dev_deck)
    for player in state.players:
        pool.extend(player.dev_cards)
    counts = [0, 0, 0, 0, 0]
    for card in pool:
        if card is DevCard.KNIGHT:
            counts[0] += 1
        elif card in VP_DEV_CARDS:
            counts[1] += 1
        elif card is DevCard.ROAD_BUILDING:
            counts[2] += 1
        elif card is DevCard.YEAR_OF_PLENTY:
            counts[3] += 1
        elif card is DevCard.MONOPOLY:
            counts[4] += 1
    return counts


def _meta(state) -> dict:
    return {
        "t": state.turn_number,
        "p_curr": state.current_player,
        "phase": _phase_code(state.phase),
        "dice": list(reversed(state.dice_history[-8:])),
        "dev_rem": _dev_rem(state),
    }


def _apply_port_tiles(tiles: list, state) -> None:
    """Write port entries onto ocean tiles and fill the ports dict."""
    from src.base_computes.game_state import PORT_TILE_TO_NODES

    node_to_port: dict[str, int] = {}
    for port in state.board.ports:
        code = _port_code(port)
        for node_id in port.node_ids:
            node_to_port[_node_key(node_id)] = code

    for tile_id, (node_a, node_b) in PORT_TILE_TO_NODES.items():
        code = node_to_port.get(node_a)
        if code is None:
            code = node_to_port.get(node_b)
        if code is not None:
            tiles[tile_id] = [code, -1]


def _tiles(state) -> list:
    tiles = [_ocean_tile() for _ in range(HDCS_TILE_COUNT)]
    for board_hex in state.board.hexes:
        token = board_hex.token if board_hex.token is not None else 0
        tiles[_tile_id(board_hex.hex_id)] = [
            _resource_id(RESOURCE_FOR_TERRAIN[board_hex.terrain]),
            token,
        ]
    _apply_port_tiles(tiles, state)
    return tiles


def _ports(state) -> dict:
    out: dict = {}
    for port in state.board.ports:
        code = _port_code(port)
        for node_id in port.node_ids:
            out[_node_key(node_id)] = code
    return out


def _nodes(state) -> dict:
    out: dict = {}
    for node_id in range(coords.NUM_NODES):
        building = node_building(state, node_id)
        if building is not None:
            owner, kind = building
            out[_node_key(node_id)] = [owner, _building_code(kind)]
    return out


def _edges(state) -> dict:
    out: dict = {}
    for edge_id in range(coords.NUM_EDGES):
        owner = edge_owner(state, edge_id)
        if owner is not None:
            out[_edge_key(edge_id)] = owner
    return out


def _map(state) -> dict:
    return {
        "tiles": _tiles(state),
        "ports": _ports(state),
        "nodes": _nodes(state),
        "edges": _edges(state),
        "robber": _tile_id(state.robber_hex),
    }


def _player(state, player) -> dict:
    return {
        "id": player.id,
        "public": [
            victory_points(player),
            player.played_knights,
            len(player.roads),
            sum(player.resources.values()),
        ],
        "res_k": [player.resources[r] for r in Resource],
        "res_u": [],
        "devs": [],
    }


def to_hdcs(state) -> dict:
    return {
        "meta": _meta(state),
        "map": _map(state),
        "players": [_player(state, player) for player in state.players],
    }
