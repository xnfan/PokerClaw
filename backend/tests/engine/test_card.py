"""Tests for Card, Rank, Suit."""
import pytest
from backend.engine.card import Card, Rank, Suit


class TestCard:
    def test_card_creation(self):
        c = Card(Rank.ACE, Suit.SPADES)
        assert c.rank == Rank.ACE
        assert c.suit == Suit.SPADES

    def test_card_str(self):
        assert str(Card(Rank.ACE, Suit.HEARTS)) == "Ah"
        assert str(Card(Rank.TEN, Suit.DIAMONDS)) == "Td"
        assert str(Card(Rank.TWO, Suit.CLUBS)) == "2c"
        assert str(Card(Rank.KING, Suit.SPADES)) == "Ks"

    def test_card_from_string(self):
        c = Card.from_string("Ah")
        assert c.rank == Rank.ACE and c.suit == Suit.HEARTS
        c2 = Card.from_string("Td")
        assert c2.rank == Rank.TEN and c2.suit == Suit.DIAMONDS

    def test_card_from_string_case_insensitive(self):
        c = Card.from_string("aH")
        assert c.rank == Rank.ACE and c.suit == Suit.HEARTS

    def test_card_from_string_invalid(self):
        with pytest.raises(ValueError):
            Card.from_string("XX")
        with pytest.raises(ValueError):
            Card.from_string("A")
        with pytest.raises(ValueError):
            Card.from_string("Ax")

    def test_card_equality(self):
        assert Card(Rank.ACE, Suit.SPADES) == Card(Rank.ACE, Suit.SPADES)
        assert Card(Rank.ACE, Suit.SPADES) != Card(Rank.ACE, Suit.HEARTS)

    def test_card_frozen(self):
        c = Card(Rank.ACE, Suit.SPADES)
        with pytest.raises(AttributeError):
            c.rank = Rank.KING  # type: ignore

    def test_card_hashable(self):
        """Cards can be used in sets and as dict keys."""
        s = {Card(Rank.ACE, Suit.SPADES), Card(Rank.ACE, Suit.SPADES)}
        assert len(s) == 1
