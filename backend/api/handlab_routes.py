"""Hand Lab API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.hand_lab import HandLab, PlayerSetup, ScenarioConfig
from backend.services import game_service

router = APIRouter(prefix="/api/handlab", tags=["handlab"])


class PlayerSetupRequest(BaseModel):
    agent_id: str
    chips: int = 5000
    hole_cards: list[str] = []
    seat_index: int = 0


class ScenarioRequest(BaseModel):
    players: list[PlayerSetupRequest]
    community_cards: list[str] = []
    small_blind: int = 50
    big_blind: int = 100
    dealer_index: int = 0


class RunMultipleRequest(BaseModel):
    scenario: ScenarioRequest
    count: int = 10


class StartLabRequest(BaseModel):
    scenario: ScenarioRequest
    count: int = 1


def _to_config(body: ScenarioRequest) -> ScenarioConfig:
    return ScenarioConfig(
        players=[
            PlayerSetup(
                agent_id=p.agent_id,
                chips=p.chips,
                hole_cards=p.hole_cards,
                seat_index=p.seat_index if p.seat_index else i,
            )
            for i, p in enumerate(body.players)
        ],
        community_cards=body.community_cards,
        small_blind=body.small_blind,
        big_blind=body.big_blind,
        dealer_index=body.dealer_index,
    )


@router.post("/run-once")
async def run_once(body: ScenarioRequest):
    try:
        config = _to_config(body)
        lab = HandLab(config)
        result = await lab.run_once()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/run-multiple")
async def run_multiple(body: RunMultipleRequest):
    try:
        config = _to_config(body.scenario)
        lab = HandLab(config)
        result = await lab.run_multiple(body.count)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/start")
def start_lab(body: StartLabRequest):
    try:
        config = _to_config(body.scenario)
        session = game_service.start_lab_session(config, count=body.count)
        return {"session_id": session.session_id}
    except ValueError as e:
        raise HTTPException(400, str(e))
