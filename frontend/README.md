# Bluff Royale frontend

Designed for the authenticated Bluff Royale API.

## Run

1. Set `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID` in `.env` (see `.env.example`).
2. Run `npm ci`.
3. Run `npm run dev`.

For local cookie authentication, use the same hostname for the frontend and API. Production sign-in requires an HTTPS API endpoint and a matching Google OAuth web client ID.

Includes the responsive table, synthesized menu/game audio, rules, options, authenticated match history, turn timer, pause/resume, challenge modal, rank selection, and two-player **Close Round** action. Game action requests never send a player ID; the API binds each request to the authenticated seat.
