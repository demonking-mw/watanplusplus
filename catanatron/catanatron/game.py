"""
Contains Game class which is a thin-wrapper around the State class.
"""

import uuid
import random
import sys
from typing import Sequence, Union, Optional

from catanatron.models.actions import generate_playable_actions
from catanatron.models.enums import Action, ActionPrompt, ActionRecord, ActionType
from catanatron.state import State
from catanatron.apply_action import apply_action
from catanatron.state_functions import player_key, player_has_rolled
from catanatron.models.map import CatanMap
from catanatron.models.player import Color, Player

# To timeout RandomRobots from getting stuck...
TURNS_LIMIT = 1000


def is_valid_action(playable_actions, state: State, action: Action) -> bool:
    """True if its a valid action right now. An action is valid
    if its in playable_actions or if its a OFFER_TRADE in the right time."""
    if action.action_type == ActionType.OFFER_TRADE:
        return (
            state.current_color() == action.color
            and state.current_prompt == ActionPrompt.PLAY_TURN
            and player_has_rolled(state, action.color)
            and is_valid_trade(action.value)
        )
    
    # Special handling for CONFIRM_TRADE: allow direct trades (bypassing offer/accept flow)
    if action.action_type == ActionType.CONFIRM_TRADE:
        if not (state.current_color() == action.color
                and state.current_prompt == ActionPrompt.PLAY_TURN
                and player_has_rolled(state, action.color)):
            return False
        
        # Validate trade value structure (11-tuple: first 10 are resources, last is Color)
        if not isinstance(action.value, (tuple, list)) or len(action.value) != 11:
            return False
        
        # Validate the trade itself (first 10 elements)
        trade_value = action.value[:10]
        if not is_valid_trade(trade_value):
            return False
        
        # Validate that the enemy color is valid
        enemy_color = action.value[10]
        # enemy_color should already be a Color enum from JSON parsing
        # But handle both cases for safety
        if isinstance(enemy_color, str):
            from catanatron.models.player import Color
            try:
                enemy_color_enum = Color[enemy_color]
            except KeyError:
                return False
        else:
            enemy_color_enum = enemy_color
        
        # Check if enemy is a valid player and not the same as offerer
        if enemy_color_enum not in state.colors or enemy_color_enum == action.color:
            return False
        
        return True
    
    # Special handling for MARITIME_TRADE: allow custom bank trades
    # If there's a MARITIME_TRADE action in playable_actions, accept any valid MARITIME_TRADE
    if action.action_type == ActionType.MARITIME_TRADE:
        # Check basic conditions: current player's turn, has rolled, correct prompt
        if not (state.current_color() == action.color
                and state.current_prompt == ActionPrompt.PLAY_TURN
                and player_has_rolled(state, action.color)):
            return False
        
        # Check if MARITIME_TRADE is a playable action (any maritime trade available)
        has_maritime_trade = any(
            a.action_type == ActionType.MARITIME_TRADE and a.color == action.color 
            for a in playable_actions
        )
        if not has_maritime_trade:
            return False
        
        # Validate trade value structure (5-tuple: first 4 are giving resources, last is receiving)
        if not isinstance(action.value, (tuple, list)) or len(action.value) != 5:
            return False
        
        # Validate that the receiving resource is valid
        receiving_resource = action.value[4]
        if receiving_resource is None:
            return False
        
        # Validate that giving resources are valid (can be None for port trades)
        giving_resources = action.value[:4]
        from catanatron.models.enums import RESOURCES
        for resource in giving_resources:
            if resource is not None and resource not in RESOURCES:
                return False
        if receiving_resource not in RESOURCES:
            return False
        
        # Check that at least one resource is being given
        if all(r is None for r in giving_resources):
            return False
        
        return True
    
    # Special handling for DISCARD actions: allow manual resource selection
    # If there's a DISCARD action in playable_actions, accept any DISCARD action
    # as long as the resource list is valid (None or list of valid resources)
    if action.action_type == ActionType.DISCARD:
        # Check if DISCARD is a playable action
        has_discard_action = any(
            a.action_type == ActionType.DISCARD and a.color == action.color 
            for a in playable_actions
        )
        if not has_discard_action:
            import logging
            logging.warning(f"DISCARD action not in playable_actions for {action.color}")
            return False
        
        # Validate that it's the current player's turn and they need to discard
        if not (state.current_color() == action.color
                and state.current_prompt == ActionPrompt.DISCARD):
            import logging
            logging.warning(f"DISCARD validation failed: current_color={state.current_color()}, action.color={action.color}, current_prompt={state.current_prompt}")
            return False
        
        # Validate resource list if provided
        if action.value is not None:
            if not isinstance(action.value, (tuple, list)):
                import logging
                logging.warning(f"DISCARD value is not a list/tuple: {type(action.value)}")
                return False
            from catanatron.models.enums import RESOURCES
            # Check all resources in the list are valid
            for resource in action.value:
                if resource not in RESOURCES:
                    import logging
                    logging.warning(f"Invalid resource in DISCARD: {resource}, valid resources: {RESOURCES}")
                    return False
            # Check that the number of resources matches what should be discarded
            from catanatron.state_functions import player_deck_to_array
            hand = player_deck_to_array(state, action.color)
            num_to_discard = len(hand) // 2
            if len(action.value) != num_to_discard:
                import logging
                logging.warning(f"DISCARD count mismatch: expected {num_to_discard}, got {len(action.value)}")
                return False
            # Check that player actually has these resources
            from catanatron.state_functions import player_key
            key = player_key(state, action.color)
            resource_counts = {
                'WOOD': state.player_state.get(f"{key}_WOOD_IN_HAND", 0),
                'BRICK': state.player_state.get(f"{key}_BRICK_IN_HAND", 0),
                'SHEEP': state.player_state.get(f"{key}_SHEEP_IN_HAND", 0),
                'WHEAT': state.player_state.get(f"{key}_WHEAT_IN_HAND", 0),
                'ORE': state.player_state.get(f"{key}_ORE_IN_HAND", 0),
            }
            from collections import Counter
            discard_counts = Counter(action.value)
            for resource, count in discard_counts.items():
                if resource not in resource_counts or resource_counts[resource] < count:
                    import logging
                    logging.warning(f"Player doesn't have enough {resource}: has {resource_counts.get(resource, 0)}, trying to discard {count}")
                    return False
        
        return True
    
    # Special handling for ROLL actions: allow manual dice selection
    # If there's a ROLL action in playable_actions, accept any ROLL action
    # as long as the dice values are valid (None or tuple of 2 ints between 1-6)
    if action.action_type == ActionType.ROLL:
        # Check if ROLL is a playable action (regardless of value)
        has_roll_action = any(
            a.action_type == ActionType.ROLL and a.color == action.color 
            for a in playable_actions
        )
        if not has_roll_action:
            return False
        
        # Validate dice values if provided
        if action.value is not None:
            if not isinstance(action.value, (tuple, list)) or len(action.value) != 2:
                return False
            if not (1 <= action.value[0] <= 6 and 1 <= action.value[1] <= 6):
                return False
        
        return True

    return action in playable_actions


def is_valid_trade(action_value):
    """Checks the value of a OFFER_TRADE does not
    give away resources or trade matching resources.
    """
    offering = action_value[:5]
    asking = action_value[5:]
    if sum(offering) == 0 or sum(asking) == 0:
        return False  # cant give away cards

    for i, j in zip(offering, asking):
        if i > 0 and j > 0:
            return False  # cant trade same resources
    return True


class GameAccumulator:
    """Interface to hook into different game lifecycle events.

    Useful to compute aggregate statistics, log information, etc...
    """

    def __init__(*args, **kwargs):
        pass

    def before(self, game):
        """
        Called when the game is created, no actions have
        been taken by players yet, but the board is decided.
        """
        pass

    def step(self, game_before_action, action):
        """
        Called after each action taken by a player.
        Game should be right before action is taken.
        """
        pass

    def after(self, game):
        """
        Called when the game is finished.

        Check game.winning_color() to see if the game
        actually finished or exceeded turn limit (is None).
        """
        pass


class Game:
    """
    Initializes a map, decides player seating order, and exposes two main
    methods for executing the game (play and play_tick; to advance until
    completion or just by one decision by a player respectively).

    Attributes:
        state (State): Current game state.
        playable_actions (List[Action]): List of playable actions by current player.
    """

    def __init__(
        self,
        players: Sequence[Player],
        seed: Optional[int] = None,
        discard_limit: int = 7,
        vps_to_win: int = 10,
        catan_map: Optional[CatanMap] = None,
        initialize: bool = True,
    ):
        """Creates a game (doesn't run it).

        Args:
            players (List[Player]): list of players, should be at most 4.
            seed (int, optional): Random seed to use (for reproducing games). Defaults to None.
            discard_limit (int, optional): Discard limit to use. Defaults to 7.
            vps_to_win (int, optional): Victory Points needed to win. Defaults to 10.
            catan_map (CatanMap, optional): Map to use. Defaults to None.
            initialize (bool, optional): Whether to initialize. Defaults to True.
        """
        if initialize:
            self.seed = seed if seed is not None else random.randrange(sys.maxsize)
            random.seed(self.seed)

            self.id = str(uuid.uuid4())
            self.vps_to_win = vps_to_win
            self.state = State(players, catan_map, discard_limit=discard_limit)
            self.playable_actions = generate_playable_actions(self.state)

    def play(self, accumulators=[], decide_fn=None):
        """Executes game until a player wins or exceeded TURNS_LIMIT.

        Args:
            accumulators (list[Accumulator], optional): list of Accumulator classes to use.
                Their .consume method will be called with every action, and
                their .finalize method will be called when the game ends (if it ends)
                Defaults to [].
            decide_fn (function, optional): Function to overwrite current player's decision with.
                Defaults to None.
        Returns:
            Color: winning color or None if game exceeded TURNS_LIMIT
        """
        for accumulator in accumulators:
            accumulator.before(self)
        while self.winning_color() is None and self.state.num_turns < TURNS_LIMIT:
            self.play_tick(decide_fn=decide_fn, accumulators=accumulators)
        for accumulator in accumulators:
            accumulator.after(self)
        return self.winning_color()

    def play_tick(self, decide_fn=None, accumulators=[]):
        """Advances game by one ply (player decision).

        Args:
            decide_fn (function, optional): Function to overwrite current player's decision with.
                Defaults to None.

        Returns:
            ActionRecord: representing the executed action
        """
        # Ask Player for action
        player = self.state.current_player()
        action = (
            decide_fn(player, self, self.playable_actions)
            if decide_fn is not None
            else player.decide(self, self.playable_actions)
        )

        # Call accumulator.step here, because we want game_before_action, action
        if len(accumulators) > 0:
            for accumulator in accumulators:
                accumulator.step(self, action)

        # Apply Action, and do Move Generation
        return self.execute(action)

    def execute(
        self,
        action: Action,
        validate_action: bool = True,
        action_record: ActionRecord = None,
    ) -> ActionRecord:
        """Internal call that carries out decided action by player"""
        if validate_action and not is_valid_action(
            self.playable_actions, self.state, action
        ):
            raise ValueError(
                f"{action} not playable right now. playable_actions={self.playable_actions}"
            )

        action_record = apply_action(self.state, action, action_record)
        self.playable_actions = generate_playable_actions(self.state)
        return action_record

    def winning_color(self) -> Union[Color, None]:
        """Gets winning color

        Returns:
            Union[Color, None]: Might be None if game truncated by TURNS_LIMIT
        """
        result = None
        for color in self.state.colors:
            key = player_key(self.state, color)
            if (
                self.state.player_state[f"{key}_ACTUAL_VICTORY_POINTS"]
                >= self.vps_to_win
            ):
                result = color

        return result

    def copy(self) -> "Game":
        """Creates a copy of this Game, that can be modified without
        repercusions on this one (useful for simulations).

        Returns:
            Game: Game copy.
        """
        game_copy = Game(players=[], initialize=False)
        game_copy.seed = self.seed
        game_copy.id = self.id
        game_copy.vps_to_win = self.vps_to_win
        game_copy.state = self.state.copy()
        game_copy.playable_actions = self.playable_actions
        return game_copy
