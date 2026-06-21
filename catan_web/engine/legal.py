"""Legal action generation for base Catan.

Pure read only queries over a GameState. legal_actions(state, player) returns
every action that player may legally take right now. apply_action in actions.py
validates against this set before mutating. Dev cards, longest road, largest
army, and player trades arrive in Phase 7.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from . import coords
from .board import Resource
from .state import Phase

MAX_SETTLEMENTS = 5
MAX_CITIES = 4
MAX_ROADS = 15

# Snake order for the two setup placement rounds.
SETUP_ORDER = (0, 1, 2, 3, 3, 2, 1, 0)

COSTS = {
    "road": {Resource.LUMBER: 1, Resource.BRICK: 1},
    "settlement": {
        Resource.LUMBER: 1,
        Resource.BRICK: 1,
        Resource.WOOL: 1,
        Resource.GRAIN: 1,
    },
    "city": {Resource.ORE: 3, Resource.GRAIN: 2},
}


class ActionType(str, Enum):
    SETUP_SETTLEMENT = "setup_settlement"
    SETUP_ROAD = "setup_road"
    ROLL = "roll"
    DISCARD = "discard"
    MOVE_ROBBER = "move_robber"
    BUILD_ROAD = "build_road"
    BUILD_SETTLEMENT = "build_settlement"
    BUILD_CITY = "build_city"
    BANK_TRADE = "bank_trade"
    END_TURN = "end_turn"


@dataclass(frozen=True)
class Action:
    type: ActionType
    node: int | None = None
    edge: int | None = None
    hex_id: int | None = None
    victim: int | None = None
    resource: Resource | None = None    # for DISCARD
    give: Resource | None = None        # for BANK_TRADE
    get: Resource | None = None         # for BANK_TRADE


# Board occupancy queries.

def node_building(state, node_id):
    """Return (owner_id, kind) for a node, kind being settlement or city."""
    for p in state.players:
        if node_id in p.cities:
            return (p.id, "city")
        if node_id in p.settlements:
            return (p.id, "settlement")
    return None


def node_owner(state, node_id):
    b = node_building(state, node_id)
    return b[0] if b else None


def edge_owner(state, edge_id):
    for p in state.players:
        if edge_id in p.roads:
            return p.id
    return None


def victory_points(player) -> int:
    """Public victory points from buildings. Awards and dev cards in Phase 7."""
    return len(player.settlements) + 2 * len(player.cities)


# Placement rules.

def _distance_ok(state, node_id) -> bool:
    if node_owner(state, node_id) is not None:
        return False
    for nb in coords.BOARD.node(node_id).neighbor_ids:
        if node_owner(state, nb) is not None:
            return False
    return True


def _settlement_connected(state, player, node_id) -> bool:
    roads = state.players[player].roads
    return any(e in roads for e in coords.BOARD.node(node_id).edge_ids)


def _road_connects(state, player, edge) -> bool:
    roads = state.players[player].roads
    for n in edge.node_ids:
        owner = node_owner(state, n)
        if owner == player:
            return True
        if owner is not None:
            continue
        for inc in coords.BOARD.node(n).edge_ids:
            if inc != edge.id and inc in roads:
                return True
    return False


def _can_afford(player, cost) -> bool:
    return all(player.resources[r] >= n for r, n in cost.items())


def _best_ratio(player, give, port_nodes) -> int:
    ratio = 4
    for node_id in (player.settlements | player.cities):
        port = port_nodes.get(node_id)
        if port is None:
            continue
        if port.resource is None:
            ratio = min(ratio, 3)
        elif port.resource == give:
            ratio = min(ratio, 2)
    return ratio


# Setup progress.

def _setup_progress(state):
    placed_settlements = sum(len(p.settlements) for p in state.players)
    placed_roads = sum(len(p.roads) for p in state.players)
    return placed_settlements, placed_roads


def _setup_actor_and_piece(state):
    s, r = _setup_progress(state)
    if s >= 8 and r >= 8:
        return None, None
    if s == r:
        return SETUP_ORDER[s], "settlement"
    return SETUP_ORDER[r], "road"


def _pending_setup_settlement(state, player):
    pl = state.players[player]
    for node_id in pl.settlements:
        incident = coords.BOARD.node(node_id).edge_ids
        if not any(e in pl.roads for e in incident):
            return node_id
    return None


# Action generators per phase.

def _setup_actions(state, player):
    actor, piece = _setup_actor_and_piece(state)
    if actor is None or player != actor:
        return []
    if piece == "settlement":
        return [
            Action(ActionType.SETUP_SETTLEMENT, node=n)
            for n in range(coords.NUM_NODES)
            if _distance_ok(state, n)
        ]
    node = _pending_setup_settlement(state, player)
    if node is None:
        return []
    return [
        Action(ActionType.SETUP_ROAD, edge=e)
        for e in coords.BOARD.node(node).edge_ids
        if edge_owner(state, e) is None
    ]


def _discard_actions(state, player):
    if state.pending_discards.get(player, 0) <= 0:
        return []
    pl = state.players[player]
    return [
        Action(ActionType.DISCARD, resource=r)
        for r in Resource
        if pl.resources[r] > 0
    ]


def _robber_victims(state, player, hex_id):
    victims = set()
    for node_id in coords.BOARD.hex(hex_id).node_ids:
        b = node_building(state, node_id)
        if b is None:
            continue
        owner, _ = b
        if owner != player and sum(state.players[owner].resources.values()) > 0:
            victims.add(owner)
    return victims


def _robber_actions(state, player):
    acts = []
    for h in coords.BOARD.hexes:
        if h.id == state.robber_hex:
            continue
        victims = _robber_victims(state, player, h.id)
        if victims:
            for v in sorted(victims):
                acts.append(Action(ActionType.MOVE_ROBBER, hex_id=h.id, victim=v))
        else:
            acts.append(Action(ActionType.MOVE_ROBBER, hex_id=h.id, victim=None))
    return acts


def _main_actions(state, player):
    pl = state.players[player]
    acts = [Action(ActionType.END_TURN)]

    if _can_afford(pl, COSTS["road"]) and len(pl.roads) < MAX_ROADS:
        for e in coords.BOARD.edges:
            if edge_owner(state, e.id) is None and _road_connects(state, player, e):
                acts.append(Action(ActionType.BUILD_ROAD, edge=e.id))

    if _can_afford(pl, COSTS["settlement"]) and len(pl.settlements) < MAX_SETTLEMENTS:
        for n in range(coords.NUM_NODES):
            if _distance_ok(state, n) and _settlement_connected(state, player, n):
                acts.append(Action(ActionType.BUILD_SETTLEMENT, node=n))

    if _can_afford(pl, COSTS["city"]) and len(pl.cities) < MAX_CITIES:
        for n in sorted(pl.settlements):
            acts.append(Action(ActionType.BUILD_CITY, node=n))

    port_nodes = state.board.port_nodes()
    for give in Resource:
        ratio = _best_ratio(pl, give, port_nodes)
        if pl.resources[give] >= ratio:
            for get in Resource:
                if get != give and state.bank[get] > 0:
                    acts.append(Action(ActionType.BANK_TRADE, give=give, get=get))

    return acts


def legal_actions(state, player):
    phase = state.phase
    if phase is Phase.GAME_OVER:
        return []
    if phase is Phase.SETUP:
        return _setup_actions(state, player)
    if phase is Phase.ROLL:
        if player != state.current_player or state.has_rolled:
            return []
        return [Action(ActionType.ROLL)]
    if phase is Phase.DISCARD:
        return _discard_actions(state, player)
    if phase is Phase.ROBBER:
        if player != state.current_player:
            return []
        return _robber_actions(state, player)
    if phase is Phase.MAIN:
        if player != state.current_player:
            return []
        return _main_actions(state, player)
    return []
