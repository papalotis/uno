"""Enums for the Uno game."""

from __future__ import annotations

from enum import Enum
from typing import Self


class CardColor(int, Enum):
    """The colors of the Uno cards."""

    RED, BLUE, GREEN, YELLOW, WILDCARD = range(5)

    @classmethod
    def non_wildcard_colors(cls) -> tuple[Self, ...]:
        """Tuple of non wildcard colors."""
        return tuple(cls)[:-1]


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
