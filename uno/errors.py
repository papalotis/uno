"""Contains the custom exceptions for the Uno library."""


class UnoError(Exception):
    """Represents an error that occurred in the Uno library."""


class InvalidCardError(UnoError):
    """Represents an error that occurred when a card is invalid."""


class PlayValidationError(UnoError):
    """Represents an error that occurred when validating a play."""


class InDrawChainButWrongTopCardError(UnoError):
    """Top card is not +2 or +4 but we are in a draw chain."""


class SpecifiedColorButNoCardError(UnoError):
    """Specified a color but no card to play.

    If a player does not want to play a card, they cannot specify a color for a wild card.
    """


class GameIsOverError(UnoError):
    """The game is over and no more plays can be made."""
