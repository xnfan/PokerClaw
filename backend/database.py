"""SQLite database initialization and session management."""
from __future__ import annotations

import sqlite3
import json
import os
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.getenv("POKERCLAW_DB", "pokerclaw.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    agent_id        TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    skill_level     TEXT NOT NULL,
    play_style      TEXT NOT NULL,
    custom_traits   TEXT DEFAULT '',
    llm_provider    TEXT NOT NULL DEFAULT 'mock',
    llm_model       TEXT NOT NULL DEFAULT 'mock-v1',
    llm_api_key     TEXT DEFAULT '',
    total_hands     INTEGER DEFAULT 0,
    total_profit    INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_sessions (
    session_id      TEXT PRIMARY KEY,
    game_type       TEXT NOT NULL DEFAULT 'cash',
    status          TEXT NOT NULL DEFAULT 'waiting',
    small_blind     INTEGER NOT NULL DEFAULT 50,
    big_blind       INTEGER NOT NULL DEFAULT 100,
    max_players     INTEGER NOT NULL DEFAULT 9,
    config_json     TEXT DEFAULT '{}',
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hand_records (
    hand_id           TEXT PRIMARY KEY,
    session_id        TEXT NOT NULL,
    hand_number       INTEGER NOT NULL,
    community_cards   TEXT DEFAULT '[]',
    pot_total         INTEGER DEFAULT 0,
    winners_json      TEXT DEFAULT '{}',
    actions_json      TEXT DEFAULT '[]',
    player_cards_json TEXT DEFAULT '{}',
    chip_changes_json TEXT DEFAULT '{}',
    started_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_call_logs (
    record_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    hand_id         TEXT,
    session_id      TEXT,
    provider_name   TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    latency_ms      REAL DEFAULT 0,
    status          TEXT NOT NULL,
    error_message   TEXT,
    is_retry        INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decision_logs (
    record_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    hand_id         TEXT,
    session_id      TEXT,
    decision_status TEXT NOT NULL,
    total_decision_ms REAL DEFAULT 0,
    error_message   TEXT,
    created_at      TEXT NOT NULL
);
"""


def get_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    conn = get_db(db_path)
    conn.executescript(_SCHEMA)
    # Migration: add chip_changes_json column if missing
    try:
        conn.execute("ALTER TABLE hand_records ADD COLUMN chip_changes_json TEXT DEFAULT '{}'")
    except Exception:
        pass  # column already exists
    conn.commit()
    conn.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
