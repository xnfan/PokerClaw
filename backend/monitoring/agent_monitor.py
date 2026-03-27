"""Agent decision monitoring: tracks success/timeout/error rates."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from backend.llm.base_provider import LLMCallResult
from backend.monitoring.llm_metrics import LLMMetricsCollector


@dataclass
class DecisionRecord:
    """Record of a single agent decision attempt."""
    record_id: str
    agent_id: str
    hand_id: str | None
    session_id: str | None
    decision_status: str  # success / timeout / error_fallback / exception
    total_decision_ms: float
    error_message: str | None
    created_at: str


class AgentMonitor:
    """Monitors agent decision behavior and delegates LLM metrics."""

    def __init__(self, llm_metrics: LLMMetricsCollector | None = None) -> None:
        self.llm_metrics = llm_metrics or LLMMetricsCollector()
        self.decisions: list[DecisionRecord] = []

    def record_llm_call(
        self,
        agent_id: str,
        llm_result: LLMCallResult,
        hand_id: str | None = None,
        session_id: str | None = None,
        is_retry: bool = False,
    ) -> None:
        """Record an LLM call (delegates to LLMMetricsCollector)."""
        self.llm_metrics.record(
            agent_id=agent_id,
            llm_result=llm_result,
            hand_id=hand_id,
            session_id=session_id,
            is_retry=is_retry,
        )

    def record_decision(
        self,
        agent_id: str,
        status: str,
        start_time: float,
        hand_id: str | None = None,
        session_id: str | None = None,
        error: str | None = None,
    ) -> DecisionRecord:
        """Record one decision outcome."""
        elapsed_ms = (time.monotonic() - start_time) * 1000
        rec = DecisionRecord(
            record_id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            hand_id=hand_id,
            session_id=session_id,
            decision_status=status,
            total_decision_ms=elapsed_ms,
            error_message=error,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.decisions.append(rec)
        return rec

    def get_agent_decisions(self, agent_id: str) -> list[DecisionRecord]:
        return [d for d in self.decisions if d.agent_id == agent_id]

    def get_session_decisions(self, session_id: str) -> list[DecisionRecord]:
        return [d for d in self.decisions if d.session_id == session_id]
