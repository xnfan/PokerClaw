"""Pot and side-pot calculation for Texas Hold'em."""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.engine.hand_evaluator import HandScore


@dataclass
class SidePot:
    amount: int
    eligible_player_ids: list[str]


class PotManager:
    """Tracks bets and calculates main pot / side pots."""

    def __init__(self) -> None:
        self.player_bets: dict[str, int] = {}  # total bet this hand
        self._all_in_amounts: list[int] = []

    @property
    def total_pot(self) -> int:
        return sum(self.player_bets.values())

    def add_bet(self, player_id: str, amount: int) -> None:
        self.player_bets[player_id] = self.player_bets.get(player_id, 0) + amount

    def mark_all_in(self, player_id: str) -> None:
        """Record that a player went all-in at their current bet level."""
        bet = self.player_bets.get(player_id, 0)
        if bet not in self._all_in_amounts:
            self._all_in_amounts.append(bet)

    def build_pots(self, active_player_ids: set[str]) -> list[SidePot]:
        """Build ordered list of pots (main + side pots).

        active_player_ids: players still in the hand (not folded).
        """
        if not self.player_bets:
            return []

        # All thresholds where pots split
        thresholds = sorted(set(self._all_in_amounts + [max(self.player_bets.values())]))
        pots: list[SidePot] = []
        prev_threshold = 0

        for threshold in thresholds:
            if threshold <= prev_threshold:
                continue
            pot_amount = 0
            eligible: list[str] = []
            for pid, bet in self.player_bets.items():
                contribution = min(bet, threshold) - min(bet, prev_threshold)
                if contribution > 0:
                    pot_amount += contribution
                # Eligible if still active AND contributed to this level
                if pid in active_player_ids and bet >= threshold:
                    eligible.append(pid)
                elif pid in active_player_ids and bet > prev_threshold:
                    eligible.append(pid)
            if pot_amount > 0 and eligible:
                pots.append(SidePot(amount=pot_amount, eligible_player_ids=eligible))
            prev_threshold = threshold

        return pots

    def distribute_winnings(
        self,
        hand_scores: dict[str, HandScore],
        active_player_ids: set[str],
    ) -> dict[str, int]:
        """Distribute pot(s) to winners. Returns {player_id: winnings}."""
        pots = self.build_pots(active_player_ids)
        winnings: dict[str, int] = {}

        for pot in pots:
            # Find eligible players who have hand scores
            eligible_scores = {
                pid: hand_scores[pid]
                for pid in pot.eligible_player_ids
                if pid in hand_scores
            }
            if not eligible_scores:
                continue

            best_score = max(eligible_scores.values())
            winners = [
                pid for pid, score in eligible_scores.items()
                if score == best_score
            ]
            share = pot.amount // len(winners)
            remainder = pot.amount % len(winners)
            for i, winner_id in enumerate(winners):
                # First winner gets odd chip
                extra = 1 if i < remainder else 0
                winnings[winner_id] = winnings.get(winner_id, 0) + share + extra

        return winnings

    def reset(self) -> None:
        self.player_bets.clear()
        self._all_in_amounts.clear()
