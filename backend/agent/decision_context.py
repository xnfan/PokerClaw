"""Build decision context text from game state for LLM prompt."""
from __future__ import annotations

from typing import Any

from backend.engine.betting_round import BettingAction


class DecisionContextBuilder:
    """Transforms game_view dict into readable text for the LLM."""

    @staticmethod
    def build(
        game_view: dict[str, Any],
        valid_actions: list[BettingAction],
        history_summary: str = "",
    ) -> str:
        """Build human-readable context string for the LLM."""
        parts: list[str] = []

        # Player's own info
        my_info = None
        opponents: list[dict] = []
        for p in game_view.get("players", []):
            if p.get("hole_cards"):
                my_info = p
            else:
                opponents.append(p)

        if my_info:
            hole = ", ".join(my_info["hole_cards"])
            parts.append(f"## 你的手牌\n{hole}")
            parts.append(f"你的筹码: {my_info['chips']}")
            parts.append(f"你本轮已下注: {my_info['current_bet']}")

        # Community cards
        community = game_view.get("community_cards", [])
        if community:
            parts.append(f"\n## 公共牌\n{', '.join(community)}")
        else:
            parts.append("\n## 公共牌\n(尚未发出)")

        # Street and pot
        parts.append(f"\n当前阶段: {game_view.get('street', 'unknown')}")
        parts.append(f"底池: {game_view.get('pot', 0)}")

        # Pot odds (if there's a bet to call)
        if my_info:
            max_bet = max(
                (p.get("current_bet", 0) for p in game_view.get("players", [])),
                default=0,
            )
            to_call = max_bet - my_info.get("current_bet", 0)
            pot = game_view.get("pot", 0)
            if to_call > 0 and pot > 0:
                odds = round(to_call / (pot + to_call) * 100, 1)
                parts.append(f"需跟注: {to_call}, 底池赔率: {odds}%")

        # Opponents
        parts.append("\n## 对手")
        for opp in opponents:
            status = "活跃" if opp["is_active"] else "已弃牌"
            if opp["is_all_in"]:
                status = "全下"
            parts.append(
                f"- {opp['display_name']}: 筹码 {opp['chips']}, "
                f"本轮下注 {opp['current_bet']}, 状态: {status}"
            )

        # History summary (short-term memory)
        if history_summary:
            parts.append(f"\n## 你的近期表现\n{history_summary}")

        # Valid actions
        action_names = [a.value for a in valid_actions]
        parts.append(f"\n## 可用动作\n{', '.join(action_names)}")

        return "\n".join(parts)
