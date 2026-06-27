"""WebSocket message type constants for the game protocol."""

# Client to server
CREATE = "create"
JOIN = "join"
START = "start"
ACTION = "action"

# Server to client
JOINED = "joined"
LOBBY = "lobby"
STATE = "state"
LEGAL = "legal_actions"
ERROR = "error"
GAME_OVER = "game_over"
