"""Game history and chat event formatting for the WebSocket protocol."""
from __future__ import annotations

from catan_web.engine.board import Resource
from catan_web.engine.legal import Action, ActionType


def resource_snapshot(state) -> dict[int, dict[str, int]]:
    return {
        p.id: {r.value: p.resources[r] for r in Resource}
        for p in state.players
    }


def _diff_resources(before: dict, after: dict) -> dict[int, dict[str, int]]:
    out: dict[int, dict[str, int]] = {}
    for pid in before:
        gained = {}
        for res, amt in after[pid].items():
            delta = amt - before[pid][res]
            if delta > 0:
                gained[res] = delta
        if gained:
            out[pid] = gained
    return out


def _fmt_gains(name: str, gains: dict[str, int]) -> str:
    parts = [f"{n} {r}" for r, n in sorted(gains.items())]
    return f"{name} received {', '.join(parts)}"


def action_event(room, seat: int, action: Action, before_snap: dict) -> dict:
    """Build one history entry after an action is applied."""
    state = room.state
    name = room.names[seat]
    after = resource_snapshot(state)

    if action.type is ActionType.ROLL:
        d1, d2 = state.dice
        total = d1 + d2
        text = f"{name} rolled {d1} + {d2} = {total}"
        if total == 7:
            text += " (robber)"
        else:
            gains = _diff_resources(before_snap, after)
            if gains:
                parts = [_fmt_gains(room.names[pid], g) for pid, g in sorted(gains.items())]
                text += ". " + "; ".join(parts)
            else:
                text += ". No resources produced"
        return {"kind": "action", "seat": seat, "name": name, "text": text}

    if action.type is ActionType.SETUP_SETTLEMENT:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} placed a settlement",
        }
    if action.type is ActionType.SETUP_ROAD:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} placed a road",
        }
    if action.type is ActionType.BUILD_SETTLEMENT:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} built a settlement",
        }
    if action.type is ActionType.BUILD_CITY:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} built a city",
        }
    if action.type is ActionType.BUILD_ROAD:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} built a road",
        }
    if action.type is ActionType.BANK_TRADE:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": (
                f"{name} traded {action.give.value} for {action.get.value}"
            ),
        }
    if action.type is ActionType.DISCARD:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} discarded {action.resource.value}",
        }
    if action.type is ActionType.MOVE_ROBBER:
        if action.victim is None:
            victim = "no one"
        else:
            victim = room.names[action.victim]
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} moved the robber and stole from {victim}",
        }
    if action.type is ActionType.END_TURN:
        return {
            "kind": "action", "seat": seat, "name": name,
            "text": f"{name} ended their turn",
        }
    return {"kind": "action", "seat": seat, "name": name, "text": f"{name} acted"}


def chat_event(seat: int, name: str, text: str) -> dict:
    return {"kind": "chat", "seat": seat, "name": name, "text": text}
