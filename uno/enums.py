"""Enums for the Uno game."""

from __future__ import annotations

from enum import Enum


class CardColor(int, Enum):
    """The colors of the Uno cards."""

    RED, BLUE, GREEN, YELLOW, WILDCARD = range(5)


class CardValue(int, Enum):
    """The values of the Uno cards.

    The values are defined such that normal "number" cards are aligned with their
    index in the enum, and the special cards are defined after the normal cards.
    """

    (
        ZERO,
        ONE,
        TWO,
        THREE,
        FOUR,
        FIVE,
        SIX,
        SEVEN,
        EIGHT,
        NINE,
        SKIP,
        REVERSE,
        DRAW_2,
        DRAW_4,
        PICK_COLOR,
    ) = range(15)

    def is_draw_value(self) -> bool:
        """Return whether the card value is a draw value."""
        return self in {CardValue.DRAW_2, CardValue.DRAW_4}
