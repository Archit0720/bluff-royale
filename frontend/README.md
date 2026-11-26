# Bluff Royale frontend

Designed for the authenticated Bluff Royale API.

## Run

1. Set `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID` in `.env` (see `.env.example`).
2. Run `npm ci`.
3. Run `npm run dev`.

In production, add the server-only Vercel environment variable `BLUFF_API_ORIGIN` with the HTTPS origin of the Render API (for example `https://your-api.onrender.com`). The browser talks to the same-origin Vercel `/api` proxy, which forwards only the app's auth and game routes, including the HttpOnly session cookie. `vercel.json` rewrites nested auth and game paths to the proxy function. Set `VITE_GOOGLE_CLIENT_ID` to the Google OAuth web client ID; its authorized JavaScript origin must include the deployed Vercel origin. On Render, set the exact deployed frontend origin in `FRONTEND_URL` and use the same client ID for `GOOGLE_CLIENT_ID`.

For local development, Vite proxies `/api` to `VITE_API_URL` (default `http://localhost:8000`). The app-session cookie is HttpOnly, Secure in production, and SameSite=Lax.

Includes the responsive table, synthesized menu/game audio, rules, options, authenticated match history, turn timer, pause/resume with in-game options and quit-to-menu, multiplayer emote reactions, challenge modal, rank selection, and two-player **Close Round** action. Emotes are broadcast to joined players through short-lived room-store events. Game action requests never send a player ID; the API binds each request to the authenticated seat.
