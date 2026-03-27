"""Tests for LLMAgent including timeout and monitoring."""
import asyncio
import pytest
from backend.agent.llm_agent import LLMAgent
from backend.agent.personality import PersonalityProfile, PlayStyle, SkillLevel
from backend.engine.betting_round import BettingAction
from backend.llm.base_provider import LLMCallResult
from backend.llm.mock_provider import MockLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor


def _make_agent(
    style="passive", fail_rate=0.0, delay_ms=5.0, timeout=30.0
) -> tuple[LLMAgent, AgentMonitor]:
    monitor = AgentMonitor()
    provider = MockLLMProvider(style=style, delay_ms=delay_ms, fail_rate=fail_rate)
    personality = PersonalityProfile(SkillLevel.EXPERT, PlayStyle.TAG)
    agent = LLMAgent(
        agent_id="test_agent",
        display_name="Test",
        personality=personality,
        llm_provider=provider,
        monitor=monitor,
        decision_timeout=timeout,
    )
    return agent, monitor


GAME_VIEW = {
    "hand_id": "h1",
    "street": "flop",
    "community_cards": ["Ah", "Kd", "Qc"],
    "pot": 500,
    "players": [
        {
            "player_id": "test_agent", "display_name": "Test",
            "chips": 5000, "is_active": True, "is_all_in": False,
            "current_bet": 100, "total_bet": 100, "seat_index": 0,
            "hole_cards": ["Js", "Ts"],
        },
        {
            "player_id": "opp", "display_name": "Opponent",
            "chips": 5000, "is_active": True, "is_all_in": False,
            "current_bet": 100, "total_bet": 100, "seat_index": 1,
            "hole_cards": [],
        },
    ],
    "small_blind": 50, "big_blind": 100, "dealer_index": 0,
}

VALID = [BettingAction.FOLD, BettingAction.CHECK, BettingAction.CALL, BettingAction.RAISE]


@pytest.mark.asyncio
class TestLLMAgent:
    async def test_decide_returns_action(self):
        agent, _ = _make_agent()
        action, metadata = await agent.decide(GAME_VIEW, VALID)
        assert action.action in VALID
        assert action.player_id == "test_agent"

    async def test_decide_records_thinking(self):
        agent, _ = _make_agent()
        _, metadata = await agent.decide(GAME_VIEW, VALID)
        assert metadata["thinking"]  # non-empty

    async def test_decide_records_metrics(self):
        agent, monitor = _make_agent()
        _, metadata = await agent.decide(GAME_VIEW, VALID)
        assert metadata["input_tokens"] > 0
        assert metadata["llm_latency_ms"] > 0
        assert metadata["decision_ms"] > 0
        # Monitor should have records
        assert len(monitor.decisions) == 1
        assert monitor.decisions[0].decision_status == "success"

    async def test_timeout_auto_folds(self):
        """Agent that exceeds timeout falls back to check/fold."""
        agent, monitor = _make_agent(delay_ms=100, timeout=0.01)
        action, metadata = await agent.decide(GAME_VIEW, VALID)
        assert metadata["is_timeout"] is True
        assert action.action in (BettingAction.CHECK, BettingAction.FOLD)
        assert monitor.decisions[0].decision_status == "timeout"

    async def test_timeout_prefers_check(self):
        agent, _ = _make_agent(delay_ms=100, timeout=0.01)
        action, _ = await agent.decide(GAME_VIEW, VALID)
        assert action.action == BettingAction.CHECK  # check available

    async def test_timeout_folds_when_no_check(self):
        agent, _ = _make_agent(delay_ms=100, timeout=0.01)
        valid_no_check = [BettingAction.FOLD, BettingAction.CALL]
        action, _ = await agent.decide(GAME_VIEW, valid_no_check)
        assert action.action == BettingAction.FOLD

    async def test_error_retry_and_fallback(self):
        """On LLM error, retries once then falls back."""
        agent, monitor = _make_agent(fail_rate=1.0)  # always fail
        action, metadata = await agent.decide(GAME_VIEW, VALID)
        assert metadata["is_fallback"] is True
        # Should have 2 LLM calls (original + 1 retry)
        llm_calls = monitor.llm_metrics.get_by_agent("test_agent")
        assert len(llm_calls) == 2
        assert llm_calls[1].is_retry is True

    async def test_successful_decision_recorded(self):
        agent, monitor = _make_agent()
        await agent.decide(GAME_VIEW, VALID)
        assert len(monitor.decisions) == 1
        assert monitor.decisions[0].decision_status == "success"
        assert len(monitor.llm_metrics.records) >= 1
