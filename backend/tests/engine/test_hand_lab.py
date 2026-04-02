"""Tests for Hand Lab scenario testing."""
import pytest
import pytest_asyncio
from backend.services.hand_lab import HandLab, PlayerSetup, ScenarioConfig
from backend.engine.card import Card
from backend.engine.game_runner import GameRunner
from backend.engine.game_state import PlayerState
from backend.agent.llm_agent import LLMAgent
from backend.agent.personality import PersonalityProfile, PlayStyle, SkillLevel
from backend.llm.mock_provider import MockLLMProvider
from backend.monitoring.agent_monitor import AgentMonitor


def _make_agent(agent_id: str, display_name: str) -> LLMAgent:
    """Create a mock agent for testing (bypasses DB)."""
    personality = PersonalityProfile(SkillLevel.INTERMEDIATE, PlayStyle.TAG, "")
    provider = MockLLMProvider(style="passive", delay_ms=5)
    return LLMAgent(
        agent_id=agent_id,
        display_name=display_name,
        personality=personality,
        llm_provider=provider,
        monitor=AgentMonitor(),
    )


class TestGameRunnerPresetCards:
    """Test that GameRunner properly handles preset hole cards and community cards."""

    @pytest.mark.asyncio
    async def test_preset_hole_cards_used(self):
        """Players with preset hole cards should keep them."""
        preset = [Card.from_string("Ah"), Card.from_string("Kh")]
        p1 = PlayerState(player_id="p1", display_name="Alice", chips=5000, hole_cards=preset)
        p2 = PlayerState(player_id="p2", display_name="Bob", chips=5000)
        agents = {"p1": _make_agent("p1", "Alice"), "p2": _make_agent("p2", "Bob")}

        runner = GameRunner(players=[p1, p2], agents=agents)
        runner.deck.remove_cards(preset)
        result = await runner.run_hand()

        # p1 should have the preset cards
        p1_cards = result.player_cards["p1"]
        assert Card.from_string("Ah") in p1_cards
        assert Card.from_string("Kh") in p1_cards
        # p2 should have been dealt random cards
        assert len(result.player_cards["p2"]) == 2

    @pytest.mark.asyncio
    async def test_preset_community_cards_used(self):
        """Preset community cards should appear in the result."""
        preset_community = [
            Card.from_string("Ts"), Card.from_string("Js"), Card.from_string("Qs"),
        ]
        p1 = PlayerState(player_id="p1", display_name="Alice", chips=5000)
        p2 = PlayerState(player_id="p2", display_name="Bob", chips=5000)
        agents = {"p1": _make_agent("p1", "Alice"), "p2": _make_agent("p2", "Bob")}

        runner = GameRunner(players=[p1, p2], agents=agents)
        runner.deck.remove_cards(preset_community)
        runner.state.community_cards = list(preset_community)
        result = await runner.run_hand()

        # First 3 community cards should match preset
        assert result.community_cards[0] == Card.from_string("Ts")
        assert result.community_cards[1] == Card.from_string("Js")
        assert result.community_cards[2] == Card.from_string("Qs")
        # Should still have 5 total community cards
        assert len(result.community_cards) == 5

    @pytest.mark.asyncio
    async def test_normal_game_still_works(self):
        """GameRunner without preset cards should work as before."""
        p1 = PlayerState(player_id="p1", display_name="Alice", chips=5000)
        p2 = PlayerState(player_id="p2", display_name="Bob", chips=5000)
        agents = {"p1": _make_agent("p1", "Alice"), "p2": _make_agent("p2", "Bob")}

        runner = GameRunner(players=[p1, p2], agents=agents, deck_seed=42)
        result = await runner.run_hand()

        assert len(result.player_cards["p1"]) == 2
        assert len(result.player_cards["p2"]) == 2
        assert len(result.community_cards) == 5
        # Chips conserved
        total = sum(result.final_chips.values())
        assert total == 10000

    @pytest.mark.asyncio
    async def test_chips_conserved_with_preset(self):
        """Total chips should be conserved even with preset cards."""
        preset = [Card.from_string("Ah"), Card.from_string("Ad")]
        p1 = PlayerState(player_id="p1", display_name="Alice", chips=5000, hole_cards=preset)
        p2 = PlayerState(player_id="p2", display_name="Bob", chips=5000)
        agents = {"p1": _make_agent("p1", "Alice"), "p2": _make_agent("p2", "Bob")}

        runner = GameRunner(players=[p1, p2], agents=agents)
        runner.deck.remove_cards(preset)
        result = await runner.run_hand()

        total = sum(result.final_chips.values())
        assert total == 10000


class TestHandLabValidation:
    def test_duplicate_cards_raises(self):
        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", hole_cards=["Ah", "Kd"]),
                PlayerSetup(agent_id="a2", hole_cards=["Ah", "Qc"]),  # duplicate Ah
            ],
        )
        with pytest.raises(ValueError, match="Duplicate"):
            HandLab(config)

    def test_too_few_players_raises(self):
        config = ScenarioConfig(
            players=[PlayerSetup(agent_id="a1", hole_cards=["Ah", "Kd"])],
        )
        with pytest.raises(ValueError, match="2 players"):
            HandLab(config)

    def test_wrong_hole_card_count_raises(self):
        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", hole_cards=["Ah"]),  # only 1 card
                PlayerSetup(agent_id="a2", hole_cards=["Kd", "Qc"]),
            ],
        )
        with pytest.raises(ValueError, match="0 or 2"):
            HandLab(config)

    def test_too_many_community_raises(self):
        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", hole_cards=["Ah", "Kd"]),
                PlayerSetup(agent_id="a2", hole_cards=["Qs", "Qc"]),
            ],
            community_cards=["2h", "3h", "4h", "5h", "6h", "7h"],  # 6 cards
        )
        with pytest.raises(ValueError, match="exceed 5"):
            HandLab(config)

    def test_valid_config_passes(self):
        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", hole_cards=["Ah", "Kd"]),
                PlayerSetup(agent_id="a2", hole_cards=["Qs", "Qc"]),
            ],
            community_cards=["Ts", "Js", "2d"],
        )
        lab = HandLab(config)
        assert lab is not None
