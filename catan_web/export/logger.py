"""Append game records to JSONL logs under catan_web/data."""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def append_record(game_id: str, record: dict) -> None:
    """Append one JSON record as a single line to data/{game_id}.jsonl."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{game_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
