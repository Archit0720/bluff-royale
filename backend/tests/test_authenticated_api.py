import json
from datetime import datetime, timezone
from types import SimpleNamespace
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from bluff_game import auth as auth_module
from bluff_game.auth import AppSession, AuthService, User
from bluff_game.api import auth_routes
from bluff_game.history import History, Match
from bluff_game.api.auth_routes import router as auth_router
from bluff_game.api.manager import Manager
from bluff_game.api.routes import router as game_router
from bluff_game.player import Player
from bluff_game.storage.room_store import MemoryRoomStore

ORIGIN = "http://localhost:5173"


def build_client(path, monkeypatch):
    history = History(f"sqlite:///{path.as_posix()}")
    app = FastAPI()
    app.state.history = history
    app.state.auth = AuthService(history.Session, "google-client-id")
    app.state.manager = Manager(MemoryRoomStore(), history)
    app.include_router(game_router)
    app.include_router(auth_router)

    def verify(credential, request, audience):
        assert audience == "google-client-id"
        return json.loads(credential)

    monkeypatch.setattr(auth_module, "verify_oauth2_token", verify)
    return TestClient(app), history


def sign_in(client, subject, email):
    nonce = client.get("/auth/nonce").json()["nonce"]
    credential = json.dumps(
        {
            "sub": subject,
            "email": email,
            "email_verified": True,
            "nonce": nonce,
        }
    )
    response = client.post(
        "/auth/google",
        json={"credential": credential, "nonce": nonce},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": True}
    return nonce, credential


def test_google_nonce_is_single_use(monkeypatch, tmp_path):
    client, _ = build_client(tmp_path / "auth.sqlite", monkeypatch)
    nonce, credential = sign_in(client, "subject-a", "a@example.test")
    replay = client.post(
        "/auth/google",
        json={"credential": credential, "nonce": nonce},
        headers={"Origin": ORIGIN},
    )

    assert replay.status_code == 401
    assert "already been used" in replay.json()["detail"]


def test_production_google_credential_requires_https(monkeypatch, tmp_path):
    client, _ = build_client(tmp_path / "https.sqlite", monkeypatch)
    monkeypatch.setattr(auth_routes, "APP_ENV", "production")
    nonce = client.get("/auth/nonce").json()["nonce"]
    credential = json.dumps(
        {
            "sub": "subject-https",
            "email": "https@example.test",
            "email_verified": True,
            "nonce": nonce,
        }
    )
    body = {"credential": credential, "nonce": nonce}
    headers = {"Origin": ORIGIN}

    rejected = client.post("/auth/google", json=body, headers=headers)
    assert rejected.status_code == 400

    https_client = TestClient(client.app, base_url="https://testserver")
    accepted = https_client.post("/auth/google", json=body, headers=headers)
    assert accepted.status_code == 200
    assert "secure" in accepted.headers["set-cookie"].lower()


def test_expired_app_session_is_rejected(monkeypatch, tmp_path):
    client, history = build_client(tmp_path / "expired.sqlite", monkeypatch)
    sign_in(client, "subject-expired", "expired@example.test")
    token = client.cookies.get("bluff_session")
    with history.Session.begin() as session:
        session.execute(
            update(AppSession)
            .where(AppSession.token_hash == auth_module._digest(token))
            .values(expires_at=0)
        )

    assert client.get("/auth/me").status_code == 401


def test_two_accounts_cannot_select_another_seat_or_read_its_hand(
    monkeypatch, tmp_path
):
    owner, history = build_client(tmp_path / "accounts.sqlite", monkeypatch)
    guest = TestClient(owner.app)
    stranger = TestClient(owner.app)
    sign_in(owner, "subject-owner", "owner@example.test")
    sign_in(guest, "subject-guest", "guest@example.test")
    sign_in(stranger, "subject-stranger", "stranger@example.test")

    room = owner.post(
        "/games",
        json={"player_name": "Owner"},
        headers={"Origin": ORIGIN},
    ).json()
    joined = guest.post(
        f"/games/{room['game_id']}/join",
        json={"player_name": "Guest"},
        headers={"Origin": ORIGIN},
    ).json()

    assert owner.get(f"/games/{room['game_id']}").status_code == 200
    stored_room = owner.app.state.manager.store.data[room["game_id"]]
    stored_room.turn_deadline = time.time() - 1
    assert stranger.get(f"/games/{room['game_id']}").status_code == 403
    assert not stored_room.paused
    stored_room.turn_deadline = time.time() + 40
    assert guest.post(
        f"/games/{room['game_id']}/start",
        headers={"Origin": ORIGIN},
    ).status_code == 403
    started = owner.post(
        f"/games/{room['game_id']}/start",
        headers={"Origin": ORIGIN},
    )
    assert started.status_code == 200
    assert "your_hand" not in started.json()

    owner_state = owner.get(f"/games/{room['game_id']}/state").json()
    guest_state = guest.get(f"/games/{room['game_id']}/state").json()
    assert owner_state["your_hand"] != guest_state["your_hand"]
    assert owner_state["players"][0]["id"] == room["player_id"]
    assert guest_state["players"][1]["id"] == joined["player_id"]
    assert owner.get(
        f"/games/{room['game_id']}/players/{joined['player_id']}"
    ).status_code == 404

    other_player_id = (
        guest_state["current_player_id"]
        if owner_state["current_player_id"] == room["player_id"]
        else room["player_id"]
    )
    attacker = guest if owner_state["current_player_id"] == room["player_id"] else owner
    forged = attacker.post(
        f"/games/{room['game_id']}/play",
        json={
            "player_id": other_player_id,
            "card_indices": [0],
            "claimed_rank": "A",
        },
        headers={"Origin": ORIGIN},
    )
    assert forged.status_code == 422
    denied = attacker.post(
        f"/games/{room['game_id']}/play",
        json={"card_indices": [0], "claimed_rank": "A"},
        headers={"Origin": ORIGIN},
    )
    assert denied.status_code == 409

    with history.Session.begin() as session:
        owner_user = session.scalar(select(User).where(User.google_sub == "subject-owner"))
        guest_user = session.scalar(select(User).where(User.google_sub == "subject-guest"))
        assert owner_user is not None
        assert guest_user is not None
        owner_user_id = owner_user.id
        guest_user_id = guest_user.id

    history.save(
        SimpleNamespace(
            id="MATCH",
            started_at=time.time(),
            history_saved=False,
            game=SimpleNamespace(
                players=[
                    Player(room["player_id"], "Owner"),
                    Player(joined["player_id"], "Guest"),
                ],
                finishing_order=[room["player_id"], joined["player_id"]],
            ),
            seat_users={
                room["player_id"]: owner_user_id,
                joined["player_id"]: guest_user_id,
            },
        )
    )

    with history.Session.begin() as session:
        session.add(
            Match(
                room_code="LEGACY",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                players_json=json.dumps(
                    [
                        {"id": room["player_id"], "name": "Owner"},
                        {"id": joined["player_id"], "name": "Guest"},
                    ]
                ),
                standings_json=json.dumps(
                    [room["player_id"], joined["player_id"]]
                ),
            )
        )

    assert len(owner.get("/auth/me/matches").json()) == 1
    assert len(guest.get("/auth/me/matches").json()) == 1
    assert stranger.get("/auth/me/matches").json() == []
    assert "owner@example.test" not in str(owner.get(f"/games/{room['game_id']}").json())
    assert "subject-owner" not in str(owner.get(f"/games/{room['game_id']}").json())

    assert owner.post("/auth/logout", headers={"Origin": ORIGIN}).status_code == 200
    assert owner.get("/auth/me").status_code == 401
