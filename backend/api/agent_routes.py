"""Agent CRUD API routes."""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db, now_iso

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    display_name: str
    skill_level: str = "intermediate"  # novice/intermediate/expert
    play_style: str = "tag"  # tag/lag/calling_station/rock/fish/maniac
    custom_traits: str = ""
    llm_provider: str = "mock"
    llm_model: str = "mock-v1"
    llm_api_key: str = ""


class AgentUpdate(BaseModel):
    display_name: str | None = None
    skill_level: str | None = None
    play_style: str | None = None
    custom_traits: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


@router.post("")
def create_agent(body: AgentCreate):
    agent_id = str(uuid.uuid4())[:8]
    db = get_db()
    db.execute(
        "INSERT INTO agents (agent_id, display_name, skill_level, play_style, custom_traits, llm_provider, llm_model, llm_api_key, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (agent_id, body.display_name, body.skill_level, body.play_style,
         body.custom_traits, body.llm_provider, body.llm_model,
         body.llm_api_key, now_iso()),
    )
    db.commit()
    db.close()
    return {"agent_id": agent_id, "display_name": body.display_name}


@router.get("")
def list_agents():
    db = get_db()
    rows = db.execute(
        "SELECT agent_id, display_name, skill_level, play_style, llm_provider, total_hands, total_profit, created_at FROM agents ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    db = get_db()
    row = db.execute("SELECT * FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Agent not found")
    result = dict(row)
    result.pop("llm_api_key", None)  # never expose key
    return result


@router.put("/{agent_id}")
def update_agent(agent_id: str, body: AgentUpdate):
    db = get_db()
    row = db.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "Agent not found")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        db.close()
        return {"ok": True}
    set_clause = ", ".join(f"{k}=?" for k in updates)
    db.execute(
        f"UPDATE agents SET {set_clause} WHERE agent_id=?",
        (*updates.values(), agent_id),
    )
    db.commit()
    db.close()
    return {"ok": True}


@router.delete("/{agent_id}")
def delete_agent(agent_id: str):
    db = get_db()
    db.execute("DELETE FROM agents WHERE agent_id=?", (agent_id,))
    db.commit()
    db.close()
    return {"ok": True}
