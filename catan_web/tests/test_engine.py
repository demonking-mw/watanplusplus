"""Scaffold smoke tests. Real rule tests arrive in Phases 1 to 3."""
from catan_web.engine import coords
from catan_web.engine.rng import GameRandom
from catan_web.export.logger import append_record, DATA_DIR


def test_board_constants():
    assert coords.NUM_HEXES == 19
    assert coords.NUM_NODES == 54
    assert coords.NUM_EDGES == 72


def test_rng_is_reproducible():
    a = GameRandom(42)
    b = GameRandom(42)
    rolls_a = [a.roll_dice() for _ in range(5)]
    rolls_b = [b.roll_dice() for _ in range(5)]
    assert rolls_a == rolls_b


def test_logger_writes_jsonl(tmp_path, monkeypatch):
    import catan_web.export.logger as logger
    monkeypatch.setattr(logger, "DATA_DIR", tmp_path)
    logger.append_record("game_test", {"seq": 1, "ok": True})
    out = tmp_path / "game_test.jsonl"
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip() == '{"seq": 1, "ok": true}'
