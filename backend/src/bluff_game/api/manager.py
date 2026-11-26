import secrets
import time
from dataclasses import dataclass, field

from ..config import ROOM_TTL_SECONDS, TURN_SECONDS
from ..game import BluffGame, GameStatus
from ..player import Player

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass
class Room:
    id: str
    players: list[Player]
    creator_id: str
    game: BluffGame | None = None
    paused: bool = False
    paused_by: str | None = None
    turn_deadline: float | None = None
    paused_seconds_left: int | None = None
    started_at: float = 0
    history_saved: bool = False
    seat_users: dict[str, str] = field(default_factory=dict)
    seat_profiles: dict[str, dict] = field(default_factory=dict)
    deck_count: int = 1

    @property
    def status(self):
        return self.game.status.value if self.game else GameStatus.WAITING.value


class Manager:
    def __init__(self, store, history):
        self.store = store
        self.history = history

    async def save(self, room):
        await self.store.set(room.id, room, ROOM_TTL_SECONDS)

    async def get(self, gid):
        room = await self.store.get(gid.upper())
        if not room:
            raise KeyError("Game not found.")
        return room

    async def get_for_user(self, gid, user_id):
        room = await self.get(gid)
        player = self.player_for_user(room, user_id)
        await self.apply_timeout(room)
        await self.store.touch_presence(room.id, player.id)
        return room

    def player_for_user(self, room, user_id):
        seat_users = getattr(room, "seat_users", {})
        player_id = next(
            (pid for pid, uid in seat_users.items() if uid == user_id),
            None,
        )
        player = next(
            (item for item in room.players if item.id == player_id),
            None,
        )
        if player is None:
            raise PermissionError("You are not a member of this room.")
        return player

    async def create(self, name, user_id, profile=None, deck_count=1):
        name = name.strip()
        if not name:
            raise ValueError("Player name cannot be empty.")
        if type(deck_count) is not int or not 1 <= deck_count <= 3:
            raise ValueError("The number of decks must be between 1 and 3.")
        room_id = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(5))
        player = Player(secrets.token_urlsafe(12), name)
        room = Room(
            room_id,
            [player],
            user_id,
            deck_count=deck_count,
            seat_users={player.id: user_id},
            seat_profiles={player.id: profile or {}},
        )
        await self.save(room)
        await self.store.touch_presence(room.id, player.id)
        return room, player

    async def join(self, gid, name, user_id, profile=None):
        async with self.store.room_lock(gid.upper()):
            room = await self.get(gid)
            name = name.strip()
            if not name:
                raise ValueError("Player name cannot be empty.")
            if not hasattr(room, "seat_users"):
                raise RuntimeError("This legacy room cannot be joined after sign-in was added.")
            if room.game:
                raise RuntimeError("Game already started.")
            if len(room.players) >= 6:
                raise ValueError("Room is full.")
            if user_id in room.seat_users.values():
                raise ValueError("You already have a seat in this room.")
            if any(player.name.casefold() == name.casefold() for player in room.players):
                raise ValueError("Name already used.")
            player = Player(secrets.token_urlsafe(12), name)
            room.players.append(player)
            room.seat_users[player.id] = user_id
            if not hasattr(room, "seat_profiles"):
                room.seat_profiles = {}
            room.seat_profiles[player.id] = profile or {}
            await self.save(room)
            await self.store.touch_presence(room.id, player.id)
            return player

    async def leave(self, room, player_id, user_id):
        self.player_for_user(room, user_id)
        await self.store.mark_left(room.id, player_id)
        await self.store.publish_emote(
            room.id,
            {
                "player_id": player_id,
                "kind": "system",
                "system_event": "leave",
                "created_at": time.time(),
            },
        )

    async def start(self, gid, user_id):
        async with self.store.room_lock(gid.upper()):
            room = await self.get(gid)
            self.player_for_user(room, user_id)
            if room.creator_id != user_id:
                raise PermissionError("Only the room creator can start the game.")
            if room.game:
                return room
            if len(room.players) < 2:
                raise ValueError("At least 2 players are required.")
            room.game = BluffGame(room.players, getattr(room, "deck_count", 1))
            room.game.start()
            room.started_at = time.time()
            self.reset_timer(room)
            await self.save(room)
            return room

    def reset_timer(self, room):
        room.turn_deadline = time.time() + TURN_SECONDS

    async def action_done(self, room):
        if room.game.status == GameStatus.FINISHED:
            self.history.save(room)
        else:
            self.reset_timer(room)
        await self.save(room)

    async def apply_timeout(self, room):
        if (
            not room.game
            or room.paused
            or room.game.status != GameStatus.PLAYING
            or not room.turn_deadline
            or time.time() < room.turn_deadline
        ):
            return

        player_id = room.game.current_player.id
        if "close_round" in room.game.available_actions(player_id):
            self._pause_after_timeout(room, player_id)
        elif room.game.last_play is not None:
            room.game.skip(player_id)
            room.game._record({"type": "timeout_skip", "player_id": player_id})
            self.reset_timer(room)
        else:
            self._pause_after_timeout(room, player_id)

        if room.game.status == GameStatus.FINISHED:
            self.history.save(room)
        await self.save(room)

    def _pause_after_timeout(self, room, player_id):
        room.paused = True
        room.paused_by = "system"
        room.paused_seconds_left = TURN_SECONDS
        room.turn_deadline = None
        room.game._record({"type": "timeout_pause", "player_id": player_id})

    async def pause(self, room, player_id, user_id):
        self.player_for_user(room, user_id)
        if room.game is None:
            raise RuntimeError("The game has not started.")
        if room.paused:
            raise RuntimeError("Game is already paused.")
        room.paused = True
        room.paused_by = player_id
        room.paused_seconds_left = max(
            1,
            int((room.turn_deadline or time.time()) - time.time()),
        )
        room.turn_deadline = None
        room.game._record({"type": "pause", "player_id": player_id})
        await self.save(room)

    async def resume(self, room, player_id, user_id):
        self.player_for_user(room, user_id)
        if room.game is None:
            raise RuntimeError("The game has not started.")
        if not room.paused:
            raise RuntimeError("Game is not paused.")
        presence = await self.store.room_presence(room.id)
        if (
            room.paused_by not in ("system", player_id)
            and room.creator_id != user_id
            and presence.get(room.paused_by) != "left"
        ):
            raise PermissionError("Only the pausing player or room creator can resume.")
        room.paused = False
        room.paused_by = None
        room.turn_deadline = time.time() + (
            room.paused_seconds_left or TURN_SECONDS
        )
        room.paused_seconds_left = None
        room.game._record({"type": "resume", "player_id": player_id})
        await self.save(room)
