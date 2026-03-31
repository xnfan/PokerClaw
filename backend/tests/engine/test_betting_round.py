"""Tests for betting round logic, especially raise cap validation."""
import pytest
from backend.engine.betting_round import (
    BettingAction,
    BettingRound,
    PlayerAction,
    PlayerSeat,
)
from backend.engine.pot_manager import PotManager


def _make_seats(num=2, chips=5000, current_bet=0):
    return [
        PlayerSeat(
            player_id=f"p{i}",
            chips=chips,
            is_active=True,
            is_all_in=False,
            current_bet=current_bet,
        )
        for i in range(num)
    ]


class TestRaiseCap:
    def test_max_four_raises_per_round(self):
        """After 4 raises, only fold/call/all-in should be available."""
        seats = _make_seats(2, chips=50000)
        pot = PotManager()
        br = BettingRound(seats=seats, pot_manager=pot, current_bet=0, min_raise=100)

        # Raise 4 times alternating between players
        actions = [
            PlayerAction("p0", BettingAction.RAISE, 200),
            PlayerAction("p1", BettingAction.RAISE, 400),
            PlayerAction("p0", BettingAction.RAISE, 800),
            PlayerAction("p1", BettingAction.RAISE, 1600),
        ]
        for a in actions:
            br.apply_action(a)

        # After 4 raises, RAISE should NOT be in valid actions
        p0_actions = br.get_valid_actions("p0")
        assert BettingAction.RAISE not in p0_actions
        assert BettingAction.FOLD in p0_actions
        assert BettingAction.CALL in p0_actions
        assert BettingAction.ALL_IN in p0_actions

    def test_three_raises_still_allows_fourth(self):
        """After 3 raises, a 4th raise is still allowed."""
        seats = _make_seats(2, chips=50000)
        pot = PotManager()
        br = BettingRound(seats=seats, pot_manager=pot, current_bet=0, min_raise=100)

        actions = [
            PlayerAction("p0", BettingAction.RAISE, 200),
            PlayerAction("p1", BettingAction.RAISE, 400),
            PlayerAction("p0", BettingAction.RAISE, 800),
        ]
        for a in actions:
            br.apply_action(a)

        p1_actions = br.get_valid_actions("p1")
        assert BettingAction.RAISE in p1_actions

    def test_heads_up_preflop_action_order(self):
        """In heads-up, both players get to act and the round completes."""
        seats = _make_seats(2, chips=5000)
        # Simulate preflop: p0 has SB=50, p1 has BB=100
        seats[0].current_bet = 50
        seats[0].chips = 4950
        seats[1].current_bet = 100
        seats[1].chips = 4900
        pot = PotManager()
        pot.add_bet("p0", 50)
        pot.add_bet("p1", 100)

        br = BettingRound(seats=seats, pot_manager=pot, current_bet=100, min_raise=100)

        # p0 should act first (SB in heads-up preflop)
        next_p = br.get_next_player_id()
        assert next_p == "p0"

        # p0 calls
        br.apply_action(PlayerAction("p0", BettingAction.CALL))

        # p1 should act next (BB option)
        next_p = br.get_next_player_id()
        assert next_p == "p1"

        # p1 checks
        br.apply_action(PlayerAction("p1", BettingAction.CHECK))

        # Round should be complete
        assert br.is_complete()
