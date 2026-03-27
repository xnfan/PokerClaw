"""Tests for PotManager."""
from backend.engine.hand_evaluator import HandRank, HandScore
from backend.engine.pot_manager import PotManager


class TestPotManager:
    def test_simple_pot(self):
        pm = PotManager()
        pm.add_bet("p1", 100)
        pm.add_bet("p2", 100)
        assert pm.total_pot == 200

    def test_side_pot_single_allin(self):
        pm = PotManager()
        pm.add_bet("p1", 100)
        pm.mark_all_in("p1")
        pm.add_bet("p2", 500)
        pm.add_bet("p3", 500)
        pots = pm.build_pots({"p1", "p2", "p3"})
        assert len(pots) >= 2
        assert sum(p.amount for p in pots) == 1100

    def test_distribution_single_winner(self):
        pm = PotManager()
        pm.add_bet("p1", 200)
        pm.add_bet("p2", 200)
        scores = {
            "p1": HandScore(HandRank.ONE_PAIR, (14, 13, 12, 11)),
            "p2": HandScore(HandRank.HIGH_CARD, (14, 13, 12, 11, 10)),
        }
        winnings = pm.distribute_winnings(scores, {"p1", "p2"})
        assert winnings["p1"] == 400
        assert winnings.get("p2", 0) == 0

    def test_distribution_split_pot(self):
        pm = PotManager()
        pm.add_bet("p1", 200)
        pm.add_bet("p2", 200)
        score = HandScore(HandRank.ONE_PAIR, (14, 13, 12, 11))
        winnings = pm.distribute_winnings(
            {"p1": score, "p2": score}, {"p1", "p2"}
        )
        assert winnings["p1"] == 200
        assert winnings["p2"] == 200

    def test_three_way_allin(self):
        pm = PotManager()
        pm.add_bet("p1", 100)
        pm.mark_all_in("p1")
        pm.add_bet("p2", 300)
        pm.mark_all_in("p2")
        pm.add_bet("p3", 500)
        pots = pm.build_pots({"p1", "p2", "p3"})
        total = sum(p.amount for p in pots)
        assert total == 900

    def test_reset(self):
        pm = PotManager()
        pm.add_bet("p1", 100)
        pm.reset()
        assert pm.total_pot == 0
