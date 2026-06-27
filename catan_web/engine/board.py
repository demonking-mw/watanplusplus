"""Board generation for base Catan.

Builds the per-hex terrain and number token overlay on top of the static
geometry from coords, places the robber on the desert, and positions the nine
harbors on coastal edges. All randomness flows through the seeded GameRandom so
a given seed always produces the same board.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from . import coords
from .rng import GameRandom


class Resource(str, Enum):
    LUMBER = "lumber"
    BRICK = "brick"
    WOOL = "wool"
    GRAIN = "grain"
    ORE = "ore"


class Terrain(str, Enum):
    FOREST = "forest"
    HILL = "hill"
    PASTURE = "pasture"
    FIELD = "field"
    MOUNTAIN = "mountain"
    DESERT = "desert"


# Which resource each terrain produces. Desert produces nothing.
RESOURCE_FOR_TERRAIN: dict[Terrain, Resource | None] = {
    Terrain.FOREST: Resource.LUMBER,
    Terrain.HILL: Resource.BRICK,
    Terrain.PASTURE: Resource.WOOL,
    Terrain.FIELD: Resource.GRAIN,
    Terrain.MOUNTAIN: Resource.ORE,
    Terrain.DESERT: None,
}

# Standard 4 player terrain multiset (19 hexes).
TERRAIN_COUNTS: dict[Terrain, int] = {
    Terrain.FOREST: 4,
    Terrain.PASTURE: 4,
    Terrain.FIELD: 4,
    Terrain.HILL: 3,
    Terrain.MOUNTAIN: 3,
    Terrain.DESERT: 1,
}

# Standard 18 number tokens placed on the non desert hexes.
NUMBER_TOKENS: tuple[int, ...] = (
    2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12,
)

HIGH_TOKENS = frozenset({6, 8})
_MAX_TOKEN_TRIES = 500


@dataclass(frozen=True)
class BoardHex:
    hex_id: int
    terrain: Terrain
    token: int | None    # None on the desert


@dataclass(frozen=True)
class Port:
    resource: Resource | None    # None means a generic 3:1 port
    ratio: int                   # 3 for generic, 2 for a specific resource
    node_ids: tuple[int, int]    # the two coastal nodes that grant the port


@dataclass(frozen=True)
class Board:
    hexes: tuple[BoardHex, ...]    # indexed by hex id
    ports: tuple[Port, ...]
    robber_hex: int

    def hex(self, hex_id: int) -> BoardHex:
        return self.hexes[hex_id]

    def port_nodes(self) -> dict[int, Port]:
        """Map each port granting node to its Port."""
        out: dict[int, Port] = {}
        for port in self.ports:
            for node_id in port.node_ids:
                out[node_id] = port
        return out


def _coastline_edge_order() -> list[int]:
    """Return the 30 coastal edge IDs in a single walk around the perimeter."""
    border = [e for e in coords.BOARD.edges if len(e.hex_ids) == 1]
    node_to_border: dict[int, list[int]] = defaultdict(list)
    for e in border:
        for n in e.node_ids:
            node_to_border[n].append(e.id)

    start = min(e.id for e in border)
    order = [start]
    used = {start}
    _, cur_node = coords.BOARD.edge(start).node_ids
    while len(order) < len(border):
        nexts = [eid for eid in node_to_border[cur_node] if eid not in used]
        if not nexts:
            break
        nxt = nexts[0]
        order.append(nxt)
        used.add(nxt)
        a, b = coords.BOARD.edge(nxt).node_ids
        cur_node = a if b == cur_node else b

    assert len(order) == 30, len(order)
    return order


def _port_definitions() -> list[tuple[Resource | None, int]]:
    """The nine ports: four generic 3:1 and five specific 2:1."""
    return [
        (None, 3), (None, 3), (None, 3), (None, 3),
        (Resource.LUMBER, 2),
        (Resource.BRICK, 2),
        (Resource.WOOL, 2),
        (Resource.GRAIN, 2),
        (Resource.ORE, 2),
    ]


def _hex_neighbor_ids(hex_id: int) -> list[int]:
    """Return adjacent land hex IDs for a hex on the 19 hex board."""
    q, r, s = coords.BOARD.hex(hex_id).cube
    cube_to_id = {h.cube: h.id for h in coords.BOARD.hexes}
    neighbors = []
    for dq, dr, ds in ((1, -1, 0), (1, 0, -1), (0, 1, -1), (-1, 1, 0), (-1, 0, 1), (0, -1, 1)):
        nxt = (q + dq, r + dr, s + ds)
        if nxt in cube_to_id:
            neighbors.append(cube_to_id[nxt])
    return neighbors


def _tokens_valid(hexes: tuple[BoardHex, ...]) -> bool:
    """No adjacent 6/8 pair and no identical tokens on touching hexes."""
    by_id = {h.hex_id: h.token for h in hexes}
    for h in hexes:
        if h.token is None:
            continue
        for nid in _hex_neighbor_ids(h.hex_id):
            other = by_id.get(nid)
            if other is None:
                continue
            if h.token in HIGH_TOKENS and other in HIGH_TOKENS:
                return False
            if h.token == other:
                return False
    return True


def _assign_tokens(
    rng: GameRandom, terrains: list[Terrain],
) -> tuple[tuple[BoardHex, ...], int]:
    """Shuffle number tokens onto non desert hexes with placement constraints."""
    non_desert = [i for i, t in enumerate(terrains) if t is not Terrain.DESERT]
    robber_hex = -1
    for attempt in range(_MAX_TOKEN_TRIES):
        tokens = rng.shuffle(list(NUMBER_TOKENS))
        assignment = dict(zip(non_desert, tokens))
        hexes = []
        for hex_id, terrain in enumerate(terrains):
            if terrain is Terrain.DESERT:
                hexes.append(BoardHex(hex_id=hex_id, terrain=terrain, token=None))
                robber_hex = hex_id
            else:
                hexes.append(
                    BoardHex(hex_id=hex_id, terrain=terrain, token=assignment[hex_id])
                )
        if _tokens_valid(tuple(hexes)):
            return tuple(hexes), robber_hex
    raise RuntimeError("failed to place number tokens with adjacency constraints")


def _place_ports(rng: GameRandom) -> tuple[Port, ...]:
    """Place the nine ports on evenly spaced coastal edges, types shuffled."""
    ring = _coastline_edge_order()
    count = len(_port_definitions())
    positions = [round(i * len(ring) / count) for i in range(count)]
    defs = rng.shuffle(_port_definitions())
    ports = []
    for pos, (resource, ratio) in zip(positions, defs):
        edge = coords.BOARD.edge(ring[pos])
        ports.append(Port(resource=resource, ratio=ratio, node_ids=edge.node_ids))
    return tuple(ports)


def generate_board(rng: GameRandom) -> Board:
    """Generate a full random board. Deterministic for a given RNG seed."""
    terrains: list[Terrain] = []
    for terrain, n in TERRAIN_COUNTS.items():
        terrains.extend([terrain] * n)
    terrains = rng.shuffle(terrains)

    hexes, robber_hex = _assign_tokens(rng, terrains)
    ports = _place_ports(rng)
    return Board(hexes=hexes, ports=ports, robber_hex=robber_hex)
