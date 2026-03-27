"""Tests for Deck."""
import pytest
from backend.engine.card import Card, Rank, Suit
from backend.engine.deck import Deck


class TestDeck:
    def test_deck_has_52_cards(self):
        d = Deck()
        assert d.remaining == 52

    def test_deck_no_duplicates(self):
        d = Deck()
        cards = d.deal(52)
        assert len(set(cards)) == 52

    def test_deal_reduces_count(self):
        d = Deck()
        d.deal(5)
        assert d.remaining == 47

    def test_deal_no_duplicate_across_deals(self):
        d = Deck(seed=42)
        d.shuffle()
        c1 = d.deal(5)
        c2 = d.deal(5)
        assert len(set(c1 + c2)) == 10

    def test_deal_from_empty_raises(self):
        d = Deck()
        d.deal(52)
        with pytest.raises(ValueError, match="Cannot deal"):
            d.deal(1)

    def test_shuffle_changes_order(self):
        d1 = Deck(seed=1)
        d2 = Deck(seed=2)
        d1.shuffle()
        d2.shuffle()
        c1 = d1.deal(5)
        c2 = d2.deal(5)
        assert c1 != c2  # different seeds produce different orders

    def test_seeded_deck_deterministic(self):
        d1 = Deck(seed=42)
        d1.shuffle()
        d2 = Deck(seed=42)
        d2.shuffle()
        assert d1.deal(10) == d2.deal(10)

    def test_remove_cards(self):
        d = Deck()
        ace_spades = Card(Rank.ACE, Suit.SPADES)
        d.remove_cards([ace_spades])
        assert d.remaining == 51
        all_dealt = d.deal(51)
        assert ace_spades not in all_dealt

    def test_reset(self):
        d = Deck()
        d.deal(10)
        d.reset()
        assert d.remaining == 52
