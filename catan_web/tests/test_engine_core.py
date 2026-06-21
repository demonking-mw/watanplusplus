"""Phase 3 engine core tests."""
import pytest

from catan_web.engine import coords
from catan_web.engine.actions import IllegalAction, apply_action
from catan_web.engine.board import Resource
from catan_web.engine.legal import (
    Action,
    ActionType,
    legal_actions,
    victory_points,
)
from catan_web.engine.rng import GameRandom
from catan_web.engine.state import Phase, new_game_state

NAMES = ["A", "B", "C", "D"]
EXPECTED_TOTAL = 5 * 19


def _find_actor(state):
    for p in range(4):
        acts = legal_actions(state, p)
        if acts:
            return p, acts
    return None, []


def _play_setup(state, rng):
    while state.phase is Phase.SETUP:
        p, acts = _find_actor(state)
        apply_action(state, p, acts[0], rng)


def _total_resources(state):
    total = sum(state.bank.values())
    for pl in state.players:
        total += sum(pl.resources.values())
    return total


def test_first_setup_offers_every_node():
    state = new_game_state(1, NAMES)
    acts = legal_actions(state, 0)
    assert len(acts) == coords.NUM_NODES
    assert all(a.type is ActionType.SETUP_SETTLEMENT for a in acts)
    assert legal_actions(state, 1) == []


def test_distance_rule_excludes_neighbors():
    state = new_game_state(1, NAMES)
    rng = GameRandom(1)
    apply_action(state, 0, Action(ActionType.SETUP_SETTLEMENT, node=0), rng)
    road = legal_actions(state, 0)[0]
    apply_action(state, 0, road, rng)
    nodes = {a.node for a in legal_actions(state, 1)}
    blocked = {0} | set(coords.BOARD.node(0).neighbor_ids)
    assert nodes.isdisjoint(blocked)


def test_setup_completes_and_grants_resources():
    state = new_game_state(7, NAMES)
    _play_setup(state, GameRandom(7))
    assert state.phase is Phase.ROLL
    assert state.current_player == 0
    assert state.turn_number == 1
    for p in state.players:
        assert len(p.settlements) == 2
        assert len(p.roads) == 2
    assert _total_resources(state) == EXPECTED_TOTAL
    assert sum(sum(p.resources.values()) for p in state.players) > 0


def test_roads_must_connect_to_network():
    state = new_game_state(7, NAMES)
    _play_setup(state, GameRandom(7))
    p0 = state.players[0]
    state.phase = Phase.MAIN
    state.current_player = 0
    state.has_rolled = True
    p0.resources[Resource.LUMBER] += 1
    p0.resources[Resource.BRICK] += 1
    roads = [a for a in legal_actions(state, 0) if a.type is ActionType.BUILD_ROAD]
    assert roads
    for a in roads:
        edge = coords.BOARD.edge(a.edge)
        connected = False
        for n in edge.node_ids:
            if n in p0.settlements or n in p0.cities:
                connected = True
            for inc in coords.BOARD.node(n).edge_ids:
                if inc in p0.roads:
                    connected = True
        assert connected


def test_generic_port_trades_three_to_one():
    state = new_game_state(11, NAMES)
    generic = next(p for p in state.board.ports if p.resource is None)
    p0 = state.players[0]
    state.phase = Phase.MAIN
    state.current_player = 0
    state.has_rolled = True
    for r in Resource:
        p0.resources[r] = 0
    p0.resources[Resource.LUMBER] = 3

    p0.settlements = {generic.node_ids[0]}
    have_port = legal_actions(state, 0)
    assert any(
        a.type is ActionType.BANK_TRADE and a.give is Resource.LUMBER
        for a in have_port
    )

    p0.settlements = set()
    no_port = legal_actions(state, 0)
    assert not any(
        a.type is ActionType.BANK_TRADE and a.give is Resource.LUMBER
        for a in no_port
    )


def test_specific_port_trades_two_to_one():
    state = new_game_state(13, NAMES)
    spec = next(p for p in state.board.ports if p.resource is not None)
    other = next(r for r in Resource if r != spec.resource)
    p0 = state.players[0]
    state.phase = Phase.MAIN
    state.current_player = 0
    state.has_rolled = True
    for r in Resource:
        p0.resources[r] = 0
    p0.resources[spec.resource] = 2
    p0.resources[other] = 2
    p0.settlements = {spec.node_ids[0]}

    acts = legal_actions(state, 0)
    assert any(
        a.type is ActionType.BANK_TRADE and a.give is spec.resource for a in acts
    )
    assert not any(
        a.type is ActionType.BANK_TRADE and a.give is other for a in acts
    )


def test_illegal_actions_raise():
    state = new_game_state(5, NAMES)
    with pytest.raises(IllegalAction):
        apply_action(state, 1, Action(ActionType.SETUP_SETTLEMENT, node=0), GameRandom(0))
    with pytest.raises(IllegalAction):
        apply_action(state, 0, Action(ActionType.ROLL), GameRandom(0))


def test_win_by_building_city():
    state = new_game_state(3, NAMES)
    p0 = state.players[0]
    p0.cities = {0, 1, 2}
    p0.settlements = {3, 4, 5}
    for r in Resource:
        p0.resources[r] = 0
    p0.resources[Resource.ORE] = 3
    p0.resources[Resource.GRAIN] = 2
    state.phase = Phase.MAIN
    state.current_player = 0
    state.has_rolled = True

    assert victory_points(p0) == 9
    apply_action(state, 0, Action(ActionType.BUILD_CITY, node=3), GameRandom(0))
    assert state.winner == 0
    assert state.phase is Phase.GAME_OVER
    assert victory_points(state.players[0]) == 10


def test_random_playthrough_conserves_resources():
    seed = 2024
    state = new_game_state(seed, NAMES)
    rng = GameRandom(seed)
    order = [
        ActionType.SETUP_SETTLEMENT,
        ActionType.SETUP_ROAD,
        ActionType.DISCARD,
        ActionType.MOVE_ROBBER,
        ActionType.ROLL,
        ActionType.BUILD_CITY,
        ActionType.BUILD_SETTLEMENT,
        ActionType.BUILD_ROAD,
        ActionType.END_TURN,
    ]

    def choose(acts):
        for t in order:
            for a in acts:
                if a.type is t:
                    return a
        return acts[0]

    steps = 0
    while state.phase is not Phase.GAME_OVER and steps < 3000:
        p, acts = _find_actor(state)
        assert p is not None, f"No actor available in phase {state.phase}"
        apply_action(state, p, choose(acts), rng)
        assert _total_resources(state) == EXPECTED_TOTAL
        steps += 1

    assert steps > 30
    if state.phase is Phase.GAME_OVER:
        assert state.winner is not None
