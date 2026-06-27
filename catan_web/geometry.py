"""Board geometry serialized for the frontend.

The browser must render using the exact node and edge IDs the server uses, so
this exposes the canonical geometry from coords.BOARD as plain JSON. Positions
come from the size 1.0 hex layout in coords; the client scales them with the
SVG viewBox using the returned bounds.
"""
from __future__ import annotations

from catan_web.engine import coords


def board_geometry() -> dict:
    nodes = [
        {"id": n.id, "x": round(n.pos[0], 4), "y": round(n.pos[1], 4)}
        for n in coords.BOARD.nodes
    ]
    edges = []
    for e in coords.BOARD.edges:
        a = coords.BOARD.node(e.node_ids[0]).pos
        b = coords.BOARD.node(e.node_ids[1]).pos
        edges.append(
            {
                "id": e.id,
                "x1": round(a[0], 4), "y1": round(a[1], 4),
                "x2": round(b[0], 4), "y2": round(b[1], 4),
                "mx": round((a[0] + b[0]) / 2, 4),
                "my": round((a[1] + b[1]) / 2, 4),
            }
        )
    hexes = []
    for h in coords.BOARD.hexes:
        corners = [
            [round(coords.BOARD.node(nid).pos[0], 4),
             round(coords.BOARD.node(nid).pos[1], 4)]
            for nid in h.node_ids
        ]
        hexes.append(
            {"id": h.id, "cx": round(h.center[0], 4),
             "cy": round(h.center[1], 4), "corners": corners}
        )
    xs = [n["x"] for n in nodes]
    ys = [n["y"] for n in nodes]
    bounds = {"minX": min(xs), "minY": min(ys), "maxX": max(xs), "maxY": max(ys)}
    return {"nodes": nodes, "edges": edges, "hexes": hexes, "bounds": bounds}
