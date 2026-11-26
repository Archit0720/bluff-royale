import asyncio
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
    profile = client.get("/auth/me")
    assert profile.status_code == 200
    assert profile.json()["display_name"] == "Player"
    assert "email" not in profile.json()
    assert "google_sub" not in profile.json()


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


def test_host_can_create_room_with_one_to_three_decks(
    monkeypatch, tmp_path
):
    client, _ = build_client(tmp_path / "decks.sqlite", monkeypatch)
    guest = TestClient(client.app)
    sign_in(client, "deck-host", "host@example.test")
    sign_in(guest, "deck-guest", "guest@example.test")

    for deck_count in (1, 2, 3):
        body = {"player_name": "Host"}
        if deck_count != 1:
            body["deck_count"] = deck_count
        created = client.post("/games", json=body, headers={"Origin": ORIGIN})
        assert created.status_code == 200
        game_id = created.json()["game_id"]
        room = client.get(f"/games/{game_id}").json()
        assert room["deck_count"] == deck_count

        joined = guest.post(
            f"/games/{game_id}/join",
            json={"player_name": f"Guest {deck_count}"},
            headers={"Origin": ORIGIN},
        )
        assert joined.status_code == 200
        started = client.post(f"/games/{game_id}/start", headers={"Origin": ORIGIN})
        assert started.status_code == 200
        assert len(client.get(f"/games/{game_id}/state").json()["your_hand"]) == (
            52 * deck_count // 2
        )
        assert len(guest.get(f"/games/{game_id}/state").json()["your_hand"]) == (
            52 * deck_count // 2
        )

    for deck_count in (0, 4):
        rejected = client.post(
            "/games",
            json={"player_name": "Host", "deck_count": deck_count},
            headers={"Origin": ORIGIN},
        )
        assert rejected.status_code == 422


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

    with owner.app.state.history.Session.begin() as db:
        owner_account = db.scalar(
            select(User).where(User.google_sub == "subject-owner")
        )
        owner_account.picture = "https://images.example.test/owner.png"

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

    owner_room = owner.get(f"/games/{room['game_id']}")
    assert owner_room.status_code == 200
    assert owner_room.json()["is_host"] is True
    owner_seat = next(
        player for player in owner_room.json()["players"]
        if player["id"] == room["player_id"]
    )
    assert owner_seat["picture"] == "https://images.example.test/owner.png"
    assert owner_seat["presence"] == "online"
    assert guest.get(f"/games/{room['game_id']}").json()["is_host"] is False
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
    original_deadline = stored_room.turn_deadline
    original_hand = owner.get(f"/games/{room['game_id']}/state").json()["your_hand"]
    repeated = owner.post(
        f"/games/{room['game_id']}/start",
        headers={"Origin": ORIGIN},
    )
    assert repeated.status_code == 200
    assert stored_room.turn_deadline == original_deadline
    assert owner.get(f"/games/{room['game_id']}/state").json()["your_hand"] == original_hand
    assert owner.post(
        f"/games/{room['game_id']}/emote",
        json={"emote": "clap"},
        headers={"Origin": ORIGIN},
    ).status_code == 200
    assert guest.post(
        f"/games/{room['game_id']}/emote",
        json={"emote": "wow"},
        headers={"Origin": ORIGIN},
    ).status_code == 200
    outsider_emote = stranger.post(
        f"/games/{room['game_id']}/emote",
        json={"emote": "heart"},
        headers={"Origin": ORIGIN},
    )
    assert outsider_emote.status_code == 403
    emotes = owner.get(f"/games/{room['game_id']}").json()["recent_emotes"]
    assert {event["emote"] for event in emotes} == {"clap", "wow"}
    dialogue = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"dialogue": "arre_bhai"},
        headers={"Origin": ORIGIN},
    )
    assert dialogue.status_code == 200
    assert owner.get(f"/games/{room['game_id']}").json()["recent_emotes"][0][
        "dialogue"
    ] == "arre_bhai"
    custom_text = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"custom_text": "The crown is still up for grabs."},
        headers={"Origin": ORIGIN},
    )
    assert custom_text.status_code == 200
    assert owner.get(f"/games/{room['game_id']}").json()["recent_emotes"][0][
        "custom_text"
    ] == "The crown is still up for grabs."
    blank_custom_text = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"custom_text": "   "},
        headers={"Origin": ORIGIN},
    )
    assert blank_custom_text.status_code == 422
    oversized_custom_text = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"custom_text": "x" * 121},
        headers={"Origin": ORIGIN},
    )
    assert oversized_custom_text.status_code == 422
    invalid_dialogue = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"dialogue": "a custom message"},
        headers={"Origin": ORIGIN},
    )
    assert invalid_dialogue.status_code == 422
    invalid_both = owner.post(
        f"/games/{room['game_id']}/dialogue",
        json={"dialogue": "arre_bhai", "custom_text": "also this"},
        headers={"Origin": ORIGIN},
    )
    assert invalid_both.status_code == 422

    owner_state = owner.get(f"/games/{room['game_id']}/state").json()
    guest_state = guest.get(f"/games/{room['game_id']}/state").json()
    assert owner_state["your_hand"] != guest_state["your_hand"]
    assert owner_state["players"][0]["id"] == room["player_id"]
    assert guest_state["players"][1]["id"] == joined["player_id"]
    assert owner.get(
        f"/games/{room['game_id']}/players/{joined['player_id']}"
    ).status_code == 404

    paused = owner.post(
        f"/games/{room['game_id']}/pause",
        json={},
        headers={"Origin": ORIGIN},
    )
    assert paused.status_code == 200
    paused_room = guest.get(f"/games/{room['game_id']}").json()
    assert paused_room["paused"] is True
    assert next(
        player for player in paused_room["players"]
        if player["id"] == room["player_id"]
    )["on_hold"] is True
    assert owner.post(
        f"/games/{room['game_id']}/resume",
        json={},
        headers={"Origin": ORIGIN},
    ).status_code == 200

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

    left = owner.post(
        f"/games/{room['game_id']}/leave",
        json={},
        headers={"Origin": ORIGIN},
    )
    assert left.status_code == 200
    guest_room_after_leave = guest.get(f"/games/{room['game_id']}").json()
    owner_seat_after_leave = next(
        player for player in guest_room_after_leave["players"]
        if player["id"] == room["player_id"]
    )
    assert owner_seat_after_leave["presence"] == "left"
    guest_events = guest_room_after_leave["recent_emotes"]
    assert any(
        event["kind"] == "system"
        and event["system_event"] == "leave"
        and event["player_id"] == room["player_id"]
        for event in guest_events
    )

    assert owner.post("/auth/logout", headers={"Origin": ORIGIN}).status_code == 200
    assert owner.get("/auth/me").status_code == 401


def test_concurrent_host_start_deals_once(monkeypatch, tmp_path):
    owner, _ = build_client(tmp_path / "concurrent-start.sqlite", monkeypatch)
    guest = TestClient(owner.app)
    sign_in(owner, "subject-host", "host@example.test")
    sign_in(guest, "subject-guest-start", "guest-start@example.test")
    created = owner.post(
        "/games",
        json={"player_name": "Host"},
        headers={"Origin": ORIGIN},
    ).json()
    guest.post(
        f"/games/{created['game_id']}/join",
        json={"player_name": "Guest"},
        headers={"Origin": ORIGIN},
    )

    with owner.app.state.history.Session() as db:
        host_user = db.scalar(select(User).where(User.google_sub == "subject-host"))
        host_user_id = host_user.id

    async def concurrent_start():
        manager = owner.app.state.manager
        return await asyncio.gather(
            manager.start(created["game_id"], host_user_id),
            manager.start(created["game_id"], host_user_id),
        )

    first, second = asyncio.run(concurrent_start())
    assert first.game is second.game
    assert first.turn_deadline == second.turn_deadline
    assert first.game.status.value == "playing"
