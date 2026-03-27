"""Tests for ActionParser."""
from backend.agent.action_parser import ActionParser
from backend.engine.betting_round import BettingAction


VALID_ALL = [
    BettingAction.FOLD, BettingAction.CHECK,
    BettingAction.CALL, BettingAction.RAISE,
]
VALID_NO_CHECK = [
    BettingAction.FOLD, BettingAction.CALL, BettingAction.RAISE,
]


class TestActionParser:
    def test_parse_fold(self):
        action = ActionParser.parse("ACTION: fold", VALID_ALL, "p1")
        assert action.action == BettingAction.FOLD

    def test_parse_call(self):
        action = ActionParser.parse("ACTION: call", VALID_ALL, "p1")
        assert action.action == BettingAction.CALL

    def test_parse_check(self):
        action = ActionParser.parse("ACTION: check", VALID_ALL, "p1")
        assert action.action == BettingAction.CHECK

    def test_parse_raise_with_amount(self):
        action = ActionParser.parse(
            "THINKING: blah\nACTION: raise\nAMOUNT: 200", VALID_ALL, "p1"
        )
        assert action.action == BettingAction.RAISE
        assert action.amount == 200

    def test_parse_allin(self):
        valid = VALID_ALL + [BettingAction.ALL_IN]
        action = ActionParser.parse("ACTION: all_in", valid, "p1")
        assert action.action == BettingAction.ALL_IN

    def test_parse_invalid_fallback_check(self):
        """Unparseable text falls back to check when available."""
        action = ActionParser.parse("I don't know what to do", VALID_ALL, "p1")
        assert action.action == BettingAction.CHECK

    def test_parse_invalid_fallback_fold(self):
        """Unparseable text falls back to fold when no check."""
        action = ActionParser.parse("gibberish", VALID_NO_CHECK, "p1")
        assert action.action == BettingAction.FOLD

    def test_invalid_action_not_in_valid_list(self):
        """If parsed action is not in valid list, fallback."""
        action = ActionParser.parse("ACTION: check", VALID_NO_CHECK, "p1")
        assert action.action == BettingAction.FOLD

    def test_extract_thinking(self):
        text = "THINKING: I have a strong hand\nACTION: raise\nAMOUNT: 300"
        thinking = ActionParser.extract_thinking(text)
        assert "strong hand" in thinking

    def test_extract_thinking_no_tag(self):
        text = "Let me analyze this hand carefully.\nACTION: call"
        thinking = ActionParser.extract_thinking(text)
        assert "analyze" in thinking
