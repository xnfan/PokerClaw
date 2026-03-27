"""Tests for HandEvaluator - all 10 hand ranks + comparisons."""
from backend.engine.card import Card, Rank, Suit
from backend.engine.hand_evaluator import HandEvaluator, HandRank


def c(s: str) -> Card:
    return Card.from_string(s)


class TestHandRanks:
    def test_royal_flush(self):
        cards = [c("As"), c("Ks"), c("Qs"), c("Js"), c("Ts")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.ROYAL_FLUSH

    def test_straight_flush(self):
        cards = [c("9h"), c("8h"), c("7h"), c("6h"), c("5h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.STRAIGHT_FLUSH

    def test_four_of_a_kind(self):
        cards = [c("Kh"), c("Kd"), c("Kc"), c("Ks"), c("2h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.FOUR_OF_A_KIND

    def test_full_house(self):
        cards = [c("Jh"), c("Jd"), c("Jc"), c("4s"), c("4h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.FULL_HOUSE

    def test_flush(self):
        cards = [c("Ah"), c("Jh"), c("9h"), c("6h"), c("3h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.FLUSH

    def test_straight(self):
        cards = [c("Ts"), c("9h"), c("8d"), c("7c"), c("6s")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.STRAIGHT

    def test_straight_ace_low(self):
        cards = [c("As"), c("2h"), c("3d"), c("4c"), c("5s")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.STRAIGHT
        assert score.tie_breakers == (Rank.FIVE,)

    def test_three_of_a_kind(self):
        cards = [c("7h"), c("7d"), c("7c"), c("Ks"), c("3h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.THREE_OF_A_KIND

    def test_two_pair(self):
        cards = [c("Ah"), c("Ad"), c("Kc"), c("Ks"), c("3h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.TWO_PAIR

    def test_one_pair(self):
        cards = [c("Qh"), c("Qd"), c("9c"), c("6s"), c("3h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.ONE_PAIR

    def test_high_card(self):
        cards = [c("Ah"), c("Jd"), c("9c"), c("6s"), c("3h")]
        score = HandEvaluator.best_five(cards)
        assert score.hand_rank == HandRank.HIGH_CARD


class TestComparisons:
    def test_flush_beats_straight(self):
        flush = HandEvaluator.best_five([c("Ah"), c("Jh"), c("9h"), c("6h"), c("3h")])
        straight = HandEvaluator.best_five([c("Ts"), c("9h"), c("8d"), c("7c"), c("6s")])
        assert flush > straight

    def test_higher_pair_wins(self):
        aa = HandEvaluator.best_five([c("Ah"), c("Ad"), c("9c"), c("6s"), c("3h")])
        kk = HandEvaluator.best_five([c("Kh"), c("Kd"), c("9c"), c("6s"), c("3h")])
        assert aa > kk

    def test_kicker_comparison(self):
        ak = HandEvaluator.best_five([c("Ah"), c("Ad"), c("Kc"), c("6s"), c("3h")])
        aq = HandEvaluator.best_five([c("Ah"), c("Ad"), c("Qc"), c("6s"), c("3h")])
        assert ak > aq

    def test_split_pot_same_hand(self):
        h1 = HandEvaluator.best_five([c("Ah"), c("Kd"), c("Qc"), c("Js"), c("9h")])
        h2 = HandEvaluator.best_five([c("As"), c("Kc"), c("Qh"), c("Jd"), c("9s")])
        assert h1 == h2

    def test_full_house_comparison(self):
        jjj44 = HandEvaluator.best_five([c("Jh"), c("Jd"), c("Jc"), c("4s"), c("4h")])
        ttt99 = HandEvaluator.best_five([c("Th"), c("Td"), c("Tc"), c("9s"), c("9h")])
        assert jjj44 > ttt99


class TestSevenCards:
    def test_best_five_from_seven(self):
        hole = [c("As"), c("Ks")]
        community = [c("Qs"), c("Js"), c("Ts"), c("2h"), c("3d")]
        score = HandEvaluator.evaluate(hole, community)
        assert score.hand_rank == HandRank.ROYAL_FLUSH

    def test_community_plays(self):
        """When the board is the best hand."""
        hole = [c("2h"), c("3d")]
        community = [c("As"), c("Ks"), c("Qs"), c("Js"), c("Ts")]
        score = HandEvaluator.evaluate(hole, community)
        assert score.hand_rank == HandRank.ROYAL_FLUSH
