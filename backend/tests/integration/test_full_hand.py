"""Integration test: run a full hand with mock agents."""
import pytest
from backend.agent.llm_agent import LLMAgent
from backend.agent.personality import PersonalityProfile, PlayStyle, SkillLevel
from backend.engine.cash_game import CashGame, CashGameConfig
from backend.llm.mock_provider import MockLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor
from backend.monitoring.metrics_aggregator import MetricsAggregator


def _create_game(num_players=4, num_hands=3) -> tuple[CashGame, AgentMonitor]:
    monitor = AgentMonitor()
    config = CashGameConfig(small_blind=50, big_blind=100)
    game = CashGame(config)

    configs = [
        ("p1", "Player1", SkillLevel.EXPERT, PlayStyle.TAG, "aggressive"),
        ("p2", "Player2", SkillLevel.NOVICE, PlayStyle.FISH, "random"),
        ("p3", "Player3", SkillLevel.INTERMEDIATE, PlayStyle.CALLING_STATION, "passive"),
        ("p4", "Player4", SkillLevel.EXPERT, PlayStyle.LAG, "aggressive"),
    ]
    for i in range(num_players):
        aid, name, skill, style, mock = configs[i]
        provider = MockLLMProvider(style=mock, delay_ms=5)
        agent = LLMAgent(
            agent_id=aid, display_name=name,
            personality=PersonalityProfile(skill, style),
            llm_provider=provider, monitor=monitor,
        )
        game.add_player(aid, name, agent, buy_in=5000)

    return game, monitor


@pytest.mark.asyncio
class TestFullHand:
    async def test_complete_session(self):
        """Run 3 hands, verify basic correctness."""
        game, monitor = _create_game(num_players=4)
        result = await game.run(3)
        assert result.total_hands == 3
        assert len(result.hand_results) == 3
        # Total chips should be conserved
        total = sum(result.final_chips.values())
        assert total == 20000  # 4 * 5000

    async def test_hands_have_actions(self):
        game, _ = _create_game(num_players=3)
        result = await game.run(2)
        for hand in result.hand_results:
            assert len(hand.action_history) > 0

    async def test_monitoring_records(self):
        """Monitoring should have records after a session."""
        game, monitor = _create_game(num_players=3)
        await game.run(3)
        assert len(monitor.decisions) > 0
        assert len(monitor.llm_metrics.records) > 0
        # All decisions should be successful (no real API failures)
        for d in monitor.decisions:
            assert d.decision_status == "success"

    async def test_monitoring_aggregation(self):
        game, monitor = _create_game(num_players=3)
        await game.run(5)
        agg = MetricsAggregator(monitor)
        for pid in ["p1", "p2", "p3"]:
            summary = agg.get_agent_summary(pid)
            assert summary.total_decisions > 0
            assert summary.success_rate == 1.0
            assert summary.total_tokens > 0

    async def test_heads_up(self):
        """2-player heads-up game works."""
        game, _ = _create_game(num_players=2)
        result = await game.run(3)
        assert result.total_hands == 3
        total = sum(result.final_chips.values())
        assert total == 10000

    async def test_chips_conserved_per_hand(self):
        """Chips are conserved in each hand."""
        game, _ = _create_game(num_players=4)
        result = await game.run(5)
        for hand in result.hand_results:
            total = sum(hand.final_chips.values())
            assert total == 20000
