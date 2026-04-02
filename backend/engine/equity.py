"""Monte Carlo equity calculator for Texas Hold'em."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from backend.engine.card import Card, Rank, Suit
from backend.engine.hand_evaluator import HandEvaluator, HandScore


@dataclass(frozen=True)
class EquityResult:
    """Equity result for a single player."""
    win_pct: float
    tie_pct: float
    lose_pct: float
    sample_count: int


class EquityCalculator:
    """Monte Carlo equity calculator."""

    @staticmethod
    def calculate(
        players_cards: list[list[Card]],
        community: list[Card] | None = None,
        num_simulations: int = 5000,
        seed: int | None = None,
    ) -> list[EquityResult]:
        """Calculate equity for each player via Monte Carlo simulation.

        Args:
            players_cards: List of hole cards per player (each is 2 Cards).
            community: Known community cards (0-5). None = empty.
            num_simulations: Number of random runouts to simulate.
            seed: Optional RNG seed for reproducibility.

        Returns:
            List of EquityResult, one per player.
        """
        community = community or []
        n_players = len(players_cards)
        if n_players < 2:
            raise ValueError("Need at least 2 players")

        # Validate no duplicate cards
        all_known: list[Card] = []
        for hand in players_cards:
            if len(hand) != 2:
                raise ValueError("Each player must have exactly 2 hole cards")
            all_known.extend(hand)
        all_known.extend(community)
        if len(all_known) != len(set(all_known)):
            raise ValueError("Duplicate cards detected")

        # Build remaining deck
        full_deck = [
            Card(rank=r, suit=s)
            for r in Rank
            for s in Suit
        ]
        known_set = set(all_known)
        remaining = [c for c in full_deck if c not in known_set]

        cards_needed = 5 - len(community)
        rng = random.Random(seed)

        wins = [0] * n_players
        ties = [0] * n_players

        # If board is complete, no simulation needed
        if cards_needed == 0:
            scores = [
                HandEvaluator.evaluate(players_cards[i], community)
                for i in range(n_players)
            ]
            best = max(scores)
            winner_indices = [i for i, s in enumerate(scores) if s == best]
            if len(winner_indices) == 1:
                wins[winner_indices[0]] = 1
            else:
                for i in winner_indices:
                    ties[i] = 1
            return [
                EquityResult(
                    win_pct=wins[i],
                    tie_pct=ties[i],
                    lose_pct=1.0 - wins[i] - ties[i],
                    sample_count=1,
                )
                for i in range(n_players)
            ]

        for _ in range(num_simulations):
            # Sample random community cards
            board = list(community) + rng.sample(remaining, cards_needed)

            # Evaluate each player
            scores = [
                HandEvaluator.evaluate(players_cards[i], board)
                for i in range(n_players)
            ]
            best = max(scores)
            winner_indices = [i for i, s in enumerate(scores) if s == best]

            if len(winner_indices) == 1:
                wins[winner_indices[0]] += 1
            else:
                for i in winner_indices:
                    ties[i] += 1

        return [
            EquityResult(
                win_pct=wins[i] / num_simulations,
                tie_pct=ties[i] / num_simulations,
                lose_pct=1.0 - (wins[i] + ties[i]) / num_simulations,
                sample_count=num_simulations,
            )
            for i in range(n_players)
        ]
