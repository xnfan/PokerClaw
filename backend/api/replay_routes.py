"""Replay/history API routes."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException
from backend.database import get_db

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.get("/sessions/{session_id}")
def get_session_hands(session_id: str):
    db = get_db()
    rows = db.execute(
        "SELECT hand_id, hand_number, community_cards, pot_total, winners_json FROM hand_records WHERE session_id=? ORDER BY hand_number",
        (session_id,),
    ).fetchall()
    db.close()
    return [
        {
            "hand_id": r["hand_id"],
            "hand_number": r["hand_number"],
            "community_cards": json.loads(r["community_cards"]),
            "pot_total": r["pot_total"],
            "winners": json.loads(r["winners_json"]),
        }
        for r in rows
    ]


@router.get("/hands/{hand_id}")
def get_hand_detail(hand_id: str):
    db = get_db()
    row = db.execute(
        "SELECT * FROM hand_records WHERE hand_id=?", (hand_id,)
    ).fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "Hand not found")
    return {
        "hand_id": row["hand_id"],
        "session_id": row["session_id"],
        "hand_number": row["hand_number"],
        "community_cards": json.loads(row["community_cards"]),
        "pot_total": row["pot_total"],
        "winners": json.loads(row["winners_json"]),
        "actions": json.loads(row["actions_json"]),
    }
