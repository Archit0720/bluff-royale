import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_code: Mapped[str] = mapped_column(String(12), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    players_json: Mapped[str] = mapped_column(Text)
    standings_json: Mapped[str] = mapped_column(Text)


class MatchParticipation(Base):
    __tablename__ = "match_participation"

    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)


class History:
    def __init__(self, url):
        from . import auth  # Register authentication tables on the shared metadata.

        args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=args)
        auth.Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(self.engine)

    def save(self, room):
        if room.history_saved:
            return

        with self.Session.begin() as session:
            match = Match(
                room_code=room.id,
                started_at=datetime.fromtimestamp(room.started_at, tz=timezone.utc),
                finished_at=datetime.now(timezone.utc),
                players_json=json.dumps(
                    [{"id": player.id, "name": player.name} for player in room.game.players]
                ),
                standings_json=json.dumps(room.game.finishing_order),
            )
            session.add(match)
            session.flush()
            for user_id in set(getattr(room, "seat_users", {}).values()):
                session.add(
                    MatchParticipation(match_id=match.id, user_id=user_id)
                )
        room.history_saved = True

    def by_user(self, user_id, limit=20):
        with self.Session() as session:
            rows = session.scalars(
                select(Match)
                .join(MatchParticipation, MatchParticipation.match_id == Match.id)
                .where(MatchParticipation.user_id == user_id)
                .order_by(Match.id.desc())
                .limit(limit)
            ).all()
            return [
                {
                    "room_code": row.room_code,
                    "started_at": row.started_at,
                    "finished_at": row.finished_at,
                    "players": json.loads(row.players_json),
                    "standings": json.loads(row.standings_json),
                }
                for row in rows
            ]
