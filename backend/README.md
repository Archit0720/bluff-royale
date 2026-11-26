# Bluff Royale backend v0.6

Adds Redis room persistence, SQL match history, 40-second server-authoritative turns, pause/resume, timeout auto-skip, and existing finishing-position rules.

## Windows setup
1. `docker compose up -d`
2. `python -m venv .venv`
3. `.\.venv\Scripts\Activate.ps1`
4. `python -m pip install -e ".[dev]"`
5. Copy `.env.example` to `.env` and load variables, or use defaults.
6. `uvicorn bluff_game.api.main:app --reload`

Timer rule: timeout auto-skips during an active round. If a new-round starter times out before playing, or control returns to a latest contributor after the other player skips in a two-player round, the game pauses because the server must never select cards for a player.

In a two-active-player round, when the non-contributor skips after a play, the latest contributor keeps the pile and claim and may add cards under the same claim or use **Close Round**. Closing discards the pile and lets that player open the next round. The contributor cannot challenge their own play. A provisional final play remains challengeable and is never returned to a player with no cards. Three-or-more-player skip cycles still discard the pile and start a new round as before.

History is SQLite locally. For free hosting later, set DATABASE_URL to a hosted PostgreSQL URL without changing code.
