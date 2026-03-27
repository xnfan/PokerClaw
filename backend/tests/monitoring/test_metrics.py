"""Tests for monitoring: LLM metrics, agent monitor, and aggregator."""
import time
import pytest
from backend.llm.base_provider import LLMCallResult
from backend.monitoring.agent_monitor import AgentMonitor
from backend.monitoring.llm_metrics import LLMMetricsCollector
from backend.monitoring.metrics_aggregator import MetricsAggregator


def _make_llm_result(
    status="success", tokens=100, latency=50.0, provider="mock"
) -> LLMCallResult:
    return LLMCallResult(
        text="ACTION: call",
        input_tokens=tokens,
        output_tokens=tokens // 2,
        total_tokens=tokens + tokens // 2,
        latency_ms=latency,
        status=status,
        provider_name=provider,
        model_name=f"{provider}-v1",
    )


class TestLLMMetricsCollector:
    def test_record_and_retrieve(self):
        collector = LLMMetricsCollector()
        result = _make_llm_result()
        collector.record("agent1", result, hand_id="h1")
        records = collector.get_by_agent("agent1")
        assert len(records) == 1
        assert records[0].input_tokens == 100

    def test_get_by_hand(self):
        collector = LLMMetricsCollector()
        collector.record("a1", _make_llm_result(), hand_id="h1")
        collector.record("a1", _make_llm_result(), hand_id="h2")
        assert len(collector.get_by_hand("h1")) == 1

    def test_get_by_session(self):
        collector = LLMMetricsCollector()
        collector.record("a1", _make_llm_result(), session_id="s1")
        collector.record("a2", _make_llm_result(), session_id="s1")
        assert len(collector.get_by_session("s1")) == 2

    def test_retry_flag(self):
        collector = LLMMetricsCollector()
        collector.record("a1", _make_llm_result(), is_retry=True)
        assert collector.records[0].is_retry is True


class TestAgentMonitor:
    def test_record_decision_success(self):
        monitor = AgentMonitor()
        start = time.monotonic()
        rec = monitor.record_decision("a1", "success", start)
        assert rec.decision_status == "success"
        assert rec.total_decision_ms >= 0

    def test_record_decision_timeout(self):
        monitor = AgentMonitor()
        start = time.monotonic()
        rec = monitor.record_decision("a1", "timeout", start)
        assert rec.decision_status == "timeout"

    def test_delegates_llm_call(self):
        monitor = AgentMonitor()
        monitor.record_llm_call("a1", _make_llm_result())
        assert len(monitor.llm_metrics.records) == 1

    def test_get_agent_decisions(self):
        monitor = AgentMonitor()
        start = time.monotonic()
        monitor.record_decision("a1", "success", start)
        monitor.record_decision("a2", "success", start)
        assert len(monitor.get_agent_decisions("a1")) == 1


class TestMetricsAggregator:
    def _setup(self) -> tuple[AgentMonitor, MetricsAggregator]:
        monitor = AgentMonitor()
        return monitor, MetricsAggregator(monitor)

    def test_agent_summary_success_rate(self):
        monitor, agg = self._setup()
        start = time.monotonic()
        for _ in range(8):
            monitor.record_decision("a1", "success", start)
            monitor.record_llm_call("a1", _make_llm_result())
        for _ in range(2):
            monitor.record_decision("a1", "timeout", start)
        summary = agg.get_agent_summary("a1")
        assert summary.total_decisions == 10
        assert summary.success_rate == pytest.approx(0.8)
        assert summary.timeout_count == 2

    def test_agent_summary_tokens(self):
        monitor, agg = self._setup()
        start = time.monotonic()
        monitor.record_llm_call("a1", _make_llm_result(tokens=100))
        monitor.record_llm_call("a1", _make_llm_result(tokens=200))
        summary = agg.get_agent_summary("a1")
        assert summary.total_input_tokens == 300
        assert summary.total_tokens == 450  # 150 + 300

    def test_provider_summary(self):
        monitor, agg = self._setup()
        for _ in range(9):
            monitor.record_llm_call("a1", _make_llm_result(provider="anthropic"))
        monitor.record_llm_call(
            "a1", _make_llm_result(status="error", provider="anthropic")
        )
        summary = agg.get_provider_summary("anthropic")
        assert summary.total_calls == 10
        assert summary.success_count == 9
        assert summary.availability_rate == pytest.approx(0.9)

    def test_empty_data(self):
        _, agg = self._setup()
        summary = agg.get_agent_summary("nonexistent")
        assert summary.total_decisions == 0
        assert summary.success_rate == 0.0
