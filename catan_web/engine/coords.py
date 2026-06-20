"""Board geometry for base Catan.

Phase 1 implements the canonical board graph:
- 19 land hexes addressed by cube coordinates
- 54 settlement nodes
- 72 road edges
- adjacency maps (node to node, node to edge, node to hex, edge to node)

Node IDs follow the project HDCS convention (0 to 53) so exported state
lines up with the existing GameState model.
"""
from __future__ import annotations

NUM_HEXES = 19
NUM_NODES = 54
NUM_EDGES = 72


def build_board_graph() -> dict:
    """Return the static board graph (hexes, nodes, edges, adjacency).

    To be implemented in Phase 1.
    """
    raise NotImplementedError("Phase 1: board graph")
