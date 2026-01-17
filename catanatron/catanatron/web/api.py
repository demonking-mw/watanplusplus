import json
import logging
import traceback

from flask import Response, Blueprint, jsonify, abort, request

from catanatron.web.models import upsert_game_state, get_game_state
from catanatron.json import GameEncoder, action_from_json
from catanatron.models.player import Color, RandomPlayer, Player
from catanatron.models.enums import ActionType
from catanatron.game import Game
from catanatron.players.value import ValueFunctionPlayer
from catanatron.players.minimax import AlphaBetaPlayer
from catanatron.web.mcts_analysis import GameAnalyzer

bp = Blueprint("api", __name__, url_prefix="/api")


class WebHumanPlayer(Player):
    """Human player for web interface. 
    
    This player has is_bot=False, so the backend will wait for HTTP requests
    instead of calling decide(). The decide() method should never be called
    in web mode, but we implement it as a safety fallback.
    """
    
    def __init__(self, color):
        super().__init__(color, is_bot=False)
    
    def decide(self, game, playable_actions):
        # This should never be called in web mode since is_bot=False
        # The backend waits for HTTP requests instead
        # But if it is called somehow, return first action as fallback
        if len(playable_actions) == 0:
            raise ValueError("No playable actions available")
        return playable_actions[0]


def player_factory(player_key):
    if player_key[0] == "CATANATRON":
        return AlphaBetaPlayer(player_key[1], 2, True)
    elif player_key[0] == "RANDOM":
        return RandomPlayer(player_key[1])
    elif player_key[0] == "HUMAN":
        return WebHumanPlayer(player_key[1])
    else:
        raise ValueError("Invalid player key")


@bp.route("/games", methods=("POST",))
def post_game_endpoint():
    if not request.is_json or request.json is None or "players" not in request.json:
        abort(400, description="Missing or invalid JSON body: 'players' key required")
    player_keys = request.json["players"]
    players = list(map(player_factory, zip(player_keys, Color)))

    game = Game(players=players)
    upsert_game_state(game)
    return jsonify({"game_id": game.id})


@bp.route("/games/<string:game_id>/states/<string:state_index>", methods=("GET",))
def get_game_endpoint(game_id, state_index):
    parsed_state_index = _parse_state_index(state_index)
    game = get_game_state(game_id, parsed_state_index)
    if game is None:
        abort(404, description="Resource not found")

    payload = json.dumps(game, cls=GameEncoder)
    return Response(
        response=payload,
        status=200,
        mimetype="application/json",
    )


@bp.route("/games/<string:game_id>/actions", methods=["POST"])
def post_action_endpoint(game_id):
    game = get_game_state(game_id)
    if game is None:
        abort(404, description="Resource not found")

    if game.winning_color() is not None:
        return Response(
            response=json.dumps(game, cls=GameEncoder),
            status=200,
            mimetype="application/json",
        )

    # TODO: remove `or body_is_empty` when fully implement actions in FE
    body_is_empty = (not request.data) or request.json is None or request.json == {}
    if game.state.current_player().is_bot or body_is_empty:
        game.play_tick()
        upsert_game_state(game)
    else:
        try:
            logging.info(f"Received request.json: {request.json}")
            action = action_from_json(request.json)
            # Debug logging for actions
            if action.action_type == ActionType.ROLL:
                logging.info(f"Received ROLL action with value: {action.value}, type: {type(action.value)}")
            elif action.action_type == ActionType.CONFIRM_TRADE:
                logging.info(f"Received CONFIRM_TRADE action: color={action.color}, value={action.value}, value_type={type(action.value)}, value_len={len(action.value) if action.value else 0}")
            elif action.action_type == ActionType.MARITIME_TRADE:
                logging.info(f"Received MARITIME_TRADE action: color={action.color}, value={action.value}, value_type={type(action.value)}, value_len={len(action.value) if action.value else 0}")
            elif action.action_type == ActionType.DISCARD:
                logging.info(f"Received DISCARD action: color={action.color}, value={action.value}, value_type={type(action.value)}, value_len={len(action.value) if action.value else 0}, current_color={game.state.current_color()}, current_prompt={game.state.current_prompt}")
            game.execute(action)
            upsert_game_state(game)
        except Exception as e:
            logging.error(f"Error processing action: {str(e)}", exc_info=True)
            abort(500, description=f"Error processing action: {str(e)}")

    return Response(
        response=json.dumps(game, cls=GameEncoder),
        status=200,
        mimetype="application/json",
    )


@bp.route("/stress-test", methods=["GET"])
def stress_test_endpoint():
    players = [
        AlphaBetaPlayer(Color.RED, 2, True),
        AlphaBetaPlayer(Color.BLUE, 2, True),
        AlphaBetaPlayer(Color.ORANGE, 2, True),
        AlphaBetaPlayer(Color.WHITE, 2, True),
    ]
    game = Game(players=players)
    game.play_tick()
    return Response(
        response=json.dumps(game, cls=GameEncoder),
        status=200,
        mimetype="application/json",
    )


@bp.route("/games/<string:game_id>/resources/batch", methods=["POST"])
def update_resources_batch_endpoint(game_id):
    """Update multiple player resource counts at once (for editor/testing purposes)"""
    # Always get the latest state to ensure we're working with the most recent version
    game = get_game_state(game_id)
    if game is None:
        abort(404, description="Resource not found")
    
    if not request.is_json or request.json is None:
        abort(400, description="Missing or invalid JSON body")
    
    try:
        changes = request.json.get("changes")
        if not isinstance(changes, list):
            abort(400, description="Missing or invalid 'changes' array")
        
        from catanatron.models.enums import RESOURCES
        from catanatron.state_functions import player_key
        
        # Process all changes
        for change in changes:
            color_str = change.get("color")
            resource_str = change.get("resource")
            amount = change.get("amount")
            
            if color_str is None or resource_str is None or amount is None:
                continue  # Skip invalid entries
            
            if not isinstance(amount, int) or amount < 0:
                continue  # Skip invalid amounts
            
            try:
                color = Color[color_str]
            except KeyError:
                continue  # Skip invalid colors
            
            if resource_str not in RESOURCES:
                continue  # Skip invalid resources
            
            # Update the resource count directly
            key = player_key(game.state, color)
            resource_key = f"{key}_{resource_str}_IN_HAND"
            
            # Calculate the difference to update the bank
            old_amount = game.state.player_state.get(resource_key, 0)
            difference = amount - old_amount
            
            # Update player's hand
            game.state.player_state[resource_key] = amount
            
            # Update the bank (add resources back to bank if decreasing, remove if increasing)
            resource_index = RESOURCES.index(resource_str)
            if difference < 0:
                # Player lost resources, add to bank
                game.state.resource_freqdeck[resource_index] += abs(difference)
            elif difference > 0:
                # Player gained resources, remove from bank (if available)
                game.state.resource_freqdeck[resource_index] = max(
                    0, game.state.resource_freqdeck[resource_index] - difference
                )
        
        # Regenerate playable actions after resource changes
        # This ensures the Buy button and other actions reflect the updated resource counts
        from catanatron.models.actions import generate_playable_actions
        game.playable_actions = generate_playable_actions(game.state)
        
        # Save the updated state - upsert_game_state will replace any existing state with the same state_index
        # This ensures manual resource edits persist even when other players take actions
        upsert_game_state(game)
        
        payload = json.dumps(game, cls=GameEncoder)
        return Response(
            response=payload,
            status=200,
            mimetype="application/json",
        )
    except Exception as e:
        logging.error(f"Error updating resources batch: {str(e)}", exc_info=True)
        abort(500, description=f"Error updating resources: {str(e)}")


@bp.route("/games/<string:game_id>/resources", methods=["POST"])
def update_resources_endpoint(game_id):
    """Update a player's resource count (for editor/testing purposes)"""
    game = get_game_state(game_id)
    if game is None:
        abort(404, description="Resource not found")
    
    if not request.is_json or request.json is None:
        abort(400, description="Missing or invalid JSON body")
    
    try:
        color_str = request.json.get("color")
        resource_str = request.json.get("resource")
        amount = request.json.get("amount")
        
        if color_str is None or resource_str is None or amount is None:
            abort(400, description="Missing required fields: color, resource, amount")
        
        if not isinstance(amount, int) or amount < 0:
            abort(400, description="Amount must be a non-negative integer")
        
        color = Color[color_str]
        from catanatron.models.enums import RESOURCES
        # RESOURCES is a list of strings, not enums
        if resource_str not in RESOURCES:
            abort(400, description=f"Invalid resource: {resource_str}")
        
        # Update the resource count directly
        from catanatron.state_functions import player_key
        key = player_key(game.state, color)
        resource_key = f"{key}_{resource_str}_IN_HAND"
        
        # Calculate the difference to update the bank
        old_amount = game.state.player_state.get(resource_key, 0)
        difference = amount - old_amount
        
        # Update player's hand
        game.state.player_state[resource_key] = amount
        
        # Update the bank (add resources back to bank if decreasing, remove if increasing)
        resource_index = RESOURCES.index(resource_str)
        if difference < 0:
            # Player lost resources, add to bank
            game.state.resource_freqdeck[resource_index] += abs(difference)
        elif difference > 0:
            # Player gained resources, remove from bank (if available)
            game.state.resource_freqdeck[resource_index] = max(
                0, game.state.resource_freqdeck[resource_index] - difference
            )
        
        upsert_game_state(game)
        
        payload = json.dumps(game, cls=GameEncoder)
        return Response(
            response=payload,
            status=200,
            mimetype="application/json",
        )
    except KeyError as e:
        abort(400, description=f"Invalid color or resource: {str(e)}")
    except Exception as e:
        logging.error(f"Error updating resources: {str(e)}", exc_info=True)
        abort(500, description=f"Error updating resources: {str(e)}")


@bp.route(
    "/games/<string:game_id>/states/<string:state_index>/mcts-analysis", methods=["GET"]
)
def mcts_analysis_endpoint(game_id, state_index):
    """Get MCTS analysis for specific game state."""
    logging.info(f"MCTS analysis request for game {game_id} at state {state_index}")

    # Convert 'latest' to None for consistency with get_game_state
    parsed_state_index = _parse_state_index(state_index)
    try:
        game = get_game_state(game_id, parsed_state_index)
        if game is None:
            logging.error(
                f"Game/state not found: {game_id}/{state_index}"
            )  # Use original state_index for logging
            abort(404, description="Game state not found")

        analyzer = GameAnalyzer(num_simulations=100)
        probabilities = analyzer.analyze_win_probabilities(game)

        logging.info(f"Analysis successful. Probabilities: {probabilities}")
        return Response(
            response=json.dumps(
                {
                    "success": True,
                    "probabilities": probabilities,
                    "state_index": (
                        parsed_state_index
                        if parsed_state_index is not None
                        else len(game.state.action_records)
                    ),
                }
            ),
            status=200,
            mimetype="application/json",
        )

    except Exception as e:
        logging.error(f"Error in MCTS analysis endpoint: {str(e)}")
        logging.error(traceback.format_exc())
        return Response(
            response=json.dumps(
                {"success": False, "error": str(e), "trace": traceback.format_exc()}
            ),
            status=500,
            mimetype="application/json",
        )


def _parse_state_index(state_index_str: str):
    """Helper function to parse and validate state_index."""
    if state_index_str == "latest":
        return None
    try:
        return int(state_index_str)
    except ValueError:
        abort(
            400,
            description="Invalid state_index format. state_index must be an integer or 'latest'.",
        )


# ===== Debugging Routes
# @app.route(
#     "/games/<string:game_id>/players/<int:player_index>/features", methods=["GET"]
# )
# def get_game_feature_vector(game_id, player_index):
#     game = get_game_state(game_id)
#     if game is None:
#         abort(404, description="Resource not found")

#     return create_sample(game, game.state.colors[player_index])


# @app.route("/games/<string:game_id>/value-function", methods=["GET"])
# def get_game_value_function(game_id):
#     game = get_game_state(game_id)
#     if game is None:
#         abort(404, description="Resource not found")

#     # model = tf.keras.models.load_model("data/models/mcts-rep-a")
#     model2 = tf.keras.models.load_model("data/models/mcts-rep-b")
#     feature_ordering = get_feature_ordering()
#     indices = [feature_ordering.index(f) for f in NUMERIC_FEATURES]
#     data = {}
#     for color in game.state.colors:
#         sample = create_sample_vector(game, color)
#         # scores = model.call(tf.convert_to_tensor([sample]))

#         inputs1 = [create_board_tensor(game, color)]
#         inputs2 = [[float(sample[i]) for i in indices]]
#         scores2 = model2.call(
#             [tf.convert_to_tensor(inputs1), tf.convert_to_tensor(inputs2)]
#         )
#         data[color.value] = float(scores2.numpy()[0][0])

#     return data
