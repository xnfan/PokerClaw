"""Aggregate monitoring metrics by agent, session, and provider."""
from __future__ import annotations

from dataclasses import dataclass

from backend.monitoring.agent_monitor import AgentMonitor
from backend.monitoring.llm_metrics import LLMMetricsCollector


@dataclass
class AgentMetricsSummary:
    agent_id: str
    total_decisions: int
    successful_decisions: int
    timeout_count: int
    error_count: int
    success_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_latency_ms: float
    avg_decision_ms: float
    p95_latency_ms: float
    total_llm_calls: int
    retry_count: int


@dataclass
class ProviderMetricsSummary:
    provider_name: str
    total_calls: int
    success_count: int
    error_count: int
    timeout_count: int
    availability_rate: float
    avg_latency_ms: float
    p95_latency_ms: float


def _percentile(values: list[float], pct: float) -> float:
    """Compute percentile from sorted list."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * pct / 100)
    idx = min(idx, len(sorted_v) - 1)
    return sorted_v[idx]


class MetricsAggregator:
    """Aggregates metrics across dimensions."""

    def __init__(self, monitor: AgentMonitor) -> None:
        self.monitor = monitor

    @property
    def llm_metrics(self) -> LLMMetricsCollector:
        return self.monitor.llm_metrics

    def get_agent_summary(self, agent_id: str) -> AgentMetricsSummary:
        decisions = self.monitor.get_agent_decisions(agent_id)
        llm_calls = self.llm_metrics.get_by_agent(agent_id)

        total = len(decisions)
        success = sum(1 for d in decisions if d.decision_status == "success")
        timeouts = sum(1 for d in decisions if d.decision_status == "timeout")
        errors = total - success - timeouts

        latencies = [r.latency_ms for r in llm_calls if r.status == "success"]
        decision_times = [d.total_decision_ms for d in decisions]

        return AgentMetricsSummary(
            agent_id=agent_id,
            total_decisions=total,
            successful_decisions=success,
            timeout_count=timeouts,
            error_count=errors,
            success_rate=success / total if total > 0 else 0.0,
            total_input_tokens=sum(r.input_tokens for r in llm_calls),
            total_output_tokens=sum(r.output_tokens for r in llm_calls),
            total_tokens=sum(r.total_tokens for r in llm_calls),
            avg_latency_ms=(
                sum(latencies) / len(latencies) if latencies else 0.0
            ),
            avg_decision_ms=(
                sum(decision_times) / len(decision_times)
                if decision_times else 0.0
            ),
            p95_latency_ms=_percentile(latencies, 95),
            total_llm_calls=len(llm_calls),
            retry_count=sum(1 for r in llm_calls if r.is_retry),
        )

    def get_provider_summary(self, provider_name: str) -> ProviderMetricsSummary:
        all_calls = [
            r for r in self.llm_metrics.get_all()
            if r.provider_name == provider_name
        ]
        total = len(all_calls)
        successes = sum(1 for r in all_calls if r.status == "success")
        errors = sum(1 for r in all_calls if r.status == "error")
        timeouts = sum(1 for r in all_calls if r.status == "timeout")
        latencies = [r.latency_ms for r in all_calls if r.status == "success"]

        return ProviderMetricsSummary(
            provider_name=provider_name,
            total_calls=total,
            success_count=successes,
            error_count=errors,
            timeout_count=timeouts,
            availability_rate=successes / total if total > 0 else 0.0,
            avg_latency_ms=(
                sum(latencies) / len(latencies) if latencies else 0.0
            ),
            p95_latency_ms=_percentile(latencies, 95),
        )
