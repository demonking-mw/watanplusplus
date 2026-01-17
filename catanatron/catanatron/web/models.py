import os
import json
import pickle
from contextlib import contextmanager
from typing import Optional
from catanatron.json import GameEncoder

from catanatron.game import Game
from catanatron.state_functions import get_state_index
from sqlalchemy import MetaData, Column, Integer, String, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from flask_sqlalchemy import SQLAlchemy
from flask import abort

# Using approach from: https://stackoverflow.com/questions/41004540/using-sqlalchemy-models-in-and-out-of-flask/41014157
metadata = MetaData()
Base = declarative_base(metadata=metadata)


class GameState(Base):
    __tablename__ = "game_states"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(64), nullable=False)
    state_index = Column(Integer, nullable=False)
    state = Column(String, nullable=False)
    pickle_data = Column(LargeBinary, nullable=False)

    # TODO: unique uuid and state_index
    @staticmethod
    def from_game(game: Game):
        state = json.dumps(game, cls=GameEncoder)
        pickle_data = pickle.dumps(game, pickle.HIGHEST_PROTOCOL)
        return GameState(
            uuid=game.id,
            state_index=get_state_index(game.state),
            state=state,
            pickle_data=pickle_data,
        )


db = SQLAlchemy(metadata=metadata)


@contextmanager
def database_session():
    """Can use like:
    with database_session() as session:
        game_states = session.query(GameState).all()
    """
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://catanatron:victorypoint@127.0.0.1:5432/catanatron_db",
    )
    engine = create_engine(database_url)
    session = Session(engine)
    try:
        yield session
    finally:
        session.expunge_all()
        session.close()


def upsert_game_state(game: Game, session_param=None):
    """
    Upsert (update or insert) game state.
    If a state with the same uuid and state_index exists, it will be deleted first.
    """
    from catanatron.state_functions import get_state_index
    game_state = GameState.from_game(game)
    session = session_param or db.session
    
    # Delete any existing state with the same uuid and state_index
    # This ensures we don't have duplicate states with the same state_index
    existing = (
        session.query(GameState)
        .filter_by(uuid=game.id, state_index=get_state_index(game.state))
        .first()
    )
    if existing:
        session.delete(existing)
    
    session.add(game_state)
    session.commit()
    return game_state


def get_game_state(game_id, state_index=None) -> Optional[Game]:
    """
    Returns the game from database.
    """
    if state_index is None:
        result = (
            db.session.query(GameState)
            .filter_by(uuid=game_id)
            .order_by(GameState.state_index.desc())
            .first()
        )
        if result is None:
            abort(404)
    else:
        result = (
            db.session.query(GameState)
            .filter_by(uuid=game_id, state_index=state_index)
            .first()
        )
        if result is None:
            abort(404)
    db.session.commit()
    game = pickle.loads(result.pickle_data)  # type: ignore
    return game
