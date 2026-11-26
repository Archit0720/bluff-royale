import hashlib
import secrets
import time
from dataclasses import dataclass
from uuid import uuid4

from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.id_token import verify_oauth2_token
from sqlalchemy import Float, ForeignKey, String, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker

from .history import Base

NONCE_TTL_SECONDS = 5 * 60
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320))


class LoginNonce(Base):
    __tablename__ = "login_nonces"

    nonce_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class AppSession(Base):
    __tablename__ = "app_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[float] = mapped_column(Float, index=True)
    revoked_at: Mapped[float | None] = mapped_column(Float, nullable=True)


@dataclass(frozen=True)
class Identity:
    user_id: str


class AuthenticationError(ValueError):
    pass


def _digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, sessions: sessionmaker, client_id: str | None):
        self.sessions = sessions
        self.client_id = client_id
        self.session_ttl_seconds = SESSION_TTL_SECONDS

    def create_nonce(self):
        nonce = secrets.token_urlsafe(32)
        with self.sessions.begin() as session:
            now = time.time()
            session.execute(
                delete(LoginNonce).where(LoginNonce.expires_at <= now)
            )
            session.execute(
                delete(AppSession).where(
                    (AppSession.expires_at <= now)
                    | (AppSession.revoked_at.is_not(None))
                )
            )
            session.add(
                LoginNonce(
                    nonce_hash=_digest(nonce),
                    expires_at=now + NONCE_TTL_SECONDS,
                )
            )
        return nonce

    def login(self, credential: str, nonce: str):
        if not self.client_id:
            raise RuntimeError("Google sign-in is not configured.")
        try:
            claims = verify_oauth2_token(
                credential,
                GoogleRequest(),
                audience=self.client_id,
            )
        except TransportError as error:
            raise RuntimeError("Google credential verification is temporarily unavailable.") from error
        except (ValueError, GoogleAuthError) as error:
            raise AuthenticationError("Google credential is invalid or expired.") from error

        subject = claims.get("sub")
        email = claims.get("email")
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(email, str)
            or claims.get("email_verified") is not True
            or claims.get("nonce") != nonce
        ):
            raise AuthenticationError("Google credential claims are incomplete or invalid.")

        now = time.time()
        token = secrets.token_urlsafe(48)
        with self.sessions.begin() as session:
            consumed = session.execute(
                delete(LoginNonce).where(
                    LoginNonce.nonce_hash == _digest(nonce),
                    LoginNonce.expires_at > now,
                )
            )
            if consumed.rowcount != 1:
                raise AuthenticationError("Login nonce is expired or has already been used.")

            user = session.scalar(select(User).where(User.google_sub == subject))
            if user is None:
                try:
                    with session.begin_nested():
                        user = User(id=str(uuid4()), google_sub=subject, email=email)
                        session.add(user)
                        session.flush()
                except IntegrityError:
                    user = session.scalar(
                        select(User).where(User.google_sub == subject)
                    )
                    if user is None:
                        raise

            session.add(
                AppSession(
                    token_hash=_digest(token),
                    user_id=user.id,
                    expires_at=now + SESSION_TTL_SECONDS,
                )
            )
            user_id = user.id

        return token, user_id

    def identity_for_token(self, token: str | None):
        if not token:
            return None
        with self.sessions() as session:
            row = session.scalar(
                select(AppSession.user_id).where(
                    AppSession.token_hash == _digest(token),
                    AppSession.expires_at > time.time(),
                    AppSession.revoked_at.is_(None),
                )
            )
            return Identity(row) if row else None

    def revoke(self, token: str | None):
        if not token:
            return
        with self.sessions.begin() as session:
            session.execute(
                update(AppSession)
                .where(
                    AppSession.token_hash == _digest(token),
                    AppSession.revoked_at.is_(None),
                )
                .values(revoked_at=time.time())
            )
