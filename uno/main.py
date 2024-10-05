"""An implementation of the card game Uno."""

from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
from typing import Self, override

from uno.enums import CardColor, CardValue
from uno.errors import (
    GameIsOverError,
    InDrawChainButWrongTopCardError,
    InvalidCardError,
    PlayValidationError,
    SpecifiedColorButNoCardError,
)
from uno.logger import create_logger

logger = create_logger(__name__, level=logging.INFO)


VALUE_POWER: dict[CardValue, int] = {key_value: 0 for key_value in list(CardValue)[: CardValue.SKIP]} | {
    CardValue.REVERSE: 1,
    CardValue.SKIP: 2,
    CardValue.PICK_COLOR: 3,
    CardValue.DRAW_2: 4,
    CardValue.DRAW_4: 5,
}


@dataclass(frozen=True)
class Card:
    """An Uno card which has a color and a value."""

    color: CardColor
    value: CardValue

    @classmethod
    def create_card_safe(cls, color: CardColor, value: CardValue) -> Card | None:
        """Create a card safely."""
        try:
            return cls(color, value)
        except InvalidCardError:
            return None

    def __post_init__(self) -> None:
        """Make sure that the card is valid."""
        self.raise_not_valid()

    def _check_valid(self) -> bool:
        return self.is_wild_card() or self.is_color_card()

    def raise_not_valid(self) -> None:
        """Raise an InvalidCardError if the card is not valid."""
        if not self._check_valid():
            raise InvalidCardError(f"{self} is not a valid card")

    def is_wild_card(self) -> bool:
        """Check if the card is a wild card."""
        return self.color == CardColor.WILDCARD and self.value >= CardValue.DRAW_4

    def is_color_card(self) -> bool:
        """Check if the card is a color card."""
        return self.color != CardColor.WILDCARD and self.value < CardValue.DRAW_4

    @property
    def number_of_instances_in_full_deck(self) -> int:
        """Number of cards of this type in a full deck.

        Wild cards have 4 instances in a full deck
        All other cards have 2 instances in a full deck, except for the ZERO cards
        which have only 1 instance in a full deck.
        """
        self.raise_not_valid()
        if self.is_wild_card():
            return 4

        if self.value == CardValue.ZERO:
            return 1

        return 2

    def can_be_played_on_top_of_other(
        self, down_card: Card, down_wildcard_color: CardColor | None, *, in_draw_chain: bool
    ) -> bool:
        """Indicate if this card can be played on top of another card."""
        if in_draw_chain:
            # the down card is either a DRAW_2 or a DRAW_4
            # we can play another DRAW_2 or DRAW_4 on top of it
            # to keep the draw chain going
            if not down_card.value.is_draw_value():
                raise InDrawChainButWrongTopCardError(f"In draw chain, but {down_card} is not a drawing card")
            # we can only play a DRAW_2 on top of a DRAW_2
            # and a DRAW_4 on top of a DRAW_4
            return self.value == down_card.value

        # we are not in a draw chain
        if self.is_color_card():
            # if we are a color card, we can play on top of any color card
            # or any card with the same value as the "assigned" color of the wild card
            if down_card.is_color_card():
                if down_wildcard_color is not None:
                    raise ValueError("down_wildcard_color should be None when down_card is a color card")
                # either we have the same color or the same value
                return self.color == down_card.color or self.value == down_card.value
            if down_card.is_wild_card():
                if down_wildcard_color is None:
                    raise ValueError("down_wildcard_color should not be None when down_card is a wild card")
                if down_wildcard_color == CardColor.WILDCARD:
                    raise ValueError("down_wildcard_color should not be WILDCARD")
                return self.color == down_wildcard_color

        if self.is_wild_card():
            # we can always play a wild card no matter what the down card is
            return True

        raise AssertionError("Unreachable code")


@dataclass
class Deck:
    """A deck of Uno cards."""

    cards: list[Card]

    @classmethod
    def create_full_deck(cls) -> Self:
        """Create a full deck of Uno cards."""
        list_cards: list[Card] = []

        for color, value in product(CardColor, CardValue):
            candidate_card = Card.create_card_safe(color, value)
            if candidate_card is None:
                continue

            list_cards.extend([candidate_card] * candidate_card.number_of_instances_in_full_deck)

        return cls(list_cards)

    def draw_random_card(self) -> Card:
        """Draw a random card and remove it from the deck."""
        random_card = random.choice(self.cards)  # noqa: S311
        self.remove_card(random_card)
        return random_card

    def remove_card(self, card: Card) -> None:
        """Remove a card from the deck."""
        if len(self.cards) == 0:
            raise ValueError("Deck is empty")

        if card not in self.cards:
            raise ValueError(f"{card} is not in the deck")
        self.cards.remove(card)


@dataclass
class Player(ABC):
    """A player in the Uno game."""

    name: str
    hand: list[Card] = field(init=False, default_factory=list)

    @abstractmethod
    def get_card_to_play(
        self, top_card: Card, top_card_wildcard_color: CardColor | None = None, *, in_draw_chain: bool
    ) -> tuple[Card | None, CardColor | None]:
        """Define the logic of the player to play a card.

        Subclasses should implement this method.

        The method should return a tuple with the card the player wants to play and the color for a wild card if the
        player wants to play a wild card. If the player does not want to play a wild card, the method should return
        `None` for the color.

        If the player does not want to play a card, the method should return None for both.
        """

    def receive_card(self, card: Card) -> None:
        """Receive a card. Used for dealing cards to the player and for drawing cards."""
        self.hand.append(card)

    def remove_card_from_player(self, card: Card) -> None:
        """Remove a card from the player's hand."""
        if card not in self.hand:
            raise ValueError(f"{card} is not in the hand of {self.name}")
        self.hand.remove(card)


@dataclass
class BasicAIPlayer(Player):
    """A basic AI player in the Uno game."""

    @override
    def get_card_to_play(
        self, top_card: Card, top_card_wildcard_color: CardColor | None = None, *, in_draw_chain: bool
    ) -> tuple[Card | None, CardColor | None]:
        cards_that_can_be_played = [
            card
            for card in self.hand
            if card.can_be_played_on_top_of_other(top_card, top_card_wildcard_color, in_draw_chain=in_draw_chain)
        ]

        if len(cards_that_can_be_played) == 0:
            logger.debug("%s doesnt have any cards to play", self.name)
            return None, None

        best_card = max(cards_that_can_be_played, key=lambda card: VALUE_POWER[card.value])

        color_wild = None
        if best_card.is_wild_card():
            colors = [card.color for card in self.hand if not card.is_wild_card()]
            color_wild = CardColor.RED if len(colors) == 0 else Counter(colors).most_common()[0][0]

        return best_card, color_wild


@dataclass
class GameManager:
    """Class that runs the Uno game."""

    players: list[Player]
    round_limit: int = 1000
    number_of_cards_to_start_with: int = 7
    seed: int | None = None
    show_plot_of_number_of_cards_per_round: bool = False
    deck: Deck = field(init=False, default_factory=Deck.create_full_deck)
    discard_pile: list[Card] = field(init=False, default_factory=list)  # the cards that have been played
    play_direction: int = field(init=False, default=1)  # 1 for clockwise, -1 for counter-clockwise
    current_player_index: int = field(init=False, default=0)  # index of the current player
    draw_chain: list[Card] = field(init=False, default_factory=list)  # the +2/+4 cards that have been played
    round_number: int = field(init=False, default=0)  # the current round number
    temporary_top_card_color: CardColor | None = field(
        init=False, default=None
    )  # the color of the top card if a wild card was played
    number_of_cards_per_round: list[dict[str, int]] = field(init=False, default_factory=list)
    next_round_is_skip: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        """Check that the number of players is valid."""
        # at least 2 players are required
        # at most 10 players are allowed
        if len(self.players) not in range(2, 11):
            raise ValueError("The number of players must be between 2 and 10. It is {len(self.players)}")

        if self.seed is not None:
            random.seed(self.seed)

        if self.number_of_cards_to_start_with < 1:
            raise ValueError(
                f"The number of cards to start with must be at least 1, but is {self.number_of_cards_to_start_with}"
            )

    def _calculate_number_of_cards_to_draw_in_current_draw_chain(self) -> int:
        return sum(2 if card.value == CardValue.DRAW_2 else 4 for card in self.draw_chain)

    def _give_player_random_cards(self, player: Player, number_of_cards: int) -> None:
        if number_of_cards < 1:
            raise ValueError(f"Number of cards to give to player must be at least 1, but is {number_of_cards}")

        for _ in range(number_of_cards):
            if len(self.deck.cards) == 0:
                self._refill_deck()

            if len(self.deck.cards) == 0:
                raise ValueError("Deck is empty and cannot be refilled")

            card_give_to_player = self.deck.draw_random_card()
            player.receive_card(card_give_to_player)

    @property
    def top_card(self) -> Card:
        """Get the top card of the discard pile."""
        if len(self.discard_pile) == 0:
            raise ValueError("The discard pile is empty")
        return self.discard_pile[-1]

    def _game_over(self) -> bool:
        return any(len(player.hand) == 0 for player in self.players) or self.round_number >= self.round_limit

    def _find_winner(self) -> Player | None:
        return next((player for player in self.players if len(player.hand) == 0), None)

    def handle_player_does_not_play_a_card(
        self, current_player: Player, color_for_wildcard: CardColor | None
    ) -> CardColor | None:
        """Handle the case when the player does not want to play a card. The player must draw at least one card."""
        # Player does not have any card to play
        if color_for_wildcard is not None:
            raise SpecifiedColorButNoCardError(f"Player specifies a color {color_for_wildcard} without playing a card")

        # draw at least one card (if we are not in a draw chain)
        cards_to_give_to_player = max(self._calculate_number_of_cards_to_draw_in_current_draw_chain(), 1)
        card_string = "1 card" if cards_to_give_to_player == 1 else f"{cards_to_give_to_player} cards"
        logger.debug("%s draws %s", current_player.name, card_string)
        self._give_player_random_cards(current_player, cards_to_give_to_player)

        # Player drew cards, the draw chain is broken
        self.draw_chain.clear()

        # We propagate the color of the top card if a wild card was played since this player did not play a card
        logger.debug("%s did not play a card so the temporary color is propagated", current_player.name)
        return self.temporary_top_card_color

    def handle_player_wants_to_play_a_card(
        self, current_player: Player, card_player_wants_to_play: Card, color_for_wildcard: CardColor | None
    ) -> CardColor | None:
        """Handle the case when the player wants to play a card.

        Validate that the player is playing a valid card. and update the game state accordingly.
        This method removes the card from the player's hand but does not add it to the discard pile.
        """
        self.validate_card_play(current_player, card_player_wants_to_play, color_for_wildcard)

        current_player.remove_card_from_player(card_player_wants_to_play)

        if card_player_wants_to_play.value.is_draw_value():
            # A draw card was played, the next player must draw 2 or 4 cards
            self.draw_chain.append(card_player_wants_to_play)

        if card_player_wants_to_play.value == CardValue.REVERSE:
            # A reverse card was played, the direction of play is reversed
            self.play_direction = 1 if self.play_direction == -1 else -1

        message_card_wants_to_play = (
            str(card_player_wants_to_play)
            if not card_player_wants_to_play.is_wild_card()
            else f"{card_player_wants_to_play} {color_for_wildcard}"
        )

        message = (
            f"{current_player.name} will play {message_card_wants_to_play}. They have {len(current_player.hand)} card"
            f"{'s' if len(current_player.hand) != 1 else ''} left"
        )

        logger.debug(message)
        return color_for_wildcard

    def play_one_round(self) -> bool:
        """Play one round of the game. Raise a GameIsOverError if the game is already over."""
        if self._game_over():
            raise GameIsOverError("The game is already over")

        current_player = self.players[self.current_player_index]

        if self.next_round_is_skip:
            self.next_round_is_skip = False
            logger.debug("%s is skipped", current_player.name)
        else:
            card_player_wants_to_play, color_for_wildcard = current_player.get_card_to_play(
                self.top_card, self.temporary_top_card_color, in_draw_chain=len(self.draw_chain) > 0
            )

            temporary_top_card_color = self.handle_play(current_player, card_player_wants_to_play, color_for_wildcard)
            logger.debug("Temporary top card color is %s", temporary_top_card_color)

            if card_player_wants_to_play is not None:
                # player played a card and we have validated that the play is valid, add the card to the discard pile
                self.discard_pile.append(card_player_wants_to_play)

                if card_player_wants_to_play.value == CardValue.SKIP:
                    self.next_round_is_skip = True

            self.temporary_top_card_color = temporary_top_card_color

        # Move to the next player
        self.current_player_index = (self.current_player_index + self.play_direction) % len(self.players)

        self.round_number += 1

        return self._game_over()

    def handle_play(
        self, current_player: Player, card_player_wants_to_play: Card | None, color_for_wildcard: CardColor | None
    ) -> CardColor | None:
        """Handle the play of a card by a player. Return the offset to the next player."""
        return (
            self.handle_player_does_not_play_a_card(current_player, color_for_wildcard)
            if card_player_wants_to_play is None
            else self.handle_player_wants_to_play_a_card(current_player, card_player_wants_to_play, color_for_wildcard)
        )

    def validate_card_play(
        self, current_player: Player, card_player_wants_to_play: Card, color_for_wildcard: CardColor | None
    ) -> None:
        """Check if the card the player wants to play is valid.

        A ValueError is raised if the card is not valid.
        """
        card_player_wants_to_play.raise_not_valid()

        # No matter what the new color, it can never be a wild card
        # something has gone really wrong if this happens
        if color_for_wildcard == CardColor.WILDCARD:
            raise PlayValidationError(
                f"Player {current_player} wants to play a wild card {card_player_wants_to_play} with an invalid color"
                f" {color_for_wildcard}"
            )

        if card_player_wants_to_play not in current_player.hand:
            # Player wants to play a card they do not have

            raise PlayValidationError(
                f"Player {current_player} wants to play card {card_player_wants_to_play} they do not have in their hand"
                f" {current_player.hand}"
            )

        if not card_player_wants_to_play.can_be_played_on_top_of_other(
            self.top_card, self.temporary_top_card_color, in_draw_chain=len(self.draw_chain) > 0
        ):
            # Player wants to play an invalid card
            raise PlayValidationError(
                f"Player {current_player} wants to play invalid card {card_player_wants_to_play} on top of"
                f" {self.top_card} with {self.draw_chain=}"
            )

        # If the player wants to play a wild card, they must specify a color
        # But if the player does not want to play a wild card, they are not allowed to
        # specify a color
        if color_for_wildcard is None and card_player_wants_to_play.is_wild_card():
            raise PlayValidationError(
                f"Player {current_player} wants to play a wild card {card_player_wants_to_play} without specifying a"
                " color"
            )
        if color_for_wildcard is not None and not card_player_wants_to_play.is_wild_card():
            raise PlayValidationError(
                f"Player {current_player} wants to play a non-wild card {card_player_wants_to_play} with a specified"
                f" color {color_for_wildcard}"
            )

    def _refill_deck(self) -> None:
        """Add all but the top card of the discard pile to the deck and shuffle the deck."""
        cards_to_add_to_deck = self.discard_pile[:-1].copy()
        random.shuffle(cards_to_add_to_deck)
        self.deck = Deck(cards_to_add_to_deck)

        self.discard_pile = [self.discard_pile[-1]]

    def _record_number_of_cards_per_round(self) -> None:
        number_of_cards_per_player = {player.name: len(player.hand) for player in self.players}
        self.number_of_cards_per_round.append(number_of_cards_per_player)

    def _create_plot_of_number_of_cards_per_round(self) -> None:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            logger.exception(
                "Matplotlib is required to create the plot of the number of cards per round. Install with [extras] like"
                " `pip install uno[extras]`"
            )
            return

        logger.debug("Creating plot of number of cards per round")
        for player in self.players:
            number_of_cards = [game_round[player.name] for game_round in self.number_of_cards_per_round]
            plt.plot(number_of_cards, label=player.name)  # pyright: ignore [reportUnknownMemberType]

        plt.xlabel("Round")  # pyright: ignore [reportUnknownMemberType]
        plt.ylabel("Number of cards")  # pyright: ignore [reportUnknownMemberType]
        plt.legend()  # pyright: ignore [reportUnknownMemberType]
        plt.show()  # pyright: ignore [reportUnknownMemberType]

    def _pick_first_card(self) -> Card:
        """Pick the first card from the deck to start the game. First card cannot be a wild card."""
        while True:
            card = self.deck.draw_random_card()

            if not card.is_wild_card():
                return card

            # create a new deck and try again
            self.deck = Deck.create_full_deck()

    def _give_starting_cards(self) -> None:
        """Give the starting cards to the players."""
        for player in self.players:
            self._give_player_random_cards(player, number_of_cards=self.number_of_cards_to_start_with)

    def _do_pre_game_setup(self) -> None:
        """Do the pre-game setup."""
        self.discard_pile.append(self._pick_first_card())
        logger.debug("First card is %s", self.top_card)
        self._give_starting_cards()

    def play_game(self) -> None:
        """Play the Uno game."""
        self._do_pre_game_setup()

        self._record_number_of_cards_per_round()

        while not self._game_over():
            self.play_one_round()
            self._record_number_of_cards_per_round()

        winner = self._find_winner()
        if winner is None:
            logger.debug("After %s rounds, the game ends in a draw.", self.round_number)
        else:
            logger.debug("After %s rounds the winner is %s.", self.round_number, winner.name)

        if self.show_plot_of_number_of_cards_per_round:
            self._create_plot_of_number_of_cards_per_round()


def play_game_with_seed(seed: int) -> int:
    """Simulate a game of UNO with a given random seed."""
    players: list[Player] = [BasicAIPlayer(name) for name in ["Alice", "Bob", "Charlie", "David", "Eve", "Frank"]]
    game_manager = GameManager(players, seed=seed, show_plot_of_number_of_cards_per_round=False, round_limit=100_000)
    game_manager.play_game()

    return game_manager.round_number


def _main() -> None:
    """Run a demo game."""
    number_of_round_for_each_seed: list[int] = []

    number_of_round_for_each_seed = [play_game_with_seed(seed) for seed in range(10000)]

    logger.info("All games have finished")
    average_rounds = sum(number_of_round_for_each_seed) / len(number_of_round_for_each_seed)
    logger.info("Average number of rounds: %.0f", average_rounds)
    logger.info("Minimum number of rounds: %s", min(number_of_round_for_each_seed))
    logger.info("Maximum number of rounds: %s", max(number_of_round_for_each_seed))


if __name__ == "__main__":
    _main()
