"""Game state model and turn phases for base 4 player Catan.

Defines the players, bank, development card deck, and turn meta, and the
factory that builds a fresh game from a seed. The board overlay (terrain,
tokens, ports, robber) comes from board.generate_board.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .board import Board, Resource, generate_board
from .rng import GameRandom


class Phase(str, Enum):
    LOBBY = "lobby"
    SETUP = "setup"
    ROLL = "roll"
    MAIN = "main"
    DISCARD = "discard"
    ROBBER = "robber"
    GAME_OVER = "game_over"


class DevCard(str, Enum):
    KNIGHT = "knight"
    ROAD_BUILDING = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"
    CHAPEL = "chapel"
    LIBRARY = "library"
    MARKET = "market"
    PALACE = "palace"
    UNIVERSITY = "university"


# The five development cards worth a victory point.
VP_DEV_CARDS = frozenset(
    {
        DevCard.CHAPEL,
        DevCard.LIBRARY,
        DevCard.MARKET,
        DevCard.PALACE,
        DevCard.UNIVERSITY,
    }
)

PLAYER_COLORS = ("red", "blue", "white", "orange")
BANK_PER_RESOURCE = 19


@dataclass
class Player:
    id: int
    name: str
    color: str
    resources: dict = field(default_factory=dict)
    dev_cards: list = field(default_factory=list)
    dev_cards_bought_this_turn: list = field(default_factory=list)
    played_knights: int = 0
    settlements: set = field(default_factory=set)
    cities: set = field(default_factory=set)
    roads: set = field(default_factory=set)
    has_played_dev_this_turn: bool = False


@dataclass
class GameState:
    seed: int
    board: Board
    players: list
    bank: dict
    dev_deck: list
    robber_hex: int
    current_player: int = 0
    phase: Phase = Phase.SETUP
    dice: tuple | None = None
    has_rolled: bool = False
    turn_number: int = 0
    dice_history: list = field(default_factory=list)
    pending_discards: dict = field(default_factory=dict)
    longest_road_holder: int | None = None
    longest_road_length: int = 0
    largest_army_holder: int | None = None
    winner: int | None = None


def empty_resources() -> dict:
    """A resource dict with zero of every resource."""
    return {resource: 0 for resource in Resource}


def new_bank() -> dict:
    """The starting bank, 19 of every resource."""
    return {resource: BANK_PER_RESOURCE for resource in Resource}


def build_dev_deck(rng: GameRandom) -> list:
    """The shuffled 25 card development deck."""
    deck = (
        [DevCard.KNIGHT] * 14
        + [DevCard.ROAD_BUILDING] * 2
        + [DevCard.YEAR_OF_PLENTY] * 2
        + [DevCard.MONOPOLY] * 2
        + [
            DevCard.CHAPEL,
            DevCard.LIBRARY,
            DevCard.MARKET,
            DevCard.PALACE,
            DevCard.UNIVERSITY,
        ]
    )
    return rng.shuffle(deck)


def new_game_state(seed: int, player_names: list) -> GameState:
    """Create the initial state for a four player game."""
    if len(player_names) != 4:
        raise ValueError("Base Catan requires exactly four players")

    rng = GameRandom(seed)
    board = generate_board(rng)
    players = [
        Player(
            id=i,
            name=player_names[i],
            color=PLAYER_COLORS[i],
            resources=empty_resources(),
        )
        for i in range(4)
    ]
    deck = build_dev_deck(rng)
    return GameState(
        seed=seed,
        board=board,
        players=players,
        bank=new_bank(),
        dev_deck=deck,
        robber_hex=board.robber_hex,
    )
