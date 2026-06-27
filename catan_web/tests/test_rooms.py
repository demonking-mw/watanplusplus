"""Phase 5 networking tests against the RoomManager and redaction."""
import pytest

from catan_web.engine.board import Resource
from catan_web.engine.legal import ActionType, legal_actions
from catan_web.engine.state import Phase
from catan_web.net.redact import view_for_player
from catan_web.net.rooms import GameError, RoomManager

EXPECTED_TOTAL = 5 * 19
PUBLIC_KEYS = {
    "seat", "name", "color", "vp", "resource_count",
    "dev_count", "knights", "road_segments",
}


def _ws():
    return object()


def _full_room():
    m = RoomManager()
    room, _ = m.create("A", _ws())
    for name in ("B", "C", "D"):
        m.join(room.code, name, None, _ws())
    return m, room


def test_create_and_join_assign_sequential_seats():
    m, room = _full_room()
    assert [s.seat for s in room.seats] == [0, 1, 2, 3]
    assert [s.name for s in room.seats] == ["A", "B", "C", "D"]


def test_join_full_room_is_rejected():
    m, room = _full_room()
    with pytest.raises(GameError):
        m.join(room.code, "E", None, _ws())


def test_start_requires_four_players_and_host():
    m = RoomManager()
    room, _ = m.create("A", _ws())
    with pytest.raises(GameError):
        m.start(room.code, 0)
    for name in ("B", "C", "D"):
        m.join(room.code, name, None, _ws())
    with pytest.raises(GameError):
        m.start(room.code, 1)
    m.start(room.code, 0)
    assert room.started


def test_reconnect_by_token_restores_seat():
    m = RoomManager()
    ws0 = _ws()
    room, s0 = m.create("A", ws0)
    m.disconnect(ws0)
    assert room.seats[0].connected is False
    room2, s = m.join(room.code, "A", s0.token, _ws())
    assert s.seat == 0
    assert room.seats[0].connected is True


def test_redaction_hides_opponent_hands():
    m, room = _full_room()
    m.start(room.code, 0)
    room.state.players[1].resources[Resource.ORE] = 3

    view = view_for_player(room, 0)
    assert view["you"] == 0
    assert view["your_resources"] == {
        r.value: room.state.players[0].resources[r] for r in Resource
    }
    opponent = view["players"][1]
    assert set(opponent.keys()) == PUBLIC_KEYS
    assert opponent["resource_count"] == 3


def test_manager_full_game_conserves_resources():
    m, room = _full_room()
    m.start(room.code, 0)
    order = [
        ActionType.SETUP_SETTLEMENT, ActionType.SETUP_ROAD,
        ActionType.DISCARD, ActionType.MOVE_ROBBER, ActionType.ROLL,
        ActionType.BUILD_CITY, ActionType.BUILD_SETTLEMENT,
        ActionType.BUILD_ROAD, ActionType.END_TURN,
    ]

    def choose(acts):
        for t in order:
            for a in acts:
                if a.type is t:
                    return a
        return acts[0]

    def total():
        out = sum(room.state.bank.values())
        for p in room.state.players:
            out += sum(p.resources.values())
        return out

    steps = 0
    while room.state.phase is not Phase.GAME_OVER and steps < 3000:
        actor, acts = None, []
        for p in range(4):
            a = legal_actions(room.state, p)
            if a:
                actor, acts = p, a
                break
        assert actor is not None
        m.apply(room.code, actor, choose(acts))
        assert total() == EXPECTED_TOTAL
        # every seat can build a redacted view without leaking opponents
        for seat in range(4):
            v = view_for_player(room, seat)
            assert set(v["players"][(seat + 1) % 4].keys()) == PUBLIC_KEYS
        steps += 1

    assert steps > 30
