"""Tests for Monte Carlo equity calculator."""
import pytest
from backend.engine.card import Card
from backend.engine.equity import EquityCalculator


class TestEquityCalculator:
    def test_aa_vs_kk_preflop(self):
        """AA should beat KK roughly 80% of the time preflop."""
        aa = [Card.from_string("Ah"), Card.from_string("Ad")]
        kk = [Card.from_string("Kh"), Card.from_string("Kd")]
        results = EquityCalculator.calculate([aa, kk], num_simulations=10000, seed=42)
        assert len(results) == 2
        # AA should win ~80% (+/- margin)
        assert results[0].win_pct > 0.75
        assert results[0].win_pct < 0.90
        assert results[1].win_pct > 0.10
        assert results[1].win_pct < 0.25

    def test_full_board_deterministic(self):
        """With all 5 community cards, result is deterministic."""
        hero = [Card.from_string("Ah"), Card.from_string("Kh")]
        villain = [Card.from_string("2c"), Card.from_string("7d")]
        community = [
            Card.from_string("Th"), Card.from_string("Jh"), Card.from_string("Qh"),
            Card.from_string("3s"), Card.from_string("4s"),
        ]
        # Hero has a royal flush draw completed — Ah Kh Th Jh Qh
        results = EquityCalculator.calculate([hero, villain], community=community)
        assert results[0].win_pct == 1.0
        assert results[0].sample_count == 1
        assert results[1].lose_pct == 1.0

    def test_identical_hands_tie(self):
        """Two players with effectively same hand should tie most of the time."""
        p1 = [Card.from_string("Ah"), Card.from_string("Kd")]
        p2 = [Card.from_string("As"), Card.from_string("Kc")]
        results = EquityCalculator.calculate([p1, p2], num_simulations=5000, seed=42)
        # Should tie very often (flush possibilities make it not 100%)
        assert results[0].tie_pct > 0.5

    def test_duplicate_cards_raises(self):
        """Duplicate cards should raise ValueError."""
        same = [Card.from_string("Ah"), Card.from_string("Kd")]
        with pytest.raises(ValueError, match="Duplicate"):
            EquityCalculator.calculate([same, same])

    def test_duplicate_with_community_raises(self):
        """Card appearing in both hand and community should raise."""
        hero = [Card.from_string("Ah"), Card.from_string("Kd")]
        villain = [Card.from_string("Qc"), Card.from_string("Js")]
        community = [Card.from_string("Ah")]  # duplicate with hero
        with pytest.raises(ValueError, match="Duplicate"):
            EquityCalculator.calculate([hero, villain], community=community)

    def test_single_player_raises(self):
        """Need at least 2 players."""
        hero = [Card.from_string("Ah"), Card.from_string("Kd")]
        with pytest.raises(ValueError, match="2 players"):
            EquityCalculator.calculate([hero])

    def test_wrong_card_count_raises(self):
        """Each player must have exactly 2 cards."""
        p1 = [Card.from_string("Ah")]
        p2 = [Card.from_string("Kd"), Card.from_string("Qc")]
        with pytest.raises(ValueError, match="2 hole cards"):
            EquityCalculator.calculate([p1, p2])

    def test_three_players(self):
        """Equity calculation works with 3+ players."""
        p1 = [Card.from_string("Ah"), Card.from_string("Ad")]
        p2 = [Card.from_string("Kh"), Card.from_string("Kd")]
        p3 = [Card.from_string("Qh"), Card.from_string("Qd")]
        results = EquityCalculator.calculate([p1, p2, p3], num_simulations=5000, seed=42)
        assert len(results) == 3
        # AA should have highest equity
        assert results[0].win_pct > results[1].win_pct
        assert results[0].win_pct > results[2].win_pct
        # All percentages should sum to ~1 per player
        for r in results:
            total = r.win_pct + r.tie_pct + r.lose_pct
            assert abs(total - 1.0) < 0.01

    def test_seeded_reproducible(self):
        """Same seed produces same results."""
        p1 = [Card.from_string("Ah"), Card.from_string("Kh")]
        p2 = [Card.from_string("Qs"), Card.from_string("Jd")]
        r1 = EquityCalculator.calculate([p1, p2], num_simulations=1000, seed=123)
        r2 = EquityCalculator.calculate([p1, p2], num_simulations=1000, seed=123)
        assert r1[0].win_pct == r2[0].win_pct
        assert r1[1].win_pct == r2[1].win_pct
