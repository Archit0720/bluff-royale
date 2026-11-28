# Bluff Royale backend

FastAPI game API with Redis room persistence, SQL match history, Google Identity Services sign-in, and server-authorized player actions.

## Local setup

1. Room state uses in-memory storage by default; Redis is optional.
2. Create and activate a virtual environment:
   `python -m venv .venv` and `.\.venv\Scripts\Activate.ps1`.
3. Install dependencies: `python -m pip install -e ".[dev]"`.
4. Copy `.env.example` to `.env`. Set `GOOGLE_CLIENT_ID` to the OAuth web client ID used by the frontend.
5. Run `uvicorn bluff_game.api.main:app --reload`.

For local cookie authentication, open the frontend and API using the same hostname (`localhost` or `127.0.0.1`). In production, set `APP_ENV=production`, `USE_MEMORY_STORE=true`, `GOOGLE_CLIENT_ID`, the exact Vercel origin in `FRONTEND_URL`, and `DATABASE_URL`; serve the API over HTTPS behind a proxy configured to pass the HTTPS scheme. The frontend's same-origin Vercel `/api` proxy forwards requests to Render, so the app cookie is Secure, HttpOnly, and SameSite=Lax rather than relying on third-party cookies. `DATABASE_URL` can point to Neon/PostgreSQL. Memory mode requires one backend instance and active rooms are lost whenever that instance restarts; set `USE_MEMORY_STORE=false` and configure `REDIS_URL` to use Redis instead.

## Authentication and private data

The browser obtains a short-lived sign-in nonce, initializes the Google Identity Services button with it, and posts the returned credential to FastAPI. The API verifies the Google ID token audience/signature and nonce with `google-auth`, then consumes the nonce once and issues a 30-day revocable HttpOnly session cookie. Google email and subject remain server-side.

Rooms bind each seat to an internal user ID. All room reads and game actions require a valid session and room membership; the server derives the acting seat from that session. Rooms created before authenticated seats were introduced cannot be claimed and expire under the configured room TTL. Match history is available only through `GET /auth/me/matches`, using recorded participation by internal user ID. Existing legacy matches are not attributed by display name.

Signed-in members can send in-game emote reactions, curated table-talk lines, or a custom table-talk message up to 120 characters. Reactions are room-scoped, briefly retained by the configured room store for cross-device polling, and do not alter game state or turn rules. Verified Google profile photos are attached to each seat; account email and Google subject remain private. Room polling updates presence, and an explicit leave or 12 seconds without an authenticated poll displays the seat as left without changing turn or scoring rules. Pause, resume, move, and challenge outcomes are recorded as shared table events for every player's screen.

## Round and timer rules

Room hosts can select one, two, or three standard decks when creating a room; one deck is the default. Multiple decks only increase the number of cards dealt and do not change the game rules.

In a two-active-player round, when the non-contributor skips after a play, the latest contributor keeps the pile and claim and may add cards under the same claim or use **Close Round**. Closing discards the pile and lets that player open the next round. The contributor cannot challenge their own play. A provisional final play remains challengeable and is never returned to a player with no cards. Three-or-more-player skip cycles still discard the pile and start a new round as before.

Turns last 40 seconds. An ordinary active-round timeout skips. If a new-round starter times out before playing, or control returns to a contributor in a two-player round, the game pauses rather than choosing cards for that player.
