"""WebSocket handler for real-time game updates."""
from __future__ import annotations

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services import game_service

router = APIRouter()

# Active WebSocket connections per session
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _connections.setdefault(session_id, []).append(websocket)

    # Register broadcast callback on the session
    session = game_service.get_session(session_id)
    if session:
        async def broadcast(event: dict):
            for ws in _connections.get(session_id, []):
                try:
                    await ws.send_json(event)
                except Exception:
                    pass
        session.on_event = broadcast

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # Handle client messages (future: player_action, spectate)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        conns = _connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
