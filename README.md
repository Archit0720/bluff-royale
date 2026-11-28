# ♠ BLUFF ROYALE

### *The table remembers every lie.*

**Bluff Royale** is a full-stack, multiplayer card game built around deception, memory, probability, and calculated risk.

Inspired by the Bluff / Cheat card-game variant commonly played in India, Bluff Royale turns the traditional game into an online multiplayer experience with private rooms, persistent game state, timed turns, bluff challenges, finishing positions, match history, and a casino-inspired interface.

> You don't need the best cards.  
> You need the best story.

---

## 🎮 Play Bluff Royale

**Live Game:** [Bluff Royale](https://bluff-royale-eight.vercel.app)

> The backend currently runs on free-tier infrastructure. If the server has been inactive, the first request may take a little longer while the service wakes up.

---

# ♦ What Makes Bluff Royale Different?

This isn't ordinary turn-based Bluff.

A round does **not** finish after every player gets one turn.

Once a rank is declared, the same round can cycle through the table repeatedly:

```text
Player A → Player B → Player C → Player A → Player B → ...

                    ↓

        until somebody calls BLUFF

                    OR

        all other players consecutively SKIP
```

Suppose the active claim is:

```text
QUEENS
```

The table might develop like this:

```text
A → claims 2 Queens
B → claims 1 Queen
C → skips
D → claims 2 Queens
A → claims 3 Queens

Pile = 8 cards
```

There are only four Queens in the deck.

Everyone knows somebody lied.

The problem is...

**Who?**

If B now calls Bluff on A, only A's latest contribution is revealed.

If A lied:

```text
A takes the entire 8-card pile.
```

If A told the truth:

```text
B takes the entire 8-card pile.
```

Earlier lies remain hidden.

That makes memory, card counting, probability, and player behaviour part of the game.

---

# ♣ Core Rules

## Starting the Game

Cards are shuffled and distributed among all players.

The player holding:

**A♠ — Ace of Spades**

opens the first round.

The opening player chooses any rank:

```text
A  2  3  4  5  6  7  8  9  10  J  Q  K
```

and places one or more cards face-down.

The cards don't actually have to match the declared rank.

That's the point.

---

## During a Round

Once a rank has been declared, it remains fixed until that round ends.

Every active player has three possible actions:

### PLAY

Add one or more face-down cards while claiming the current rank.

### CALL BLUFF

Challenge the **latest player who actually placed cards**.

Only that player's latest contribution is revealed.

### SKIP

Pass without adding cards or making a challenge.

Skipped players can participate again when the turn comes back around.

---

## 🔥 Bluff Resolution

Imagine the centre pile contains:

```text
11 cards
```

The latest player claims:

```text
3 Kings
```

You call:

# BLUFF!

Only those latest three cards are revealed.

### The player lied

The challenged player receives:

```text
ALL 11 CARDS
```

The successful challenger opens the next round.

### The player told the truth

The challenger receives:

```text
ALL 11 CARDS
```

The truthful player opens the next round.

The rest of the pile is never revealed.

Remembering previous claims is your responsibility.

---

## Skipping

Skips are tracked from the **most recent play**.

Example:

```text
A → PLAY

B → SKIP
C → SKIP
D → PLAY
```

Because D played, the previous skips are reset.

Now:

```text
A → SKIP
B → SKIP
C → SKIP
```

If D remains the latest contributor and every other active player consecutively skips:

```text
The pile is discarded.

D opens a new round.
```

D can choose a completely new rank.

---

# 🏆 Finishing Positions

Getting rid of your cards doesn't immediately terminate the game.

Instead, players receive finishing positions.

```text
1st
2nd
3rd
...
Last
```

Players who finish are removed from the active turn rotation while the remaining players continue.

A player's final contribution is still challengeable.

If the final play was a bluff and gets caught:

```text
Player receives the entire pile
        ↓
Player returns to the game
```

Otherwise the finishing position becomes permanent.

When only one player remains, that player receives the final position.

---

# ⏱ 40-Second Turn Clock

Every player receives **40 seconds** to act.

During an active round:

```text
40 → 39 → 38 → ... → 1 → 0
```

A timeout becomes an automatic skip.

However, a new-round starter must choose:

- which cards to play;
- which rank to claim.

The server never makes that decision for the player.

If the opening player times out:

```text
GAME PAUSED
```

The table can then be resumed.

---

# 🎰 Casino-Style Experience

Bluff Royale was built to feel like a game rather than a CRUD application.

The frontend includes:

- Animated loading screen
- Casino-inspired table
- Players visually seated around the table
- Active-player glow
- Animated cards
- Selectable hands
- Central card pile
- Current-claim display
- Turn timer
- Bluff reveal modal
- Pause / Resume
- Rank selection
- Finishing-position indicators
- Final standings
- Match-history interface
- Responsive multiplayer layout
- Motion preferences
- Sound preferences

---

# 🧠 Server-Authoritative Architecture

The browser does **not** decide whether somebody bluffed.

It doesn't decide:

```text
Whose turn is it?
Who owns which cards?
Was the claim truthful?
Who receives the pile?
Who finished?
Who starts the next round?
```

The backend does.

```text
┌──────────────────────────┐
│      React Clients       │
│                          │
│ Player A  B  C  D        │
└────────────┬─────────────┘
             │
             │ HTTPS / REST
             ▼
┌──────────────────────────┐
│         FastAPI          │
│                          │
│  Authoritative Game      │
│        Engine            │
└────────────┬─────────────┘
             │
       ┌─────┴─────┐
       │           │
       ▼           ▼
┌──────────┐  ┌──────────────┐
│ Memory   │  │  PostgreSQL  │
│          │  │              │
│ Live     │  │ Match        │
│ Games    │  │ History      │
└──────────┘  └──────────────┘
```

This prevents clients from simply telling the server:

```text
"I won."
```

or:

```text
"Those cards were Queens."
```

The engine independently determines the result.

---

# 🏗 Technology Stack

## Frontend

| Technology | Purpose |
|---|---|
| React | Component-based game interface |
| TypeScript | Type-safe frontend logic |
| Vite | Development server and production builds |
| CSS | Casino table, animations and responsive UI |
| Vercel | Frontend deployment |

## Backend

| Technology | Purpose |
|---|---|
| Python | Game engine |
| FastAPI | REST API |
| Pydantic | Request validation |
| Uvicorn | ASGI server |
| Render | Backend deployment |

## Data

| Technology | Purpose |
|---|---|
| In-memory store | Active multiplayer game state (single backend instance) |
| PostgreSQL | Permanent match history |
| Neon | Production PostgreSQL hosting |
| SQLAlchemy | Database abstraction / ORM |
| SQLite | Lightweight local-development history |

## Development & Infrastructure

| Technology | Purpose |
|---|---|
| Git | Version control |
| GitHub | Source hosting |
| pytest | Backend testing |

---

# 📁 Project Structure

```text
bluff-royale/
│
├── backend/
│   │
│   ├── src/
│   │   └── bluff_game/
│   │       │
│   │       ├── api/
│   │       │   ├── main.py
│   │       │   ├── manager.py
│   │       │   ├── routes.py
│   │       │   └── schemas.py
│   │       │
│   │       ├── storage/
│   │       │   └── room_store.py
│   │       │
│   │       ├── card.py
│   │       ├── deck.py
│   │       ├── player.py
│   │       ├── game.py
│   │       ├── config.py
│   │       └── history.py
│   │
│   ├── tests/
│   ├── docker-compose.yml
│   └── pyproject.toml
│
├── frontend/
│   │
│   ├── src/
│   │   ├── api.ts
│   │   ├── main.tsx
│   │   └── style.css
│   │
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
└── README.md
```

---

# 🚀 Running Locally

## Prerequisites

Install:

- Python 3.11+
- Node.js
- npm

---

Room state is stored in backend memory. No Redis server, Upstash account, Docker, or Redis-related environment variable is needed.

---

## Start the Backend

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

### Windows PowerShell

```text
.\.venv\Scripts\Activate.ps1
```

Install:

```bash
python -m pip install -e ".[dev]"
```

Configure the development environment:

```text
DATABASE_URL=sqlite:///./bluff_history.db

TURN_SECONDS=40
ROOM_TTL_SECONDS=86400

FRONTEND_URL=http://localhost:5173
ANALYTICS_ADMIN_EMAIL=architdogra07@gmail.com
FEEDBACK_TO_EMAIL=architdogra95@gmail.com
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
```

Start FastAPI:

```bash
uvicorn bluff_game.api.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## 3. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🌐 Production Architecture

Bluff Royale is designed to run entirely on free-tier-friendly infrastructure.

```text
                  Players
                     │
                     ▼
              Vercel CDN
                     │
               React + Vite
                     │
                     ▼
              Render Web API
                     │
                  FastAPI
                     │
            ┌────────┴────────┐
            ▼                 ▼
      Instance Memory    Neon Postgres
            │                 │
       Active Rooms       Match History
```

### Production Services

| Layer | Provider |
|---|---|
| Frontend | Vercel |
| Backend | Render |
| Live Game State | Render instance memory |
| Match History | Neon PostgreSQL |
| Source | GitHub |

---

# 🔐 Security & Game Integrity

Several design decisions intentionally keep authority away from the client.

### Hidden hands

A player receives:

```text
their own cards
```

but only receives this for opponents:

```text
name
card count
position
turn state
```

Opponent hands never need to be sent to the browser.

### Bluff verification

Real cards remain server-side.

The frontend requests:

```text
CALL BLUFF
```

The backend determines whether that challenge succeeds.

### Credentials

Production credentials are supplied through environment variables:

```text
DATABASE_URL
FRONTEND_URL
VITE_API_URL
ANALYTICS_ADMIN_EMAIL
FEEDBACK_TO_EMAIL
SMTP_HOST
SMTP_PORT
SMTP_USERNAME
SMTP_PASSWORD
```

Secrets are not intended to be committed to source control.
Configure SMTP values only in Render's environment. Gmail delivery requires an App Password; until SMTP is configured, feedback submissions return a clear unavailable message. The analytics dashboard is restricted to `ANALYTICS_ADMIN_EMAIL` and stores aggregate page-view counts only, without visitor emails or IP addresses.

---

# 💾 Live Room State vs Match History

Bluff Royale separates temporary live rooms from persistent match history.

## Live room state

In-memory storage is the default and keeps temporary multiplayer state in the running backend process:

```text
Room
Players
Hands
Current turn
Current rank
Pile
Recent claims
Skipped players
Timer state
Pause state
Finishing order
```

This requires a single backend instance; rooms are lost when that process restarts. The backend no longer connects to Redis, so Upstash request quotas do not apply.

## PostgreSQL

Used for persistent records:

```text
Completed matches
Players
Final standings
Start time
Finish time
Room identifier
```

In other words:

```text
Memory = what is happening now.

PostgreSQL = what happened before.
```

---

# 🔄 Example Multiplayer Flow

```text
Player A
   │
   │ Create Table
   ▼
FastAPI
   │
   ├── Generate room code
   └── Store room in memory


Player B
   │
   │ Join ABCDE
   ▼
FastAPI
   │
   └── Add player to room


Players Start
   │
   ▼
Shuffle 52-card deck
   │
   ▼
Deal cards
   │
   ▼
Locate A♠
   │
   ▼
A♠ owner opens


Player makes claim
   │
   ▼
Memory updated
   │
   ▼
Other clients receive new state


Someone calls BLUFF
   │
   ▼
Last contribution revealed
   │
   ▼
Backend verifies cards
   │
   ├── Liar → receives entire pile
   │
   └── Truthful → challenger receives entire pile
```

---

# 🧪 Testing

Backend tests cover core behaviour including:

- Card distribution
- Turn ownership
- Fixed-rank rounds
- Multiple rotations
- Playing after skips
- Skip reset
- Challenge targeting
- Whole-pile penalties
- Truthful challenges
- Failed challenges
- Final-card challenges
- Finishing positions
- Finished-player turn removal
- Last-place resolution
- In-memory room storage

Run:

```bash
pytest -q
```

---

# 🗺 Roadmap

The current version focuses on a complete multiplayer foundation.

Potential future additions:

- WebSockets instead of REST polling
- Public matchmaking
- Friends / invite system
- Player accounts
- Global leaderboards
- Bluff statistics
- Win/loss analytics
- Spectator mode
- Reconnect handling
- Game replays
- Different table themes
- AI opponents with bluff inference
- Ranked matchmaking
- Tournament mode
- Mobile/PWA experience

---

# 🤖 Future AI Mode

A Bluff AI should not simply choose random cards.

An intelligent player could estimate:

```text
P(bluff | cards in hand,
          claimed cards,
          known cards,
          pile history,
          previous claims,
          opponent behaviour)
```

For example:

```text
Bot holds 3 Queens.

Opponent claims 2 Queens.
```

At least one part of that claim is impossible.

An advanced bot could track:

- Impossible card combinations
- Historical bluff rate
- Challenge success rate
- Claim patterns
- Risk/reward of taking the pile
- Cards remaining
- Player behaviour

This creates an interesting future reinforcement-learning / probabilistic-agent extension.

---

# 💡 Engineering Lessons

Bluff Royale started as a card-game engine.

Building the multiplayer version required solving much broader engineering problems:

- Server-authoritative state
- Hidden information
- State machines
- Concurrent multiplayer sessions
- Temporary vs persistent storage
- Turn expiration
- Player lifecycle
- Failure-safe game actions
- Cross-origin deployments
- Client/server synchronization
- Cloud database configuration
- Production environment management

The biggest architectural lesson:

> **The UI displays the game. The server decides the game.**

---

# ⚠️ Free-Tier Hosting

Bluff Royale intentionally uses free-tier-friendly infrastructure.

Because the backend runs on free infrastructure, the API may occasionally require some time to wake after a period of inactivity.

That trade-off is intentional:

```text
$0 infrastructure
+
real public deployment
+
in-memory multiplayer
+
real PostgreSQL
+
multiplayer access
```

without requiring paid cloud resources for a portfolio project.

---

# ♠ Philosophy

Bluff is not really a game about cards.

It's a game about information.

You know your cards.

You know what other players **claim**.

You know how many cards supposedly exist.

You remember who played what.

But you never know exactly where the lie began.

That's where Bluff Royale lives.

---

<div align="center">

# ♠ BLUFF ROYALE

### TRUST NOBODY. REMEMBER EVERYTHING.

**React · TypeScript · FastAPI · PostgreSQL**

Built by **Archit Dogra**

© 2026 Bluff Royale

</div>
