"""Phase 4 HDCS export validation against the real project model."""
from catan_web.engine.actions import apply_action
from catan_web.engine.legal import legal_actions
from catan_web.engine.rng import GameRandom
from catan_web.engine.state import Phase, new_game_state
from catan_web.export.hdcs import to_hdcs

NAMES = ["A", "B", "C", "D"]


def _advance(state, rng, steps):
    done = 0
    while state.phase is not Phase.GAME_OVER and done < steps:
        actor, acts = None, []
        for p in range(4):
            a = legal_actions(state, p)
            if a:
                actor, acts = p, a
                break
        if actor is None:
            break
        apply_action(state, actor, acts[0], rng)
        done += 1


def test_export_top_level_shape():
    state = new_game_state(7, NAMES)
    _advance(state, GameRandom(7), 40)
    hdcs = to_hdcs(state)
    assert set(hdcs.keys()) == {"meta", "map", "players"}
    assert len(hdcs["players"]) == 4
    assert len(hdcs["map"]["tiles"]) == 37


def test_export_validates_against_project_model():
    from src.base_computes.game_state import GameState as HDCSGameState

    state = new_game_state(7, NAMES)
    _advance(state, GameRandom(7), 40)
    hdcs = to_hdcs(state)
    model = HDCSGameState.from_json(hdcs)
    assert model is not None
