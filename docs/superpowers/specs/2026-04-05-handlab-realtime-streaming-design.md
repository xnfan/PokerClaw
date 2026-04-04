# Hand Lab Real-Time Streaming Design

**Date:** 2026-04-05
**Status:** Approved

## Problem

Hand Lab currently runs hands to completion on the backend, then returns all steps in a single HTTP response. The frontend simulates real-time playback by stepping through pre-collected steps with a timer. This means users never see the actual deal/think/bet/flop/turn/river process happening live — they only see a replay after the fact.

## Goal

Make Hand Lab stream events in real-time via WebSocket, identical to how normal games work. Both "Run Once" and "Run N Times" modes should show live dealing, thinking animations, betting actions, and street reveals as they happen.

## Approach

Reuse the existing WebSocket infrastructure (`/ws/game/{session_id}`, `GameSession`, `broadcast` callback). Hand Lab creates a temporary game session, and the frontend connects to it via WebSocket to receive real-time events.

## Backend Changes

### 1. New endpoint: `POST /api/handlab/start`

**Request body:** Same `ScenarioRequest` + optional `count` field (default 1).

**Response:** `{ "session_id": "<uuid>" }`

This endpoint:
1. Validates the scenario config
2. Creates a `GameSession` with status `"pending_start"` and stores it in `_active_games`
3. Stores the Hand Lab config (preset cards, community cards) on the session for later use
4. Returns the session_id immediately (does NOT run the hand)

The game starts when the WebSocket connects (same pattern as normal games via `trigger_game_start`).

### 2. New function: `start_lab_session` in `game_service.py`

```python
def start_lab_session(config: ScenarioConfig, count: int = 1) -> GameSession:
```

- Builds `PlayerState` list with preset hole cards
- Loads agents via `create_agent_from_db`
- Creates a `CashGame` with appropriate config (street_delay_ms=1200, hand_delay_ms=2000)
- Adds players to the game
- Stores preset card info on the session (for deck manipulation before each hand)
- Registers the session in `_active_games` with status `"pending_start"`

### 3. New function: `run_lab_game` in `game_service.py`

```python
async def run_lab_game(session_id: str) -> dict:
```

Called by `trigger_game_start` when it detects a lab session. For each hand:
1. Creates a `GameRunner` with the session's players and agents
2. Removes preset cards from deck (`deck.remove_cards`)
3. Pre-sets community cards on `runner.state.community_cards`
4. Registers `on_action` callback that:
   - Computes equity at `hand_start` and `street_start` events
   - Augments events with `equity` data before broadcasting
   - Forwards all events via `session.on_event` (the WebSocket broadcast)
5. Runs `runner.run_hand()`
6. Broadcasts `hand_complete` with full result + equity
7. After all hands: broadcasts `lab_finished` with summary statistics

### 4. Modified `trigger_game_start`

Add a check: if the session has a `lab_config` attribute, call `run_lab_game` instead of `run_game`.

### 5. Event augmentation

Hand Lab events carry extra data compared to normal game events:

| Event | Extra fields |
|-------|-------------|
| `hand_start` | `equity: [{player_id, win_pct, tie_pct}]` |
| `street_start` | `equity: [{player_id, win_pct, tie_pct}]` |
| `lab_finished` | `summary: {win_rate, avg_profit, avg_pot, total_runs}`, replaces `game_finished` |

### 6. Keep existing REST endpoints

`/api/handlab/run-once` and `/api/handlab/run-multiple` remain for backward compatibility / programmatic use.

## Frontend Changes

### 1. HandLabPage state machine

```
Setup → Connecting → Live → Finished
```

- **Setup**: Scenario configuration (unchanged)
- **Connecting**: After POST `/api/handlab/start`, connecting WebSocket
- **Live**: Real-time event display (poker table, actions, equity)
- **Finished**: Review completed hands, summary statistics

### 2. WebSocket connection in HandLabPage

On "Run Once" or "Run N Times":
1. `POST /api/handlab/start` with scenario + count
2. `createGameWS(sessionId)` to connect WebSocket
3. Handle events identically to `GamePlayPage`:
   - `hand_start` → reset live state, show hole cards, show equity
   - `player_thinking` → show thinking indicator
   - `player_action` → append to action log, update pot
   - `street_start` → reveal community cards, update equity
   - `hand_complete` → store completed hand, update hand list
   - `lab_finished` → show summary, transition to Finished state

### 3. Live UI during streaming

During the Live phase, the Hand Lab page shows:
- Poker table with community cards (revealed progressively)
- Player seats with hole cards, equity bars, thinking dots
- Live action log (auto-scrolling)
- Pot display
- "Stop" button (to abort remaining hands in multi-run)
- Hand counter: "Hand 3 / 10"

### 4. Finished state

After `lab_finished`:
- Multi-run summary (win rates, avg profit) — same as current
- Hand selector to browse individual completed hands
- Step-by-step replay controls for reviewing any completed hand (reuse existing playback logic with the steps data from `hand_complete`)

### 5. API client additions

```typescript
startLab: (data: { scenario: ScenarioRequest, count?: number }) =>
  request<{ session_id: string }>('/api/handlab/start', { method: 'POST', body: JSON.stringify(data) }),
```

## Files to Modify

### Backend
- `backend/api/handlab_routes.py` — add `POST /api/handlab/start` endpoint
- `backend/services/game_service.py` — add `start_lab_session`, `run_lab_game`, modify `trigger_game_start`
- `backend/services/hand_lab.py` — extract equity computation to a reusable function

### Frontend
- `frontend/src/pages/HandLabPage.tsx` — major rewrite: add WS connection, live state, state machine
- `frontend/src/api/client.ts` — add `startLab` API method

### No changes needed
- `backend/api/websocket_handler.py` — reused as-is
- `backend/engine/game_runner.py` — reused as-is
- `backend/engine/cash_game.py` — reused as-is
- Existing REST endpoints preserved for backward compatibility
