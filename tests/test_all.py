"""Tests for the uno package."""

import pytest

from uno.enums import CardColor, CardValue
from uno.errors import (
    GameIsOverError,
    InDrawChainButWrongTopCardError,
    InvalidCardError,
    PlayValidationError,
    SpecifiedColorButNoCardError,
)
from uno.main import BasicAIPlayer, Card, Deck, GameManager, Player

# pyright: reportPrivateUsage=false


# Fixtures for reusable test setup
@pytest.fixture
def basic_deck() -> Deck:
    return Deck.create_full_deck()


@pytest.fixture
def sample_card() -> Card:
    return Card(CardColor.RED, CardValue.FIVE)


@pytest.fixture
def wild_card() -> Card:
    return Card(CardColor.WILDCARD, CardValue.DRAW_4)


@pytest.fixture
def sample_player() -> Player:
    return BasicAIPlayer(name="Test Player")


@pytest.fixture
def sample_game_manager() -> GameManager:
    players: list[Player] = [BasicAIPlayer("Player 1"), BasicAIPlayer("Player 2")]
    game_manager = GameManager(players=players, round_limit=50)
    game_manager._do_pre_game_setup()
    return game_manager


# Test cases


# Card Tests
def test_card_creation_valid(sample_card: Card):
    assert sample_card.color == CardColor.RED
    assert sample_card.value == CardValue.FIVE


def test_card_creation_invalid():
    with pytest.raises(InvalidCardError):
        Card(CardColor.WILDCARD, CardValue.FIVE)  # Invalid combination


def test_is_wild_card(wild_card: Card):
    assert wild_card.is_wild_card()


def test_is_color_card(sample_card: Card):
    assert sample_card.is_color_card()


def test_card_can_be_played_on_top(sample_card: Card, wild_card: Card):
    top_card = Card(CardColor.RED, CardValue.FOUR)
    assert sample_card.can_be_played_on_top_of_other(top_card, None, in_draw_chain=False)

    with pytest.raises(InDrawChainButWrongTopCardError):
        wild_card.can_be_played_on_top_of_other(top_card, None, in_draw_chain=True)


# Deck Tests
def test_deck_creation_full(basic_deck: Deck):
    assert len(basic_deck.cards) == 108


def test_draw_random_card(basic_deck: Deck):
    card_count_before = len(basic_deck.cards)
    card = basic_deck.draw_random_card()
    assert isinstance(card, Card)
    assert len(basic_deck.cards) == card_count_before - 1


def test_remove_card_from_deck(basic_deck: Deck, sample_card: Card) -> None:
    # start from full deck, remove a card, check if it's not in the deck anymore
    basic_deck.remove_card(sample_card)
    assert sample_card in basic_deck.cards
    basic_deck.remove_card(sample_card)  # We need to remove the card twice because sample card is not a ZERO card
    assert sample_card not in basic_deck.cards

    with pytest.raises(ValueError, match="is not in the deck"):
        basic_deck.remove_card(sample_card)  # Card is not in the deck

    basic_deck.cards.clear()

    with pytest.raises(ValueError, match="Deck is empty"):
        basic_deck.remove_card(sample_card)


# Player Tests
def test_player_receive_card(sample_player: Player, sample_card: Card) -> None:
    sample_player.receive_card(sample_card)
    assert sample_card in sample_player.hand


def test_player_remove_card(sample_player: Player, sample_card: Card) -> None:
    sample_player.receive_card(sample_card)
    sample_player.remove_card_from_player(sample_card)
    assert sample_card not in sample_player.hand


def test_ai_player_get_card_to_play(sample_player: BasicAIPlayer, sample_card: Card) -> None:
    sample_player.receive_card(sample_card)
    top_card = Card(CardColor.RED, CardValue.THREE)
    card_to_play, _ = sample_player.get_card_to_play(top_card, None, in_draw_chain=False)
    assert card_to_play == sample_card


# GameManager Tests
def test_game_manager_initialization(sample_game_manager: GameManager) -> None:
    assert len(sample_game_manager.players) == 2
    assert sample_game_manager.round_limit == 50


def test_game_manager_give_player_random_cards(sample_game_manager: GameManager, sample_player: Player) -> None:
    card_count_before = len(sample_player.hand)
    sample_game_manager._give_player_random_cards(sample_player, 3)
    assert len(sample_player.hand) == card_count_before + 3


def test_game_manager_top_card(sample_game_manager: GameManager):
    sample_game_manager.discard_pile.append(Card(CardColor.RED, CardValue.FIVE))
    assert sample_game_manager.top_card == Card(CardColor.RED, CardValue.FIVE)


def test_game_over(sample_game_manager: GameManager):
    assert not sample_game_manager._game_over()
    sample_game_manager.players[0].hand.clear()
    assert sample_game_manager._game_over()


def test_play_one_round(sample_game_manager: GameManager):
    sample_game_manager.play_one_round()
    assert sample_game_manager.round_number == 1


def test_validate_card_play(sample_game_manager: GameManager, sample_player: Player):
    card = Card(CardColor.RED, CardValue.THREE)
    sample_player.receive_card(card)

    sample_game_manager.discard_pile.append(Card(CardColor.RED, CardValue.FIVE))

    sample_game_manager.validate_card_play(sample_player, card, None)


# Simulated Game Test
def test_simulate_game_with_seed():
    players: list[Player] = [BasicAIPlayer(name) for name in ["Alice", "Bob", "Charlie"]]
    game_manager = GameManager(players, seed=42, round_limit=100)
    game_manager.play_game()

    assert game_manager.round_number <= 100


def test_game_winner(sample_game_manager: GameManager):
    sample_game_manager.players[0].receive_card(Card(CardColor.RED, CardValue.FIVE))
    assert not sample_game_manager._game_over()
    sample_game_manager.players[0].hand.clear()
    assert sample_game_manager._game_over()


# Error Handling Tests
def test_invalid_card_play_error(sample_game_manager: GameManager, sample_player: Player):
    card = Card(CardColor.RED, CardValue.THREE)
    sample_player.receive_card(card)
    sample_game_manager.discard_pile.append(Card(CardColor.BLUE, CardValue.FIVE))

    with pytest.raises(PlayValidationError, match="wants to play invalid card"):
        sample_game_manager.validate_card_play(sample_player, card, None)

    sample_game_manager.discard_pile.append(Card(CardColor.RED, CardValue.FIVE))

    with pytest.raises(PlayValidationError, match="wants to play a non-wild card"):
        sample_game_manager.validate_card_play(sample_player, card, CardColor.RED)


def test_specified_color_but_no_card_error(sample_game_manager: GameManager, sample_player: Player):
    with pytest.raises(SpecifiedColorButNoCardError):
        sample_game_manager.handle_player_does_not_play_a_card(sample_player, CardColor.RED)


def test_game_is_over_error(sample_game_manager: GameManager):
    sample_game_manager.round_number = sample_game_manager.round_limit
    with pytest.raises(GameIsOverError):
        sample_game_manager.play_one_round()
