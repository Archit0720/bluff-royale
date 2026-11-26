import time
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request

from .auth_routes import current_identity
from .schemas import ActionRequest, NameRequest, PlayRequest

router = APIRouter(prefix="/games", tags=["games"])


def manager(request):
    return request.app.state.manager


def fail(error):
    if isinstance(error, KeyError):
        status_code = 404
    elif isinstance(error, PermissionError):
        status_code = 403
    else:
        status_code = 409
    return HTTPException(
        status_code=status_code,
        detail=str(error.args[0] if error.args else error),
    )


def state(room, player_id):
    data = room.game.visible_state(player_id)
    data.update(
        {
            "room_code": room.id,
            "paused": room.paused,
            "paused_by": room.paused_by,
            "turn_seconds_left": (
                room.paused_seconds_left
                if room.paused
                else max(0, int((room.turn_deadline or time.time()) - time.time()))
            ),
        }
    )
    return data


def active_game(room):
    if room.game is None:
        raise RuntimeError("The game has not started.")
    return room.game


@router.post("")
async def create(
    body: NameRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        room, player = await manager(request).create(
            body.player_name,
            identity.user_id,
        )
        return {
            "game_id": room.id,
            "player_id": player.id,
            "player_name": player.name,
        }
    except (ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.get("/{gid}")
async def room(
    gid: str,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        return {
            "game_id": game_room.id,
            "status": game_room.status,
            "paused": game_room.paused,
            "player_id": player.id,
            "players": [
                {
                    "id": item.id,
                    "name": item.name,
                    "card_count": item.card_count,
                }
                for item in game_room.players
            ],
        }
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/join")
async def join(
    gid: str,
    body: NameRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        player = await manager(request).join(
            gid,
            body.player_name,
            identity.user_id,
        )
        return {
            "game_id": gid.upper(),
            "player_id": player.id,
            "player_name": player.name,
        }
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/start")
async def start(
    gid: str,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        game_room = await manager(request).start(gid, identity.user_id)
        return {
            "game_id": game_room.id,
            "status": game_room.status,
        }
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.get("/{gid}/state")
async def private_state(
    gid: str,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        active_game(game_room)
        return state(game_room, player.id)
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/play")
async def play(
    gid: str,
    body: PlayRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        if game_room.paused:
            raise RuntimeError("Game is paused.")
        result = active_game(game_room).play(
            player.id,
            body.card_indices,
            body.claimed_rank,
        )
        await service.action_done(game_room)
        return {
            "card_count": len(result.cards),
            "claimed_rank": result.claimed_rank.value,
        }
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/skip")
async def skip(
    gid: str,
    body: ActionRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        if game_room.paused:
            raise RuntimeError("Game is paused.")
        result = active_game(game_room).skip(player.id)
        await service.action_done(game_room)
        return asdict(result)
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/close-round")
async def close_round(
    gid: str,
    body: ActionRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        if game_room.paused:
            raise RuntimeError("Game is paused.")
        result = active_game(game_room).close_round(player.id)
        await service.action_done(game_room)
        return asdict(result)
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/challenge")
async def challenge(
    gid: str,
    body: ActionRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        if game_room.paused:
            raise RuntimeError("Game is paused.")
        result = active_game(game_room).challenge(player.id)
        await service.action_done(game_room)
        data = asdict(result)
        data["revealed_cards"] = [str(card) for card in result.revealed_cards]
        return data
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/pause")
async def pause(
    gid: str,
    body: ActionRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        await service.pause(game_room, player.id, identity.user_id)
        return {"paused": True, "paused_by": player.id}
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error


@router.post("/{gid}/resume")
async def resume(
    gid: str,
    body: ActionRequest,
    request: Request,
    identity=Depends(current_identity),
):
    try:
        service = manager(request)
        game_room = await service.get_for_user(gid, identity.user_id)
        player = service.player_for_user(game_room, identity.user_id)
        await service.resume(game_room, player.id, identity.user_id)
        return {"paused": False}
    except (KeyError, PermissionError, ValueError, RuntimeError) as error:
        raise fail(error) from error
