"""JSONL logging for catan_web games.

Each applied action appends one record to data/{game_id}.jsonl, and a meta file
is written when the game ends. Records carry a ground truth HDCS snapshot so the
project tooling can consume them directly.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from catan_web.engine.legal import victory_points
from catan_web.export.hdcs import to_hdcs

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_record(game_id: str, record: dict) -> None:
    """Append one JSON record as a single line to data/{game_id}.jsonl."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{game_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def action_to_dict(action) -> dict:
    """Serialize an engine Action to a compact JSON friendly dict."""
    out = {"type": action.type.value}
    for name in ("node", "edge", "hex_id", "victim"):
        value = getattr(action, name)
        if value is not None:
            out[name] = value
    for name in ("resource", "give", "get"):
        value = getattr(action, name)
        if value is not None:
            out[name] = value.value
    return out


def log_action(game_id: str, seq: int, actor: int, action, state) -> dict:
    """Build, append, and return the decision record for one applied action."""
    record = {
        "seq": seq,
        "ts": _now_iso(),
        "actor": actor,
        "action": action_to_dict(action),
        "hdcs": to_hdcs(state),
    }
    append_record(game_id, record)
    return record


def write_meta(game_id: str, state, names) -> dict:
    """Write the end of game meta file and return it."""
    meta = {
        "game_id": game_id,
        "seed": state.seed,
        "winner": state.winner,
        "final_vps": [victory_points(p) for p in state.players],
        "names": list(names),
        "turns": state.turn_number,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{game_id}.meta.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta
