"""Hand evaluation: determine best 5-card hand from 5-7 cards."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations

from backend.engine.card import Card, Rank


class HandRank(IntEnum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


@dataclass(frozen=True, order=True)
class HandScore:
    """Comparable hand score: higher is better."""
    hand_rank: HandRank
    tie_breakers: tuple[int, ...]

    def __str__(self) -> str:
        return f"{self.hand_rank.name} {self.tie_breakers}"


class HandEvaluator:
    """Evaluate poker hands and compare them."""

    @staticmethod
    def evaluate(hole_cards: list[Card], community_cards: list[Card]) -> HandScore:
        """Find best 5-card hand from hole + community cards."""
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            raise ValueError(f"Need at least 5 cards, got {len(all_cards)}")
        return HandEvaluator.best_five(all_cards)

    @staticmethod
    def best_five(cards: list[Card]) -> HandScore:
        """Find best HandScore from all C(n,5) combinations."""
        if len(cards) == 5:
            return HandEvaluator._score_five(cards)
        best = None
        for combo in combinations(cards, 5):
            score = HandEvaluator._score_five(list(combo))
            if best is None or score > best:
                best = score
        return best  # type: ignore[return-value]

    @staticmethod
    def _score_five(cards: list[Card]) -> HandScore:
        """Score exactly 5 cards."""
        ranks = sorted([c.rank for c in cards], reverse=True)
        suits = [c.suit for c in cards]
        rank_counts = Counter(ranks)
        is_flush = len(set(suits)) == 1
        is_straight, straight_high = HandEvaluator._check_straight(ranks)

        # Straight flush / Royal flush
        if is_flush and is_straight:
            if straight_high == Rank.ACE:
                return HandScore(HandRank.ROYAL_FLUSH, (Rank.ACE,))
            return HandScore(HandRank.STRAIGHT_FLUSH, (straight_high,))

        groups = HandEvaluator._group_by_count(rank_counts)

        # Four of a kind
        if 4 in rank_counts.values():
            quad = groups[4][0]
            kicker = groups[1][0]
            return HandScore(HandRank.FOUR_OF_A_KIND, (quad, kicker))

        # Full house
        if 3 in rank_counts.values() and 2 in rank_counts.values():
            trips = groups[3][0]
            pair = groups[2][0]
            return HandScore(HandRank.FULL_HOUSE, (trips, pair))

        # Flush
        if is_flush:
            return HandScore(HandRank.FLUSH, tuple(ranks))

        # Straight
        if is_straight:
            return HandScore(HandRank.STRAIGHT, (straight_high,))

        # Three of a kind
        if 3 in rank_counts.values():
            trips = groups[3][0]
            kickers = tuple(sorted(groups[1], reverse=True))
            return HandScore(HandRank.THREE_OF_A_KIND, (trips,) + kickers)

        # Two pair
        pairs = sorted(groups.get(2, []), reverse=True)
        if len(pairs) == 2:
            kicker = groups[1][0]
            return HandScore(HandRank.TWO_PAIR, (pairs[0], pairs[1], kicker))

        # One pair
        if len(pairs) == 1:
            kickers = tuple(sorted(groups[1], reverse=True))
            return HandScore(HandRank.ONE_PAIR, (pairs[0],) + kickers)

        # High card
        return HandScore(HandRank.HIGH_CARD, tuple(ranks))

    @staticmethod
    def _check_straight(ranks: list[Rank]) -> tuple[bool, int]:
        """Check if sorted-desc ranks form a straight. Returns (is_straight, high)."""
        unique = sorted(set(ranks), reverse=True)
        if len(unique) < 5:
            return False, 0
        # Normal straight check
        if unique[0] - unique[4] == 4:
            return True, unique[0]
        # Ace-low straight: A-2-3-4-5
        if set(unique) == {Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE}:
            return True, Rank.FIVE  # 5-high straight
        return False, 0

    @staticmethod
    def _group_by_count(rank_counts: Counter) -> dict[int, list[int]]:
        """Group rank values by their count. {count: [rank_values desc]}."""
        groups: dict[int, list[int]] = {}
        for rank_val, cnt in rank_counts.items():
            groups.setdefault(cnt, []).append(int(rank_val))
        for cnt in groups:
            groups[cnt].sort(reverse=True)
        return groups
