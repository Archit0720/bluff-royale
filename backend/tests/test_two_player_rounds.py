import time

import pytest

from bluff_game.api.manager import Manager, Room
from bluff_game.card import Card, Rank, Suit
from bluff_game.game import BluffGame, GameStatus
from bluff_game.history import History
from bluff_game.player import Player
from bluff_game.storage.room_store import MemoryRoomStore


def make_game(first_hand=None, second_hand=None):
    players = [Player("first", "First"), Player("second", "Second")]
    game = BluffGame(players)
    players[0].hand = first_hand or [
        Card(Rank.ACE, Suit.CLUBS),
        Card(Rank.TWO, Suit.CLUBS),
        Card(Rank.THREE, Suit.CLUBS),
        Card(Rank.FOUR, Suit.CLUBS),
        Card(Rank.FIVE, Suit.CLUBS),
        Card(Rank.SIX, Suit.CLUBS),
        Card(Rank.SEVEN, Suit.CLUBS),
        Card(Rank.EIGHT, Suit.CLUBS),
    ]
    players[1].hand = second_hand or [
        Card(Rank.NINE, Suit.CLUBS),
        Card(Rank.TEN, Suit.CLUBS),
        Card(Rank.JACK, Suit.CLUBS),
        Card(Rank.QUEEN, Suit.CLUBS),
        Card(Rank.KING, Suit.CLUBS),
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.TWO, Suit.HEARTS),
        Card(Rank.THREE, Suit.HEARTS),
    ]
    game.status = GameStatus.PLAYING
    return game


def play_four_and_return_turn():
    game = make_game()
    game.play("first", [0, 1, 2, 3], Rank.ACE)
    game.skip("second")
    assert game.current_player.id == "first"
    return game


def test_two_player_skip_returns_contributor_and_pile_grows_from_four_to_eight():
    game = play_four_and_return_turn()

    assert game.current_rank == Rank.ACE
    assert len(game.pile) == 4
    assert game.last_play.player_id == "first"
    assert game.available_actions("first") == ["play", "close_round"]
    assert "challenge" not in game.available_actions("first")
    with pytest.raises(ValueError, match="own contribution"):
        game.challenge("first")

    game.play("first", [0, 1, 2, 3])

    assert len(game.pile) == 8
    assert game.current_rank == Rank.ACE
    assert game.current_player.id == "second"
    assert len(game.last_play.cards) == 4


def test_close_round_discards_pile_and_starts_new_round_with_contributor():
    game = play_four_and_return_turn()

    result = game.close_round("first")

    assert result.discarded_count == 4
    assert result.next_round_starter_id == "first"
    assert len(game.pile) == 0
    assert len(game.discard_pile) == 4
    assert game.current_rank is None
    assert game.last_play is None
    assert game.current_player.id == "first"
    assert game.available_actions("first") == ["play"]


def test_close_round_is_not_available_before_other_player_skips():
    game = make_game()
    game.play("first", [0], Rank.ACE)

    with pytest.raises(RuntimeError, match="cannot be closed"):
        game.close_round("second")


def test_three_player_skip_cycle_still_discards_and_opens_next_round():
    players = [Player("first", "First"), Player("second", "Second"), Player("third", "Third")]
    game = BluffGame(players)
    for player in players:
        player.hand = [
            Card(Rank.ACE, Suit.CLUBS),
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.THREE, Suit.CLUBS),
            Card(Rank.FOUR, Suit.CLUBS),
            Card(Rank.FIVE, Suit.CLUBS),
        ]
    game.status = GameStatus.PLAYING
    game.play("first", [0], Rank.ACE)

    game.skip("second")
    result = game.skip("third")

    assert result.round_ended
    assert result.discarded_count == 1
    assert len(game.pile) == 0
    assert game.current_rank is None
    assert game.current_player.id == "first"


@pytest.mark.parametrize(
    ("played_card", "claimed_rank", "expected_loser", "expected_starter"),
    [
        (Card(Rank.ACE, Suit.CLUBS), Rank.ACE, "second", "first"),
        (Card(Rank.TWO, Suit.CLUBS), Rank.ACE, "first", "second"),
    ],
)
def test_both_challenge_outcomes_remain_available(
    played_card, claimed_rank, expected_loser, expected_starter
):
    game = make_game(
        first_hand=[
            played_card,
            Card(Rank.THREE, Suit.HEARTS),
            Card(Rank.FOUR, Suit.HEARTS),
        ]
    )
    game.play("first", [0], claimed_rank)

    result = game.challenge("second")

    assert result.loser_id == expected_loser
    assert result.next_round_starter_id == expected_starter
    assert game.get_player(expected_loser).card_count == (
        9 if expected_loser == "second" else 3
    )
    challenge_event = next(
        event for event in reversed(game.event_log)
        if event["type"] == "challenge"
    )
    assert challenge_event["revealed_cards"] == [str(played_card)]
    assert challenge_event["at"] > 0


def test_provisional_final_play_remains_challengeable():
    game = make_game(first_hand=[Card(Rank.ACE, Suit.CLUBS)])
    game.play("first", [0], Rank.ACE)

    result = game.challenge("second")

    assert result.challenged_player_id == "first"
    assert result.was_bluff is False
    assert game.status is GameStatus.FINISHED
    assert game.finishing_order == ["first", "second"]
    assert game.available_actions("first") == []


def test_provisional_final_play_is_not_returned_to_finisher():
    game = make_game(first_hand=[Card(Rank.ACE, Suit.CLUBS)])
    game.play("first", [0], Rank.ACE)

    result = game.skip("second")

    assert result.round_ended
    assert game.status is GameStatus.FINISHED
    assert game.finishing_order == ["first", "second"]
    assert game.current_player.id != "first"
    assert game.available_actions("first") == []


def test_last_remaining_player_finishes_without_invalidating_the_game():
    game = make_game(
        second_hand=[
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.THREE, Suit.CLUBS),
        ],
    )
    game.players[0].hand = []
    game.finishing_order = ["first"]
    game.current_player_index = 1

    game.play("second", [0], Rank.ACE)

    assert game.status is GameStatus.FINISHED
    assert game.finishing_order == ["first", "second"]
    assert game.last_place_id == "second"


def test_three_decks_deal_three_aces_and_select_one_holder_to_open():
    players = [Player(str(index), f"Player {index}") for index in range(6)]
    game = BluffGame(players, deck_count=3)

    game.start(seed=23)

    ace_of_spades = Card(Rank.ACE, Suit.SPADES)
    assert sum(player.hand.count(ace_of_spades) for player in players) == 3
    assert ace_of_spades in game.current_player.hand


def test_timeout_pauses_after_control_returns_to_contributor():
    import asyncio

    game = play_four_and_return_turn()
    room = Room("ABCDE", game.players, "first", game=game, turn_deadline=time.time() - 1)
    manager = Manager(MemoryRoomStore(), History("sqlite://"))

    asyncio.run(manager.apply_timeout(room))

    assert room.paused
    assert room.paused_by == "system"
    assert room.turn_deadline is None
    assert len(game.pile) == 4
    assert len(game.discard_pile) == 0
    assert game.current_rank == Rank.ACE
    assert game.current_player.id == "first"
