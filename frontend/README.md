# Bluff Royale frontend

Designed for the authenticated Bluff Royale API.

## Run

1. Set `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID` in `.env` (see `.env.example`).
2. Run `npm ci`.
3. Run `npm run dev`.

In production, Vercel rewrites the app's same-origin `/api` auth and game routes directly to the HTTPS Render API. This avoids cross-origin browser cookies while keeping the session cookie HttpOnly and scoped to the deployed frontend origin. Set `VITE_GOOGLE_CLIENT_ID` to the Google OAuth web client ID; its authorized JavaScript origin must include the deployed Vercel origin. On Render, set the exact deployed frontend origin in `FRONTEND_URL` and use the same client ID for `GOOGLE_CLIENT_ID`.

For local development, Vite proxies `/api` to `VITE_API_URL` (default `http://localhost:8000`). The app-session cookie is HttpOnly, Secure in production, and SameSite=Lax.

Includes the responsive table, synthesized menu/game audio, rules, options, authenticated match history, turn timer, pause/resume with in-game options and quit-to-menu, animated multiplayer emotes, Indian-English curated and custom table talk (up to 120 characters), shared move/challenge announcements, profile-photo avatars, and two-player **Close Round** action. Room hosts can choose one, two, or three decks when creating a room; one deck is the default. Reactions are broadcast to joined players through short-lived room-store events. Game action requests never send a player ID; the API binds each request to the authenticated seat.
