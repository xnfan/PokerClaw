"""Monitoring API routes."""
from __future__ import annotations

from fastapi import APIRouter
from backend.services.game_service import get_aggregator, get_monitor

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/agents/{agent_id}")
def get_agent_metrics(agent_id: str):
    agg = get_aggregator()
    summary = agg.get_agent_summary(agent_id)
    return {
        "agent_id": summary.agent_id,
        "total_decisions": summary.total_decisions,
        "successful_decisions": summary.successful_decisions,
        "timeout_count": summary.timeout_count,
        "error_count": summary.error_count,
        "success_rate": round(summary.success_rate, 4),
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "total_tokens": summary.total_tokens,
        "avg_latency_ms": round(summary.avg_latency_ms, 1),
        "avg_decision_ms": round(summary.avg_decision_ms, 1),
        "p95_latency_ms": round(summary.p95_latency_ms, 1),
        "total_llm_calls": summary.total_llm_calls,
        "retry_count": summary.retry_count,
    }


@router.get("/agents/{agent_id}/llm-calls")
def get_agent_llm_calls(agent_id: str):
    monitor = get_monitor()
    records = monitor.llm_metrics.get_by_agent(agent_id)
    return [
        {
            "record_id": r.record_id,
            "provider_name": r.provider_name,
            "model_name": r.model_name,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "latency_ms": round(r.latency_ms, 1),
            "status": r.status,
            "is_retry": r.is_retry,
            "created_at": r.created_at,
        }
        for r in records[-100:]  # last 100
    ]


@router.get("/agents/{agent_id}/decisions")
def get_agent_decisions(agent_id: str):
    monitor = get_monitor()
    decisions = monitor.get_agent_decisions(agent_id)
    return [
        {
            "record_id": d.record_id,
            "decision_status": d.decision_status,
            "total_decision_ms": round(d.total_decision_ms, 1),
            "error_message": d.error_message,
            "created_at": d.created_at,
        }
        for d in decisions[-100:]
    ]


@router.get("/providers")
def get_providers_overview():
    agg = get_aggregator()
    all_records = agg.llm_metrics.get_all()
    providers = set(r.provider_name for r in all_records)
    return [
        {
            "provider_name": p,
            **_provider_dict(agg.get_provider_summary(p)),
        }
        for p in providers
    ]


@router.get("/overview")
def get_overview():
    monitor = get_monitor()
    all_llm = monitor.llm_metrics.get_all()
    all_dec = monitor.decisions
    return {
        "total_llm_calls": len(all_llm),
        "total_decisions": len(all_dec),
        "total_tokens": sum(r.total_tokens for r in all_llm),
        "success_decisions": sum(
            1 for d in all_dec if d.decision_status == "success"
        ),
        "timeout_decisions": sum(
            1 for d in all_dec if d.decision_status == "timeout"
        ),
    }


def _provider_dict(s) -> dict:
    return {
        "total_calls": s.total_calls,
        "success_count": s.success_count,
        "error_count": s.error_count,
        "availability_rate": round(s.availability_rate, 4),
        "avg_latency_ms": round(s.avg_latency_ms, 1),
        "p95_latency_ms": round(s.p95_latency_ms, 1),
    }
