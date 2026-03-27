"""Betting round logic for a single street."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from backend.engine.pot_manager import PotManager


class BettingAction(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class PlayerAction:
    player_id: str
    action: BettingAction
    amount: int = 0  # raise/all_in total amount for this action


@dataclass
class PlayerSeat:
    """Minimal player state needed by betting round."""
    player_id: str
    chips: int
    is_active: bool = True  # still in this hand (not folded)
    is_all_in: bool = False
    current_bet: int = 0    # bet in current round


class BettingRound:
    """Manages one round of betting (preflop/flop/turn/river)."""

    MAX_RAISES_PER_ROUND = 4  # standard cap on raises

    def __init__(
        self,
        seats: list[PlayerSeat],
        pot_manager: PotManager,
        current_bet: int = 0,
        min_raise: int = 0,
    ) -> None:
        self.seats = seats
        self.pot = pot_manager
        self.current_bet = current_bet
        self.min_raise = min_raise  # minimum raise increment
        self._action_index = 0
        self._last_raiser_id: str | None = None
        self._acted_since_raise: set[str] = set()
        self._raise_count = 0
        # Build action order: only active, non-all-in
        self._action_order = [
            s.player_id for s in seats if s.is_active and not s.is_all_in
        ]

    def get_valid_actions(self, player_id: str) -> list[BettingAction]:
        """Return list of valid actions for the given player."""
        seat = self._find_seat(player_id)
        if not seat.is_active or seat.is_all_in:
            return []

        actions: list[BettingAction] = [BettingAction.FOLD]
        to_call = self.current_bet - seat.current_bet

        if to_call <= 0:
            actions.append(BettingAction.CHECK)
        if to_call > 0 and seat.chips >= to_call:
            actions.append(BettingAction.CALL)
        # Can raise if have more chips than call amount AND raise cap not hit
        if seat.chips > to_call and self._raise_count < self.MAX_RAISES_PER_ROUND:
            actions.append(BettingAction.RAISE)
        # All-in is always available if player has chips
        if seat.chips > 0:
            actions.append(BettingAction.ALL_IN)

        return actions

    def apply_action(self, action: PlayerAction) -> None:
        """Apply a player's action to the round state."""
        seat = self._find_seat(action.player_id)

        if action.action == BettingAction.FOLD:
            seat.is_active = False
        elif action.action == BettingAction.CHECK:
            pass  # no chip movement
        elif action.action == BettingAction.CALL:
            call_amount = min(self.current_bet - seat.current_bet, seat.chips)
            seat.chips -= call_amount
            seat.current_bet += call_amount
            self.pot.add_bet(action.player_id, call_amount)
            if seat.chips == 0:
                seat.is_all_in = True
                self.pot.mark_all_in(action.player_id)
        elif action.action == BettingAction.RAISE:
            to_call = self.current_bet - seat.current_bet
            raise_total = max(action.amount, to_call + self.min_raise)
            raise_total = min(raise_total, seat.chips)  # cap at stack
            seat.chips -= raise_total
            seat.current_bet += raise_total
            self.min_raise = raise_total - to_call  # new min raise
            self.current_bet = seat.current_bet
            self.pot.add_bet(action.player_id, raise_total)
            self._last_raiser_id = action.player_id
            self._raise_count += 1
            self._acted_since_raise.clear()
            if seat.chips == 0:
                seat.is_all_in = True
                self.pot.mark_all_in(action.player_id)
        elif action.action == BettingAction.ALL_IN:
            all_in_amount = seat.chips
            seat.current_bet += all_in_amount
            seat.chips = 0
            seat.is_all_in = True
            self.pot.add_bet(action.player_id, all_in_amount)
            self.pot.mark_all_in(action.player_id)
            if seat.current_bet > self.current_bet:
                raise_diff = seat.current_bet - self.current_bet
                if raise_diff >= self.min_raise:
                    self.min_raise = raise_diff
                self.current_bet = seat.current_bet
                self._last_raiser_id = action.player_id
                self._raise_count += 1
                self._acted_since_raise.clear()

        self._acted_since_raise.add(action.player_id)

    def get_next_player_id(self) -> str | None:
        """Return next player to act, or None if round is complete."""
        active_non_allin = [
            s for s in self.seats if s.is_active and not s.is_all_in
        ]
        if len(active_non_allin) <= 1 and self._all_bets_settled():
            return None
        if len(active_non_allin) == 0:
            return None

        for _ in range(len(self._action_order)):
            idx = self._action_index % len(self._action_order)
            self._action_index += 1
            pid = self._action_order[idx]
            seat = self._find_seat(pid)
            if not seat.is_active or seat.is_all_in:
                continue
            # Player already acted since last raise and bet matches
            if pid in self._acted_since_raise and seat.current_bet == self.current_bet:
                continue
            return pid

        return None

    def is_complete(self) -> bool:
        return self.get_next_player_id() is None

    def _all_bets_settled(self) -> bool:
        """Check if all active players have matching bets or are all-in."""
        for s in self.seats:
            if s.is_active and not s.is_all_in and s.current_bet != self.current_bet:
                return False
        return True

    def _find_seat(self, player_id: str) -> PlayerSeat:
        for s in self.seats:
            if s.player_id == player_id:
                return s
        raise ValueError(f"Player {player_id} not found")
