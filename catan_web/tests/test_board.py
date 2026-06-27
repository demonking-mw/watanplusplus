"""Phase 2 board generation tests."""
from collections import Counter

from catan_web.engine import coords
from catan_web.engine.board import (
    HIGH_TOKENS,
    NUMBER_TOKENS,
    Resource,
    Terrain,
    _hex_neighbor_ids,
    _tokens_valid,
    generate_board,
)
from catan_web.engine.rng import GameRandom


def _board(seed=7):
    return generate_board(GameRandom(seed))


def test_has_nineteen_hexes():
    assert len(_board().hexes) == coords.NUM_HEXES == 19


def test_terrain_counts_are_standard():
    counts = Counter(h.terrain for h in _board().hexes)
    assert counts[Terrain.FOREST] == 4
    assert counts[Terrain.PASTURE] == 4
    assert counts[Terrain.FIELD] == 4
    assert counts[Terrain.HILL] == 3
    assert counts[Terrain.MOUNTAIN] == 3
    assert counts[Terrain.DESERT] == 1


def test_desert_has_no_token_and_holds_robber():
    board = _board()
    deserts = [h for h in board.hexes if h.terrain is Terrain.DESERT]
    assert len(deserts) == 1
    assert deserts[0].token is None
    assert board.robber_hex == deserts[0].hex_id


def test_number_tokens_match_standard_set():
    tokens = [h.token for h in _board().hexes if h.token is not None]
    assert sorted(tokens) == sorted(NUMBER_TOKENS)
    assert len(tokens) == 18


def test_nine_ports_with_correct_composition():
    ports = _board().ports
    assert len(ports) == 9
    generic = [p for p in ports if p.resource is None]
    specific = [p for p in ports if p.resource is not None]
    assert len(generic) == 4
    assert all(p.ratio == 3 for p in generic)
    assert len(specific) == 5
    assert all(p.ratio == 2 for p in specific)
    assert {p.resource for p in specific} == set(Resource)


def test_ports_sit_on_coastal_edges():
    border_pairs = {
        e.node_ids for e in coords.BOARD.edges if len(e.hex_ids) == 1
    }
    for port in _board().ports:
        assert port.node_ids in border_pairs


def test_no_node_carries_two_ports():
    board = _board()
    seen = set()
    for port in board.ports:
        for node_id in port.node_ids:
            assert node_id not in seen
            seen.add(node_id)


def test_board_is_reproducible_from_seed():
    a = _board(123)
    b = _board(123)
    assert [h.terrain for h in a.hexes] == [h.terrain for h in b.hexes]
    assert [h.token for h in a.hexes] == [h.token for h in b.hexes]
    assert a.ports == b.ports
    assert a.robber_hex == b.robber_hex


def test_no_adjacent_high_or_matching_tokens():
    for seed in range(50):
        board = _board(seed)
        assert _tokens_valid(board.hexes)
        by_id = {h.hex_id: h.token for h in board.hexes}
        for h in board.hexes:
            if h.token is None:
                continue
            for nid in _hex_neighbor_ids(h.hex_id):
                other = by_id[nid]
                if other is None:
                    continue
                assert not (h.token in HIGH_TOKENS and other in HIGH_TOKENS)
                assert h.token != other
