"""Pure game engine for base Catan.

Two functions form the entire interface the server and any future bot need:
legal_actions(state, player) and apply_action(state, action). Everything here
is framework free and deterministic given a seed.
"""
