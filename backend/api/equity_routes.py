"""Equity calculation API routes."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.engine.card import Card
from backend.engine.equity import EquityCalculator

router = APIRouter(prefix="/api/equity", tags=["equity"])


class EquityRequest(BaseModel):
    players: list[list[str]]  # e.g. [["Ah", "Kd"], ["Qs", "Qh"]]
    community: list[str] = []
    num_simulations: int = 5000


@router.post("")
async def calculate_equity(body: EquityRequest):
    try:
        players_cards = [
            [Card.from_string(c) for c in hand]
            for hand in body.players
        ]
        community = [Card.from_string(c) for c in body.community]
    except ValueError as e:
        raise HTTPException(400, f"Invalid card: {e}")

    try:
        results = await asyncio.to_thread(
            EquityCalculator.calculate,
            players_cards, community, body.num_simulations,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "players": [
            {
                "cards": body.players[i],
                "win_pct": round(r.win_pct * 100, 1),
                "tie_pct": round(r.tie_pct * 100, 1),
                "lose_pct": round(r.lose_pct * 100, 1),
                "sample_count": r.sample_count,
            }
            for i, r in enumerate(results)
        ],
        "community": body.community,
    }
