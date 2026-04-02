"""WebSocket handler for real-time game updates."""
from __future__ import annotations

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services import game_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections per session
_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _connections.setdefault(session_id, []).append(websocket)
    logger.info(f"[WS] Client connected for session {session_id}, total clients: {len(_connections[session_id])}")

    # Register broadcast callback on the session
    session = game_service.get_session(session_id)
    if session:
        async def broadcast(event: dict):
            clients = _connections.get(session_id, [])
            event_type = event.get("type", "unknown")
            logger.info(f"[WS] Broadcasting {event_type} to {len(clients)} clients")
            dead = []
            for ws in clients:
                try:
                    await ws.send_json(event)
                except Exception as e:
                    logger.warning(f"[WS] Failed to send to client: {e}")
                    dead.append(ws)
            # Clean up dead connections
            for ws in dead:
                if ws in clients:
                    clients.remove(ws)
        session.on_event = broadcast

        # If game is pending start, trigger it now that callback is registered
        if session.status == "pending_start":
            logger.info(f"[WS] Triggering game start for {session_id}")
            game_service.trigger_game_start(session_id)
    else:
        logger.warning(f"[WS] Session {session_id} not found in active games")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected from session {session_id}")
        conns = _connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
