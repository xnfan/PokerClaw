"""Deck of 52 playing cards with shuffle and deal operations."""
from __future__ import annotations

import random
from typing import Sequence

from backend.engine.card import Card, Rank, Suit


class Deck:
    """Standard 52-card deck."""

    def __init__(self, seed: int | None = None):
        self._cards: list[Card] = [
            Card(rank, suit) for rank in Rank for suit in Suit
        ]
        self._rng = random.Random(seed)
        self._deal_index = 0

    def shuffle(self) -> None:
        """Shuffle remaining cards."""
        remaining = self._cards[self._deal_index:]
        self._rng.shuffle(remaining)
        self._cards[self._deal_index:] = remaining

    def deal(self, count: int = 1) -> list[Card]:
        """Deal cards from the top of the deck."""
        if self._deal_index + count > len(self._cards):
            raise ValueError(
                f"Cannot deal {count} cards, only {self.remaining} left"
            )
        dealt = self._cards[self._deal_index: self._deal_index + count]
        self._deal_index += count
        return dealt

    def remove_cards(self, cards_to_remove: Sequence[Card]) -> None:
        """Remove specific cards from undealt portion (for hand lab presets)."""
        remove_set = set(cards_to_remove)
        remaining = [
            c for c in self._cards[self._deal_index:] if c not in remove_set
        ]
        self._cards = self._cards[:self._deal_index] + remaining

    @property
    def remaining(self) -> int:
        return len(self._cards) - self._deal_index

    def reset(self, seed: int | None = None) -> None:
        """Reset deck to full 52 cards."""
        self._cards = [Card(rank, suit) for rank in Rank for suit in Suit]
        self._deal_index = 0
        if seed is not None:
            self._rng = random.Random(seed)
