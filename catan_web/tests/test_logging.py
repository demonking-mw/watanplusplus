"""Phase 4 logging format tests. These do not depend on HDCS reconciliation."""
import json

from catan_web.engine.board import Resource
from catan_web.engine.legal import Action, ActionType
from catan_web.engine.state import new_game_state
from catan_web.export import logger

NAMES = ["A", "B", "C", "D"]


def test_action_to_dict_omits_none_and_serializes_enums():
    a = Action(ActionType.BANK_TRADE, give=Resource.ORE, get=Resource.GRAIN)
    assert logger.action_to_dict(a) == {
        "type": "bank_trade",
        "give": "ore",
        "get": "grain",
    }


def test_append_record_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(logger, "DATA_DIR", tmp_path)
    logger.append_record("g", {"seq": 1, "ok": True})
    line = (tmp_path / "g.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(line) == {"seq": 1, "ok": True}


def test_write_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(logger, "DATA_DIR", tmp_path)
    state = new_game_state(5, NAMES)
    meta = logger.write_meta("g", state, NAMES)
    assert meta["seed"] == 5
    assert meta["final_vps"] == [0, 0, 0, 0]
    assert (tmp_path / "g.meta.json").exists()
