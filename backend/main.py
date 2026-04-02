"""FastAPI application entry point for PokerClaw.

Run with:
    cd PokerClaw
    uvicorn backend.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.api.agent_routes import router as agent_router
from backend.api.game_routes import router as game_router
from backend.api.replay_routes import router as replay_router
from backend.api.monitoring_routes import router as monitoring_router
from backend.api.equity_routes import router as equity_router
from backend.api.handlab_routes import router as handlab_router
from backend.api.websocket_handler import router as ws_router

# Initialize database on startup
init_db()

app = FastAPI(title="PokerClaw", version="0.1.0")

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(agent_router)
app.include_router(game_router)
app.include_router(replay_router)
app.include_router(monitoring_router)
app.include_router(equity_router)
app.include_router(handlab_router)
app.include_router(ws_router)


@app.get("/")
def root():
    return {
        "name": "PokerClaw",
        "version": "0.1.0",
        "docs": "/docs",
    }
