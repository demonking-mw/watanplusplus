"""WebSocket message types for the game protocol (implemented in Phase 5)."""

# Client to server
JOIN = "join"
START = "start"
ACTION = "action"

# Server to client
LOBBY = "lobby"
STATE = "state"
LEGAL = "legal_actions"
ERROR = "error"
GAME_OVER = "game_over"
