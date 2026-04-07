"""WebSocket handler for real-time game updates."""
from __future__ import annotations

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.services import game_service
from backend.agent.human_agent import HumanAgent
from backend.engine.betting_round import BettingAction, PlayerAction

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
            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "human_decision":
                # Handle human player decision
                player_id = msg.get("player_id")
                action_str = msg.get("action")
                amount = msg.get("amount", 0)

                if not player_id or not action_str:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Missing player_id or action"}
                    })
                    continue

                # Find the human agent
                human_agent = HumanAgent.get_agent(player_id)
                if not human_agent:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Human agent {player_id} not found"}
                    })
                    continue

                # Convert action string to BettingAction
                try:
                    action_enum = BettingAction(action_str)
                except ValueError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Invalid action: {action_str}"}
                    })
                    continue

                # Submit the decision
                action = PlayerAction(player_id, action_enum, amount)
                success = human_agent.submit_decision(action)

                if success:
                    await websocket.send_json({
                        "type": "decision_accepted",
                        "data": {"player_id": player_id, "action": action_str}
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Decision not accepted (not your turn or invalid action)"}
                    })

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected from session {session_id}")
        conns = _connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)
