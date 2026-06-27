"""Per-player state views.

view_for_player builds the snapshot a single seat is allowed to see: its own
exact hand and dev cards, but only public counts for opponents. The server keeps
the full GameState for logging.
"""
from __future__ import annotations

from catan_web.engine.board import Resource
from catan_web.engine.legal import legal_actions, victory_points
from catan_web.export.logger import action_to_dict


def _buildings(state):
    settlements, cities, roads = {}, {}, {}
    for p in state.players:
        for n in p.settlements:
            settlements[n] = p.id
        for n in p.cities:
            cities[n] = p.id
        for e in p.roads:
            roads[e] = p.id
    return settlements, cities, roads


def _board(state):
    return {
        "hexes": [
            {"id": h.hex_id, "terrain": h.terrain.value, "token": h.token}
            for h in state.board.hexes
        ],
        "ports": [
            {
                "resource": port.resource.value if port.resource else None,
                "ratio": port.ratio,
                "nodes": list(port.node_ids),
            }
            for port in state.board.ports
        ],
    }


def public_state(room):
    state = room.state
    settlements, cities, roads = _buildings(state)
    return {
        "phase": state.phase.value,
        "current_player": state.current_player,
        "turn": state.turn_number,
        "dice": list(state.dice) if state.dice else None,
        "robber_hex": state.robber_hex,
        "winner": state.winner,
        "bank": {r.value: state.bank[r] for r in Resource},
        "pending_discards": {str(k): v for k, v in state.pending_discards.items()},
        "board": _board(state),
        "buildings": {
            "settlements": {str(k): v for k, v in settlements.items()},
            "cities": {str(k): v for k, v in cities.items()},
            "roads": {str(k): v for k, v in roads.items()},
        },
        "players": [
            {
                "seat": p.id,
                "name": room.names[p.id],
                "color": p.color,
                "vp": victory_points(p),
                "resource_count": sum(p.resources.values()),
                "dev_count": len(p.dev_cards),
                "knights": p.played_knights,
                "road_segments": len(p.roads),
            }
            for p in state.players
        ],
    }


def view_for_player(room, seat):
    view = public_state(room)
    view["you"] = seat
    pl = room.state.players[seat]
    view["your_resources"] = {r.value: pl.resources[r] for r in Resource}
    view["your_dev_cards"] = [c.value for c in pl.dev_cards]
    return view


def legal_for(room, seat):
    return [action_to_dict(a) for a in legal_actions(room.state, seat)]
