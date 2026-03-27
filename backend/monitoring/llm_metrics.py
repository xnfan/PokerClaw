"""LLM call metrics collection and storage."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.llm.base_provider import LLMCallResult


@dataclass
class LLMCallRecord:
    """A single LLM call's full metrics."""
    record_id: str
    agent_id: str
    hand_id: str | None
    session_id: str | None
    provider_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    status: str
    error_message: str | None
    is_retry: bool
    created_at: str


class LLMMetricsCollector:
    """Collects and stores LLM call metrics (in-memory for MVP, DB later)."""

    def __init__(self) -> None:
        self.records: list[LLMCallRecord] = []

    def record(
        self,
        agent_id: str,
        llm_result: LLMCallResult,
        hand_id: str | None = None,
        session_id: str | None = None,
        is_retry: bool = False,
    ) -> LLMCallRecord:
        """Record one LLM API call."""
        rec = LLMCallRecord(
            record_id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            hand_id=hand_id,
            session_id=session_id,
            provider_name=llm_result.provider_name,
            model_name=llm_result.model_name,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
            total_tokens=llm_result.total_tokens,
            latency_ms=llm_result.latency_ms,
            status=llm_result.status,
            error_message=llm_result.error_message,
            is_retry=is_retry,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.records.append(rec)
        return rec

    def get_by_agent(self, agent_id: str) -> list[LLMCallRecord]:
        return [r for r in self.records if r.agent_id == agent_id]

    def get_by_session(self, session_id: str) -> list[LLMCallRecord]:
        return [r for r in self.records if r.session_id == session_id]

    def get_by_hand(self, hand_id: str) -> list[LLMCallRecord]:
        return [r for r in self.records if r.hand_id == hand_id]

    def get_all(self) -> list[LLMCallRecord]:
        return list(self.records)
