# Catan Web

Isolated 4-player Catan web app for the watanplusplus project. The server is
authoritative: it holds the single source of truth for the game, validates
every action, and broadcasts state. Clients only render and send intents.

Game records are written to `catan_web/data/` as HDCS JSONL so the existing
project tools can read them directly.

## Run (Windows PowerShell, from the repo root with .venv active)

    pip install -r catan_web/requirements.txt
    uvicorn catan_web.server:app --host 0.0.0.0 --port 8000 --reload

Open http://localhost:8000 and use the echo box to confirm connectivity.

## Connect from another computer on the same network

Find the host machine LAN IP (ipconfig), then on the other machine open:

    http://HOST_LAN_IP:8000

## Tests

    pytest catan_web/tests

## Status

This is the scaffold phase. The server serves the thin client and a WebSocket
echo endpoint. Board graph, rules, networking protocol, and HDCS export are
implemented in later phases. The engine, net, and export modules are stubs
with documented signatures.
