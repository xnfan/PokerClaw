"""Card, Rank, and Suit definitions for Texas Hold'em."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class Suit(Enum):
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"
    SPADES = "s"


# Short display names for ranks
_RANK_SYMBOLS: dict[Rank, str] = {
    Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
    Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
    Rank.TEN: "T", Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K",
    Rank.ACE: "A",
}

_SYMBOL_TO_RANK: dict[str, Rank] = {v: k for k, v in _RANK_SYMBOLS.items()}
_SYMBOL_TO_SUIT: dict[str, Suit] = {s.value: s for s in Suit}


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{_RANK_SYMBOLS[self.rank]}{self.suit.value}"

    def __repr__(self) -> str:
        return f"Card({self})"

    @classmethod
    def from_string(cls, text: str) -> Card:
        """Parse card from short string like 'Ah', 'Td', '2c'."""
        text = text.strip()
        if len(text) != 2:
            raise ValueError(f"Invalid card string: '{text}', expected 2 chars")
        rank_char, suit_char = text[0].upper(), text[1].lower()
        if rank_char not in _SYMBOL_TO_RANK:
            raise ValueError(f"Invalid rank: '{rank_char}'")
        if suit_char not in _SYMBOL_TO_SUIT:
            raise ValueError(f"Invalid suit: '{suit_char}'")
        return cls(rank=_SYMBOL_TO_RANK[rank_char], suit=_SYMBOL_TO_SUIT[suit_char])

    def to_dict(self) -> dict:
        return {"rank": self.rank.value, "suit": self.suit.value, "str": str(self)}
