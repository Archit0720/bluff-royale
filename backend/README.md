# Bluff Royale backend v0.6

Adds Redis room persistence, SQL match history, 40-second server-authoritative turns, pause/resume, timeout auto-skip, and existing finishing-position rules.

## Windows setup
1. `docker compose up -d`
2. `python -m venv .venv`
3. `.\.venv\Scripts\Activate.ps1`
4. `python -m pip install -e ".[dev]"`
5. Copy `.env.example` to `.env` and load variables, or use defaults.
6. `uvicorn bluff_game.api.main:app --reload`

Timer rule: timeout auto-skips during an active round. If a new-round starter times out before playing, the game pauses because the server must never select a random card/rank.

History is SQLite locally. For free hosting later, set DATABASE_URL to a hosted PostgreSQL URL without changing code.
