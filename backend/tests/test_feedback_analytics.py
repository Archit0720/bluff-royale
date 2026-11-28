import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bluff_game import auth as auth_module
from bluff_game.api import analytics_routes, feedback_routes
from bluff_game.api.analytics_routes import router as analytics_router
from bluff_game.api.auth_routes import router as auth_router
from bluff_game.api.feedback_routes import router as feedback_router
from bluff_game.auth import AuthService
from bluff_game.history import History

ORIGIN = "http://localhost:5173"


def build_client(path, monkeypatch):
    history = History(f"sqlite:///{path.as_posix()}")
    app = FastAPI()
    app.state.history = history
    app.state.auth = AuthService(history.Session, "google-client-id")
    app.include_router(auth_router)
    app.include_router(analytics_router)
    app.include_router(feedback_router)

    def verify(credential, request, audience):
        assert audience == "google-client-id"
        return json.loads(credential)

    monkeypatch.setattr(auth_module, "verify_oauth2_token", verify)
    return TestClient(app)


def sign_in(client, subject, email):
    nonce = client.get("/auth/nonce").json()["nonce"]
    credential = json.dumps({
        "sub": subject,
        "email": email,
        "email_verified": True,
        "nonce": nonce,
    })
    response = client.post(
        "/auth/google",
        json={"credential": credential, "nonce": nonce},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200


def test_analytics_counts_anonymous_visits_and_restricts_summary(
    monkeypatch, tmp_path
):
    client = build_client(tmp_path / "analytics.sqlite", monkeypatch)
    monkeypatch.setattr(analytics_routes, "ANALYTICS_ADMIN_EMAIL", "owner@example.test")

    for _ in range(2):
        response = client.post("/analytics/visit", headers={"Origin": ORIGIN})
        assert response.status_code == 200

    sign_in(client, "visitor", "visitor@example.test")
    assert client.get("/analytics/summary").status_code == 403

    owner = TestClient(client.app)
    sign_in(owner, "owner", "owner@example.test")
    summary = owner.get("/analytics/summary")
    assert summary.status_code == 200
    assert summary.json() == {
        "total_visits": 2,
        "total_sign_ins": 2,
        "registered_accounts": 2,
    }
    assert "visitor@example.test" not in summary.text


def test_feedback_reports_unconfigured_email_delivery(monkeypatch, tmp_path):
    client = build_client(tmp_path / "feedback.sqlite", monkeypatch)
    monkeypatch.setattr(feedback_routes, "SMTP_HOST", "")

    response = client.post(
        "/feedback",
        json={"message": "I have an idea for the game."},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]
