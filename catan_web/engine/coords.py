"""Static board geometry and graph for base Catan.

This module builds the canonical board graph used across the engine:
- 19 land hexes arranged as a radius 2 hexagon, addressed by cube coordinates
- 54 settlement nodes (hex corners de-duplicated by position)
- 72 road edges (hex sides de-duplicated by endpoint pair)

It also computes adjacency in every direction the engine needs (node to node,
node to edge, node to hex, edge to node, hex to node, hex to edge) and keeps
the pixel positions of hexes and nodes so the frontend can reuse them for
rendering in a later phase.

Node and edge IDs are canonical and deterministic. Nodes are numbered top to
bottom then left to right by position. Edges are numbered by their sorted
endpoint node IDs. The geometry never changes, so the IDs are stable.

Aligning these land hexes to the project HDCS 0 to 36 tile grid (which includes
the ocean ring) is handled in Phase 4 at the export boundary, not here. Each
node stores the cube coordinates of its adjacent hexes so that mapping is
straightforward later.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

NUM_HEXES = 19
NUM_NODES = 54
NUM_EDGES = 72

# Board radius in hexes. Radius 2 gives the standard 19 hex Catan board.
_BOARD_RADIUS = 2

# Quantization factor for de-duplicating corner positions. Two corners that
# represent the same physical point can differ by tiny floating point error,
# so we snap to a grid this many units per coordinate before comparing. The
# minimum distance between two distinct corners is 1.0 units, so this is safe.
_QUANTIZE = 1000


@dataclass(frozen=True)
class Hex:
    id: int
    cube: tuple[int, int, int]    # (q, r, s) with q + r + s == 0
    center: tuple[float, float]   # pixel position, size 1.0 units
    node_ids: tuple[int, ...]     # 6 corner nodes in corner order 0..5
    edge_ids: tuple[int, ...]     # 6 edges, edge i joins corner i and i+1


@dataclass(frozen=True)
class Node:
    id: int
    pos: tuple[float, float]                        # pixel position
    hex_ids: tuple[int, ...]                        # 1 to 3 adjacent hexes
    hex_cubes: tuple[tuple[int, int, int], ...]     # cube coords of those hexes
    neighbor_ids: tuple[int, ...]                   # 2 or 3 adjacent nodes
    edge_ids: tuple[int, ...]                        # 2 or 3 incident edges


@dataclass(frozen=True)
class Edge:
    id: int
    node_ids: tuple[int, int]     # the two endpoints, sorted ascending
    hex_ids: tuple[int, ...]      # 1 or 2 adjacent hexes


@dataclass(frozen=True)
class BoardGraph:
    hexes: tuple[Hex, ...]
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]

    def hex(self, hex_id: int) -> Hex:
        return self.hexes[hex_id]

    def node(self, node_id: int) -> Node:
        return self.nodes[node_id]

    def edge(self, edge_id: int) -> Edge:
        return self.edges[edge_id]


def _cube_coords(radius: int) -> list[tuple[int, int, int]]:
    """Return all cube coordinates within the radius, sorted by (r, q)."""
    coords = []
    for q in range(-radius, radius + 1):
        for r in range(-radius, radius + 1):
            s = -q - r
            if abs(s) <= radius:
                coords.append((q, r, s))
    coords.sort(key=lambda c: (c[1], c[0]))
    return coords


def _hex_center(q: int, r: int) -> tuple[float, float]:
    """Pixel center of a pointy top hex at axial coordinate (q, r), size 1.0."""
    x = math.sqrt(3.0) * (q + r / 2.0)
    y = 1.5 * r
    return (x, y)


def _hex_corner(center: tuple[float, float], i: int) -> tuple[float, float]:
    """Pixel position of corner i (0..5) of a pointy top hex, size 1.0."""
    angle = math.radians(60.0 * i - 30.0)
    return (center[0] + math.cos(angle), center[1] + math.sin(angle))


def _quantize(p: tuple[float, float]) -> tuple[int, int]:
    """Snap a position to an integer grid so equal corners compare equal."""
    return (round(p[0] * _QUANTIZE), round(p[1] * _QUANTIZE))


def build_board_graph() -> BoardGraph:
    """Construct the full board graph. Deterministic and side effect free."""
    cubes = _cube_coords(_BOARD_RADIUS)

    # Step 1: compute every hex center and its six corner positions, collecting
    # unique corner positions keyed by quantized coordinate.
    corner_pos: dict[tuple[int, int], tuple[float, float]] = {}
    corner_hexes: dict[tuple[int, int], set[int]] = defaultdict(set)
    hex_corner_keys: list[list[tuple[int, int]]] = []

    for hex_index, (q, r, s) in enumerate(cubes):
        center = _hex_center(q, r)
        keys = []
        for i in range(6):
            p = _hex_corner(center, i)
            key = _quantize(p)
            if key not in corner_pos:
                corner_pos[key] = p
            corner_hexes[key].add(hex_index)
            keys.append(key)
        hex_corner_keys.append(keys)

    # Step 2: assign canonical node IDs, top to bottom then left to right.
    sorted_keys = sorted(
        corner_pos.keys(),
        key=lambda k: (round(corner_pos[k][1], 6), round(corner_pos[k][0], 6)),
    )
    key_to_node: dict[tuple[int, int], int] = {
        key: node_id for node_id, key in enumerate(sorted_keys)
    }

    # Step 3: collect unique edges as sorted endpoint pairs with their hexes.
    edge_hexes: dict[tuple[int, int], set[int]] = defaultdict(set)
    for hex_index, keys in enumerate(hex_corner_keys):
        for i in range(6):
            a = key_to_node[keys[i]]
            b = key_to_node[keys[(i + 1) % 6]]
            pair = (a, b) if a < b else (b, a)
            edge_hexes[pair].add(hex_index)

    # Step 4: assign canonical edge IDs by sorted endpoint pair.
    sorted_pairs = sorted(edge_hexes.keys())
    pair_to_edge: dict[tuple[int, int], int] = {
        pair: edge_id for edge_id, pair in enumerate(sorted_pairs)
    }

    # Step 5: build node neighbours and incident edges from the edge set.
    node_neighbors: dict[int, set[int]] = defaultdict(set)
    node_edges: dict[int, set[int]] = defaultdict(set)
    for pair, edge_id in pair_to_edge.items():
        a, b = pair
        node_neighbors[a].add(b)
        node_neighbors[b].add(a)
        node_edges[a].add(edge_id)
        node_edges[b].add(edge_id)

    # Step 6: build node to hex adjacency from the corner collection.
    node_hexes: dict[int, set[int]] = defaultdict(set)
    for key, hex_set in corner_hexes.items():
        node_hexes[key_to_node[key]].update(hex_set)

    # Step 7: assemble immutable Node objects.
    nodes = []
    for node_id in range(len(sorted_keys)):
        hex_ids = tuple(sorted(node_hexes[node_id]))
        nodes.append(
            Node(
                id=node_id,
                pos=corner_pos[sorted_keys[node_id]],
                hex_ids=hex_ids,
                hex_cubes=tuple(cubes[h] for h in hex_ids),
                neighbor_ids=tuple(sorted(node_neighbors[node_id])),
                edge_ids=tuple(sorted(node_edges[node_id])),
            )
        )

    # Step 8: assemble immutable Edge objects.
    edges = []
    for edge_id, pair in enumerate(sorted_pairs):
        edges.append(
            Edge(
                id=edge_id,
                node_ids=pair,
                hex_ids=tuple(sorted(edge_hexes[pair])),
            )
        )

    # Step 9: assemble immutable Hex objects with ordered corners and edges.
    hexes = []
    for hex_index, (q, r, s) in enumerate(cubes):
        keys = hex_corner_keys[hex_index]
        node_ids = tuple(key_to_node[k] for k in keys)
        edge_ids = []
        for i in range(6):
            a = node_ids[i]
            b = node_ids[(i + 1) % 6]
            pair = (a, b) if a < b else (b, a)
            edge_ids.append(pair_to_edge[pair])
        hexes.append(
            Hex(
                id=hex_index,
                cube=(q, r, s),
                center=_hex_center(q, r),
                node_ids=node_ids,
                edge_ids=tuple(edge_ids),
            )
        )

    graph = BoardGraph(
        hexes=tuple(hexes),
        nodes=tuple(nodes),
        edges=tuple(edges),
    )
    _validate(graph)
    return graph


def _validate(graph: BoardGraph) -> None:
    """Fail fast if the constructed graph violates known invariants."""
    assert len(graph.hexes) == NUM_HEXES, len(graph.hexes)
    assert len(graph.nodes) == NUM_NODES, len(graph.nodes)
    assert len(graph.edges) == NUM_EDGES, len(graph.edges)
    for h in graph.hexes:
        assert len(h.node_ids) == 6
        assert len(h.edge_ids) == 6
    for e in graph.edges:
        assert e.node_ids[0] < e.node_ids[1]
        assert 1 <= len(e.hex_ids) <= 2
    for n in graph.nodes:
        assert 1 <= len(n.hex_ids) <= 3
        assert 2 <= len(n.neighbor_ids) <= 3
        assert len(n.edge_ids) == len(n.neighbor_ids)


# Built once at import. The board geometry never changes during a game.
BOARD = build_board_graph()
