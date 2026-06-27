"""History and chat event formatting tests."""
from catan_web.engine.legal import Action, ActionType, legal_actions
from catan_web.net.history import action_event, chat_event, resource_snapshot
from catan_web.net.rooms import RoomManager


def _ws():
    return object()


def _started_room():
    m = RoomManager()
    room, _ = m.create("A", _ws())
    for name in ("B", "C", "D"):
        m.join(room.code, name, None, _ws())
    m.start(room.code, 0)
    return m, room


def test_chat_event_shape():
    e = chat_event(1, "Bob", "hello")
    assert e["kind"] == "chat"
    assert e["name"] == "Bob"
    assert e["text"] == "hello"


def test_setup_action_event():
    m, room = _started_room()
    acts = legal_actions(room.state, 0)
    assert acts
    action = acts[0]
    before = resource_snapshot(room.state)
    m.apply(room.code, 0, action)
    evt = action_event(room, 0, action, before)
    assert evt["kind"] == "action"
    assert "settlement" in evt["text"]


def test_room_chat_validation():
    m, room = _started_room()
    room, seat, text = m.chat(room.code, 0, "  hi there  ")
    assert text == "hi there"
    assert seat == 0
