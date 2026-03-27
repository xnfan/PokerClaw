"""Parse LLM text output into a valid game action."""
from __future__ import annotations

import re

from backend.engine.betting_round import BettingAction, PlayerAction


class ActionParser:
    """Extract structured action from LLM free-text response."""

    # Patterns to match action lines
    _ACTION_RE = re.compile(
        r"ACTION:\s*(fold|check|call|raise|all_in|all-in|allin)",
        re.IGNORECASE,
    )
    _AMOUNT_RE = re.compile(r"AMOUNT:\s*(\d+)", re.IGNORECASE)

    @staticmethod
    def parse(
        llm_text: str,
        valid_actions: list[BettingAction],
        player_id: str,
    ) -> PlayerAction:
        """Parse LLM output into a PlayerAction.

        Falls back to check (if available) or fold on parse failure.
        """
        action_match = ActionParser._ACTION_RE.search(llm_text)
        if not action_match:
            return ActionParser._fallback(valid_actions, player_id)

        raw_action = action_match.group(1).lower().replace("-", "_")
        action_map = {
            "fold": BettingAction.FOLD,
            "check": BettingAction.CHECK,
            "call": BettingAction.CALL,
            "raise": BettingAction.RAISE,
            "all_in": BettingAction.ALL_IN,
            "allin": BettingAction.ALL_IN,
        }
        action = action_map.get(raw_action)
        if action is None or action not in valid_actions:
            return ActionParser._fallback(valid_actions, player_id)

        amount = 0
        if action == BettingAction.RAISE:
            amount_match = ActionParser._AMOUNT_RE.search(llm_text)
            if amount_match:
                amount = int(amount_match.group(1))

        return PlayerAction(player_id=player_id, action=action, amount=amount)

    @staticmethod
    def extract_thinking(llm_text: str) -> str:
        """Extract the THINKING section from LLM output."""
        match = re.search(
            r"THINKING:\s*(.+?)(?=\nACTION:|\Z)",
            llm_text,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        # If no THINKING tag, return everything before ACTION as thinking
        action_pos = llm_text.upper().find("ACTION:")
        if action_pos > 0:
            return llm_text[:action_pos].strip()
        return llm_text.strip()

    @staticmethod
    def _fallback(
        valid_actions: list[BettingAction], player_id: str
    ) -> PlayerAction:
        """Fallback: check if possible, else fold."""
        if BettingAction.CHECK in valid_actions:
            return PlayerAction(player_id=player_id, action=BettingAction.CHECK)
        return PlayerAction(player_id=player_id, action=BettingAction.FOLD)
