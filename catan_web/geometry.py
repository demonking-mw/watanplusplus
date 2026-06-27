"""Board geometry serialized for the frontend.

The browser must render using the exact node and edge IDs the server uses, so
this exposes the canonical geometry from coords.BOARD as plain JSON. Positions
come from the size 1.0 hex layout in coords; the client scales them with the
SVG viewBox using the returned bounds.

Also includes the ocean hex ring (radius 3 minus land) and harbor tile anchors
on the sea side of each coastal edge.
"""
from __future__ import annotations

import math

from catan_web.engine import coords

_LAND_RADIUS = 2
_OCEAN_RADIUS = 3


def _cube_coords(radius: int) -> list[tuple[int, int, int]]:
    cubes = []
    for q in range(-radius, radius + 1):
        for r in range(-radius, radius + 1):
            s = -q - r
            if abs(s) <= radius:
                cubes.append((q, r, s))
    cubes.sort(key=lambda c: (c[1], c[0]))
    return cubes


def _hex_center(q: int, r: int) -> tuple[float, float]:
    x = math.sqrt(3.0) * (q + r / 2.0)
    y = 1.5 * r
    return (x, y)


def _hex_corner(center: tuple[float, float], i: int) -> tuple[float, float]:
    angle = math.radians(60.0 * i - 30.0)
    return (center[0] + math.cos(angle), center[1] + math.sin(angle))


def _hex_polygon(cube: tuple[int, int, int]) -> dict:
    q, r, _ = cube
    center = _hex_center(q, r)
    corners = [
        [round(_hex_corner(center, i)[0], 4), round(_hex_corner(center, i)[1], 4)]
        for i in range(6)
    ]
    return {
        "cx": round(center[0], 4),
        "cy": round(center[1], 4),
        "corners": corners,
    }


def _ocean_hexes() -> list[dict]:
    land = {h.cube for h in coords.BOARD.hexes}
    out = []
    for i, cube in enumerate(_cube_coords(_OCEAN_RADIUS)):
        if cube in land:
            continue
        h = _hex_polygon(cube)
        h["id"] = f"ocean-{i}"
        out.append(h)
    return out


def _harbor_slots() -> dict[str, dict]:
    """Map sorted coastal node pair to harbor tile center on the ocean ring."""
    slots: dict[str, dict] = {}
    for edge in coords.BOARD.edges:
        if len(edge.hex_ids) != 1:
            continue
        land_id = edge.hex_ids[0]
        lc = coords.BOARD.hex(land_id).center
        n1 = coords.BOARD.node(edge.node_ids[0]).pos
        n2 = coords.BOARD.node(edge.node_ids[1]).pos
        mx, my = (n1[0] + n2[0]) / 2.0, (n1[1] + n2[1]) / 2.0
        dx, dy = mx - lc[0], my - lc[1]
        dist = math.hypot(dx, dy) or 1.0
        # Extend past the coast edge onto the adjacent ocean hex center.
        scale = 2.15 / dist
        hx, hy = lc[0] + dx * scale, lc[1] + dy * scale
        key = f"{min(edge.node_ids)}_{max(edge.node_ids)}"
        slots[key] = {
            "cx": round(hx, 4),
            "cy": round(hy, 4),
            "angle": round(math.degrees(math.atan2(dy, dx)), 2),
        }
    return slots


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

    ocean = _ocean_hexes()
    all_x = [n["x"] for n in nodes] + [c for o in ocean for pt in o["corners"] for c in [pt[0]]]
    all_y = [n["y"] for n in nodes] + [c for o in ocean for pt in o["corners"] for c in [pt[1]]]
    bounds = {"minX": min(all_x), "minY": min(all_y), "maxX": max(all_x), "maxY": max(all_y)}
    return {
        "nodes": nodes,
        "edges": edges,
        "hexes": hexes,
        "ocean": ocean,
        "harbor_slots": _harbor_slots(),
        "bounds": bounds,
    }
