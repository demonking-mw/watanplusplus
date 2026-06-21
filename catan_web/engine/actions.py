"""Authoritative state transitions for base Catan.

apply_action validates a single action against legal_actions, then mutates the
state in place and returns it. Randomness for dice and stealing is injected via
the rng argument so the state itself stays free of nondeterminism.
"""
from __future__ import annotations

from . import coords
from .board import RESOURCE_FOR_TERRAIN, Resource
from .state import Phase
from .legal import (
    Action,
    ActionType,
    COSTS,
    _best_ratio,
    _setup_progress,
    legal_actions,
    node_building,
    victory_points,
)


class IllegalAction(Exception):
    pass


def apply_action(state, player, action, rng=None):
    if action not in legal_actions(state, player):
        raise IllegalAction(
            f"Illegal action {action} for player {player} in phase {state.phase}"
        )

    t = action.type
    if t is ActionType.SETUP_SETTLEMENT:
        _apply_setup_settlement(state, player, action)
    elif t is ActionType.SETUP_ROAD:
        _apply_setup_road(state, player, action)
    elif t is ActionType.ROLL:
        _apply_roll(state, rng)
    elif t is ActionType.DISCARD:
        _apply_discard(state, player, action)
    elif t is ActionType.MOVE_ROBBER:
        _apply_move_robber(state, player, action, rng)
    elif t is ActionType.BUILD_ROAD:
        _apply_build_road(state, player, action)
    elif t is ActionType.BUILD_SETTLEMENT:
        _apply_build_settlement(state, player, action)
    elif t is ActionType.BUILD_CITY:
        _apply_build_city(state, player, action)
    elif t is ActionType.BANK_TRADE:
        _apply_bank_trade(state, player, action)
    elif t is ActionType.END_TURN:
        _apply_end_turn(state, player)
    return state


# Resource movement helpers. All movement is conserved against the bank.

def _take_from_bank(state, pl, resource, amount):
    amount = min(amount, state.bank[resource])
    state.bank[resource] -= amount
    pl.resources[resource] += amount
    return amount


def _pay_to_bank(state, pl, cost):
    for r, n in cost.items():
        pl.resources[r] -= n
        state.bank[r] += n


def _check_win(state, player):
    if victory_points(state.players[player]) >= 10:
        state.winner = player
        state.phase = Phase.GAME_OVER


# Setup.

def _apply_setup_settlement(state, player, action):
    pl = state.players[player]
    pl.settlements.add(action.node)
    if len(pl.settlements) == 2:
        for hex_id in coords.BOARD.node(action.node).hex_ids:
            res = RESOURCE_FOR_TERRAIN[state.board.hex(hex_id).terrain]
            if res is not None:
                _take_from_bank(state, pl, res, 1)


def _apply_setup_road(state, player, action):
    state.players[player].roads.add(action.edge)
    s, r = _setup_progress(state)
    if s >= 8 and r >= 8:
        state.phase = Phase.ROLL
        state.current_player = 0
        state.turn_number = 1
        state.has_rolled = False


# Rolling and production.

def _apply_roll(state, rng):
    d1, d2 = rng.roll_dice()
    total = d1 + d2
    state.dice = (d1, d2)
    state.has_rolled = True
    state.dice_history.append(total)
    state.dice_history = state.dice_history[-8:]

    if total == 7:
        pending = {}
        for p in state.players:
            hand = sum(p.resources.values())
            if hand > 7:
                pending[p.id] = hand // 2
        state.pending_discards = pending
        state.phase = Phase.DISCARD if pending else Phase.ROBBER
    else:
        _produce(state, total)
        state.phase = Phase.MAIN


def _produce(state, total):
    gains = {p.id: {r: 0 for r in Resource} for p in state.players}
    for bh in state.board.hexes:
        if bh.token != total or bh.hex_id == state.robber_hex:
            continue
        res = RESOURCE_FOR_TERRAIN[bh.terrain]
        if res is None:
            continue
        for node_id in coords.BOARD.hex(bh.hex_id).node_ids:
            b = node_building(state, node_id)
            if b is None:
                continue
            owner, kind = b
            gains[owner][res] += 2 if kind == "city" else 1

    for res in Resource:
        owed = {pid: g[res] for pid, g in gains.items() if g[res] > 0}
        if not owed:
            continue
        if state.bank[res] >= sum(owed.values()):
            for pid, amt in owed.items():
                _take_from_bank(state, state.players[pid], res, amt)
        elif len(owed) == 1:
            pid = next(iter(owed))
            _take_from_bank(state, state.players[pid], res, owed[pid])
        # multiple players owed but bank short: nobody receives this resource


# Discard and robber.

def _apply_discard(state, player, action):
    pl = state.players[player]
    pl.resources[action.resource] -= 1
    state.bank[action.resource] += 1
    state.pending_discards[player] -= 1
    if state.pending_discards[player] <= 0:
        del state.pending_discards[player]
    if not state.pending_discards:
        state.phase = Phase.ROBBER


def _apply_move_robber(state, player, action, rng):
    state.robber_hex = action.hex_id
    if action.victim is not None:
        victim = state.players[action.victim]
        cards = [r for r in Resource for _ in range(victim.resources[r])]
        if cards:
            stolen = rng.shuffle(cards)[0]
            victim.resources[stolen] -= 1
            state.players[player].resources[stolen] += 1
    state.phase = Phase.MAIN


# Building and trading.

def _apply_build_road(state, player, action):
    pl = state.players[player]
    _pay_to_bank(state, pl, COSTS["road"])
    pl.roads.add(action.edge)


def _apply_build_settlement(state, player, action):
    pl = state.players[player]
    _pay_to_bank(state, pl, COSTS["settlement"])
    pl.settlements.add(action.node)
    _check_win(state, player)


def _apply_build_city(state, player, action):
    pl = state.players[player]
    _pay_to_bank(state, pl, COSTS["city"])
    pl.settlements.discard(action.node)
    pl.cities.add(action.node)
    _check_win(state, player)


def _apply_bank_trade(state, player, action):
    pl = state.players[player]
    ratio = _best_ratio(pl, action.give, state.board.port_nodes())
    pl.resources[action.give] -= ratio
    state.bank[action.give] += ratio
    state.bank[action.get] -= 1
    pl.resources[action.get] += 1


def _apply_end_turn(state, player):
    pl = state.players[player]
    pl.has_played_dev_this_turn = False
    pl.dev_cards_bought_this_turn = []
    state.current_player = (player + 1) % 4
    state.turn_number += 1
    state.phase = Phase.ROLL
    state.has_rolled = False
    state.dice = None
