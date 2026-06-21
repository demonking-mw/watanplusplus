"""Phase 2 game state tests."""
from collections import Counter

import pytest

from catan_web.engine.board import Resource
from catan_web.engine.state import (
    BANK_PER_RESOURCE,
    DevCard,
    PLAYER_COLORS,
    Phase,
    VP_DEV_CARDS,
    new_game_state,
)

NAMES = ["A", "B", "C", "D"]


def test_four_players_with_colors_and_empty_hands():
    state = new_game_state(42, NAMES)
    assert len(state.players) == 4
    for i, player in enumerate(state.players):
        assert player.id == i
        assert player.name == NAMES[i]
        assert player.color == PLAYER_COLORS[i]
        assert sum(player.resources.values()) == 0
        assert set(player.resources.keys()) == set(Resource)
        assert player.settlements == set()
        assert player.cities == set()
        assert player.roads == set()


def test_requires_exactly_four_players():
    with pytest.raises(ValueError):
        new_game_state(42, ["A", "B", "C"])


def test_bank_starts_full():
    state = new_game_state(42, NAMES)
    assert all(state.bank[r] == BANK_PER_RESOURCE for r in Resource)


def test_dev_deck_composition():
    deck = new_game_state(42, NAMES).dev_deck
    assert len(deck) == 25
    counts = Counter(deck)
    assert counts[DevCard.KNIGHT] == 14
    assert counts[DevCard.ROAD_BUILDING] == 2
    assert counts[DevCard.YEAR_OF_PLENTY] == 2
    assert counts[DevCard.MONOPOLY] == 2
    assert sum(counts[c] for c in VP_DEV_CARDS) == 5


def test_initial_turn_meta():
    state = new_game_state(42, NAMES)
    assert state.phase is Phase.SETUP
    assert state.current_player == 0
    assert state.turn_number == 0
    assert state.has_rolled is False
    assert state.winner is None
    assert state.robber_hex == state.board.robber_hex


def test_state_is_reproducible_from_seed():
    a = new_game_state(99, NAMES)
    b = new_game_state(99, NAMES)
    assert [h.terrain for h in a.board.hexes] == [h.terrain for h in b.board.hexes]
    assert a.dev_deck == b.dev_deck
