"""Phase 1 board graph tests."""
from catan_web.engine import coords
from catan_web.engine.coords import BOARD


def test_counts():
    assert len(BOARD.hexes) == coords.NUM_HEXES == 19
    assert len(BOARD.nodes) == coords.NUM_NODES == 54
    assert len(BOARD.edges) == coords.NUM_EDGES == 72


def test_each_hex_has_six_unique_corners_and_edges():
    for h in BOARD.hexes:
        assert len(h.node_ids) == 6
        assert len(set(h.node_ids)) == 6
        assert len(h.edge_ids) == 6
        assert len(set(h.edge_ids)) == 6


def test_edges_join_two_distinct_sorted_nodes():
    for e in BOARD.edges:
        a, b = e.node_ids
        assert a < b


def test_edge_endpoints_are_mutual_neighbors():
    for e in BOARD.edges:
        a, b = e.node_ids
        assert b in BOARD.node(a).neighbor_ids
        assert a in BOARD.node(b).neighbor_ids


def test_node_edge_and_neighbor_counts_match():
    for n in BOARD.nodes:
        assert len(n.edge_ids) == len(n.neighbor_ids)
        assert 2 <= len(n.neighbor_ids) <= 3


def test_node_touches_one_to_three_hexes():
    for n in BOARD.nodes:
        assert len(n.hex_ids) == len(n.hex_cubes)
        assert 1 <= len(n.hex_ids) <= 3


def test_node_hex_split_is_18_12_24():
    one = [n for n in BOARD.nodes if len(n.hex_ids) == 1]
    two = [n for n in BOARD.nodes if len(n.hex_ids) == 2]
    three = [n for n in BOARD.nodes if len(n.hex_ids) == 3]
    assert (len(one), len(two), len(three)) == (18, 12, 24)


def test_node_degree_matches_hex_adjacency():
    """Only outer tip nodes (1 hex) have degree 2; all others have degree 3."""
    for n in BOARD.nodes:
        if len(n.hex_ids) == 1:
            assert len(n.edge_ids) == 2
        else:
            assert len(n.edge_ids) == 3
    two_edge = [n for n in BOARD.nodes if len(n.edge_ids) == 2]
    three_edge = [n for n in BOARD.nodes if len(n.edge_ids) == 3]
    assert len(two_edge) == 18
    assert len(three_edge) == 36


def test_border_and_interior_edge_counts():
    border = [e for e in BOARD.edges if len(e.hex_ids) == 1]
    interior = [e for e in BOARD.edges if len(e.hex_ids) == 2]
    assert len(border) == 30
    assert len(interior) == 42


def test_total_node_hex_incidence():
    total = sum(len(n.hex_ids) for n in BOARD.nodes)
    assert total == coords.NUM_HEXES * 6 == 114


def test_adjacency_is_symmetric():
    for n in BOARD.nodes:
        for m in n.neighbor_ids:
            assert n.id in BOARD.node(m).neighbor_ids


def test_center_hex_is_fully_surrounded():
    center = next(h for h in BOARD.hexes if h.cube == (0, 0, 0))
    for node_id in center.node_ids:
        assert len(BOARD.node(node_id).hex_ids) == 3
