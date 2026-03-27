"""Minimal CLI prototype: run a cash game session with mock agents.

Usage:
    cd PokerClaw
    python -m scripts.run_cli_game [--hands N] [--players N]
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agent.llm_agent import LLMAgent
from backend.agent.personality import PersonalityProfile, PlayStyle, SkillLevel
from backend.engine.cash_game import CashGame, CashGameConfig
from backend.engine.game_runner import HandResult
from backend.llm.mock_provider import MockLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor
from backend.monitoring.llm_metrics import LLMMetricsCollector
from backend.monitoring.metrics_aggregator import MetricsAggregator


# Agent configs for demo
AGENT_CONFIGS = [
    ("alice", "Alice (TAG高手)", SkillLevel.EXPERT, PlayStyle.TAG, "aggressive"),
    ("bob", "Bob (LAG高手)", SkillLevel.EXPERT, PlayStyle.LAG, "aggressive"),
    ("charlie", "Charlie (鱼)", SkillLevel.NOVICE, PlayStyle.FISH, "random"),
    ("diana", "Diana (跟注站)", SkillLevel.INTERMEDIATE, PlayStyle.CALLING_STATION, "passive"),
]


def print_hand_result(result: HandResult, hand_num: int) -> None:
    """Pretty-print a hand result."""
    print(f"\n{'='*60}")
    print(f"  Hand #{hand_num}  (ID: {result.hand_id})")
    print(f"{'='*60}")

    # Community cards
    community = " ".join(str(c) for c in result.community_cards)
    print(f"  Board: {community or '(no showdown)'}")

    # Actions summary
    for action in result.action_history:
        timeout_mark = " [TIMEOUT]" if action.is_timeout else ""
        fallback_mark = " [FALLBACK]" if action.is_fallback else ""
        tokens = ""
        if action.input_tokens > 0:
            tokens = f" (tokens: {action.input_tokens}+{action.output_tokens}, {action.llm_latency_ms:.0f}ms)"
        print(
            f"  [{action.street:8s}] {action.player_id:10s}: "
            f"{action.action:6s} {action.amount:>5d}{timeout_mark}{fallback_mark}{tokens}"
        )
        if action.thinking:
            short = action.thinking[:80].replace("\n", " ")
            print(f"             思考: {short}")

    # Winners
    print(f"\n  Winners:")
    for pid, amount in result.winners.items():
        hand_str = str(result.player_hands.get(pid, ""))
        print(f"    {pid}: +{amount} chips  ({hand_str})")

    # Final chips
    print(f"  Final chips: ", end="")
    chips_str = ", ".join(f"{pid}={c}" for pid, c in result.final_chips.items())
    print(chips_str)


async def run_session(num_hands: int, num_players: int) -> None:
    """Run a demo cash game session."""
    # Setup monitoring
    llm_metrics = LLMMetricsCollector()
    monitor = AgentMonitor(llm_metrics)
    aggregator = MetricsAggregator(monitor)

    # Create game
    config = CashGameConfig(small_blind=50, big_blind=100)
    game = CashGame(config)

    # Create agents
    for i in range(min(num_players, len(AGENT_CONFIGS))):
        aid, name, skill, style, mock_style = AGENT_CONFIGS[i]
        personality = PersonalityProfile(skill_level=skill, play_style=style)
        provider = MockLLMProvider(style=mock_style, delay_ms=10)
        agent = LLMAgent(
            agent_id=aid,
            display_name=name,
            personality=personality,
            llm_provider=provider,
            monitor=monitor,
        )
        game.add_player(aid, name, agent, buy_in=5000)

    print(f"\n{'#'*60}")
    print(f"  PokerClaw CLI - Cash Game Session")
    print(f"  Players: {num_players}, Hands: {num_hands}")
    print(f"  Blinds: {config.small_blind}/{config.big_blind}")
    print(f"{'#'*60}")

    hand_num = 0

    async def on_hand_complete(result: HandResult) -> None:
        nonlocal hand_num
        hand_num += 1
        print_hand_result(result, hand_num)

    result = await game.run(num_hands, on_hand_complete=on_hand_complete)

    # Print session summary
    print(f"\n{'='*60}")
    print(f"  SESSION SUMMARY")
    print(f"{'='*60}")
    print(f"  Total hands: {result.total_hands}")
    print(f"  Final chips:")
    for pid, chips in result.final_chips.items():
        print(f"    {pid}: {chips}")

    # Print monitoring summary
    print(f"\n  --- Monitoring ---")
    for aid, _, _, _, _ in AGENT_CONFIGS[:num_players]:
        summary = aggregator.get_agent_summary(aid)
        print(
            f"  {aid}: decisions={summary.total_decisions}, "
            f"success_rate={summary.success_rate:.1%}, "
            f"timeouts={summary.timeout_count}, "
            f"tokens={summary.total_tokens}, "
            f"avg_latency={summary.avg_latency_ms:.0f}ms"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="PokerClaw CLI Game")
    parser.add_argument("--hands", type=int, default=5, help="Number of hands")
    parser.add_argument("--players", type=int, default=4, help="Number of players (2-4)")
    args = parser.parse_args()
    asyncio.run(run_session(args.hands, args.players))


if __name__ == "__main__":
    main()
