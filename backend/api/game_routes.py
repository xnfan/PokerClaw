"""Game session API routes."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import game_service

router = APIRouter(prefix="/api/games", tags=["games"])


class GameCreate(BaseModel):
    agent_ids: list[str]
    small_blind: int = 50
    big_blind: int = 100
    buy_in: int = 5000
    num_hands: int = 10


class HumanGameCreate(BaseModel):
    agent_ids: list[str]
    human_name: str = "Player"
    small_blind: int = 50
    big_blind: int = 100
    buy_in: int = 5000
    num_hands: int = 10


@router.post("")
def create_game(body: GameCreate):
    try:
        session = game_service.create_game(
            agent_ids=body.agent_ids,
            small_blind=body.small_blind,
            big_blind=body.big_blind,
            buy_in=body.buy_in,
        )
        return {"session_id": session.session_id, "status": session.status}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{session_id}/start")
async def start_game(session_id: str, num_hands: int = 10):
    session = game_service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != "waiting":
        raise HTTPException(400, f"Session is {session.status}, cannot start")

    # Set pending_start — game will be triggered when WebSocket connects
    session.status = "pending_start"
    session._num_hands = num_hands
    return {"session_id": session_id, "status": "pending_start", "num_hands": num_hands}


@router.post("/{session_id}/stop")
async def stop_game(session_id: str):
    success = game_service.stop_game(session_id)
    if not success:
        raise HTTPException(404, "Session not found or not running")
    return {"session_id": session_id, "status": "stopping"}


@router.get("")
def list_games():
    return game_service.list_sessions()


@router.get("/{session_id}")
def get_game(session_id: str):
    session = game_service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "session_id": session.session_id,
        "status": session.status,
        "total_hands_played": len(session.hand_results),
        "current_chips": {
            p.display_name: p.chips for p in session.game.players
        },
        "human_player_id": session.human_player_id,
    }


@router.get("/{session_id}/hands")
def get_game_hands(session_id: str):
    session = game_service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session.hand_results


@router.post("/human")
def create_human_game(body: HumanGameCreate):
    """Create a game with a human player vs AI agents."""
    try:
        human_player = {
            "player_id": f"human_{body.human_name.lower().replace(' ', '_')}",
            "display_name": body.human_name,
        }
        session = game_service.create_game(
            agent_ids=body.agent_ids,
            small_blind=body.small_blind,
            big_blind=body.big_blind,
            buy_in=body.buy_in,
            human_player=human_player,
        )
        return {
            "session_id": session.session_id,
            "status": session.status,
            "human_player_id": session.human_player_id,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
