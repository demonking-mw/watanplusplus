"""Phase 6 geometry endpoint tests."""
from catan_web.engine import coords
from catan_web.geometry import board_geometry


def test_counts():
    g = board_geometry()
    assert len(g["nodes"]) == 54
    assert len(g["edges"]) == 72
    assert len(g["hexes"]) == 19


def test_nodes_have_coordinates():
    for n in board_geometry()["nodes"]:
        assert isinstance(n["x"], float) and isinstance(n["y"], float)


def test_edges_have_endpoints_and_midpoint():
    keys = {"id", "x1", "y1", "x2", "y2", "mx", "my"}
    for e in board_geometry()["edges"]:
        assert keys <= set(e.keys())


def test_hexes_have_six_corners():
    for h in board_geometry()["hexes"]:
        assert len(h["corners"]) == 6


def test_bounds_are_ordered():
    b = board_geometry()["bounds"]
    assert b["minX"] < b["maxX"]
    assert b["minY"] < b["maxY"]


def test_ocean_ring_surrounds_land():
    g = board_geometry()
    assert len(g["ocean"]) == 18
    for o in g["ocean"]:
        assert len(o["corners"]) == 6


def test_harbor_slots_for_coast():
    g = board_geometry()
    coastal = sum(1 for e in coords.BOARD.edges if len(e.hex_ids) == 1)
    assert len(g["harbor_slots"]) == coastal
