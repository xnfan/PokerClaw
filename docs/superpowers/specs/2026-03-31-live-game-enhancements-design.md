# PokerClaw Live Game Enhancements Design

## Overview

Five enhancements to improve the real-time game experience, betting transparency, and game control.

## Feature 1: Real-Time Streaming (Live Game View)

### Problem
Currently the WebSocket only sends `hand_complete` events. Users cannot see the game unfolding in real-time — they must wait for a full hand to finish, then click replay.

### Design

**New WebSocket Event Types:**

```
street_start    — A new street begins (deal community cards)
player_thinking — An agent has started its decision process
player_action   — An agent has completed its action
hand_complete   — (existing) Full hand summary
```

**Event Payloads:**

```python
# street_start
{
  "type": "street_start",
  "data": {
    "hand_id": "abc123",
    "street": "flop",
    "community_cards": ["Ah", "Ks", "7d"],
    "pot": 300
  }
}

# player_thinking
{
  "type": "player_thinking",
  "data": {
    "hand_id": "abc123",
    "player_id": "Alice",
    "street": "flop"
  }
}

# player_action
{
  "type": "player_action",
  "data": {
    "hand_id": "abc123",
    "player_id": "Alice",
    "street": "flop",
    "action": "raise",
    "amount": 200,
    "round_bet": 300,
    "pot_after": 600,
    "thinking": "Strong hand with top pair...",
    "input_tokens": 450,
    "output_tokens": 32,
    "llm_latency_ms": 1200
  }
}
```

**Backend Changes:**

1. `GameRunner` — Add `on_action` async callback (already partially stubbed in `CashGame.run()`):
   - Called after each `betting.apply_action()` in `_run_betting_round()`
   - Also called on `_deal_community()` for street_start events
   - Also called before agent.decide() for player_thinking events

2. `game_service.run_game()` — Wire `on_action` callback that broadcasts via WebSocket

3. `websocket_handler.py` — No changes needed (already generic broadcast)

**Frontend Changes (GamePlayPage):**

1. Handle new event types in WebSocket `onmessage`:
   - `street_start`: Update community cards display progressively
   - `player_thinking`: Show thinking indicator (pulsing dot) on active player's seat
   - `player_action`: Append to live action log, show thinking text, update pot
   - `hand_complete`: Final summary, update chips, clear thinking indicators

2. Live action log panel: Scrolls to bottom on each new action. Shows thinking text expandable.

3. Active player highlight: The currently-thinking player's seat pulses/highlights.

## Feature 2: Betting Logic Audit (Alice Triple Raise)

### Analysis

The code at `betting_round.py` has `MAX_RAISES_PER_ROUND = 4`. In heads-up preflop:
1. Alice (SB/Dealer) posts SB=50
2. Bob (BB) posts BB=100
3. Alice acts first preflop (heads-up rule), raises to 200 (raise #1)
4. Bob re-raises to 400 (raise #2)
5. Alice re-raises to 800 (raise #3)
6. Bob calls 800

This is **legal poker** — 3 raises is within the 4-raise cap. The action log shows Alice raising twice with Bob's re-raise between, which can look like "Alice raised 3 times."

### Fix: Improve Action Display Clarity

Rather than changing the engine logic (which is correct), improve the display:
1. Show `round_bet` (total invested this round) in each action, making it clear each raise builds on the previous bet
2. In the action log, clearly show the betting progression: "Alice raises to 200" not just "Alice raise 200"
3. Verify the `_raise_count` is correctly tracking across the round (audit with test)

### Additional Verification

Add an integration test that specifically validates heads-up preflop raise sequences to confirm:
- Max 4 raises per street are enforced
- After 4 raises, only fold/call/all-in are available
- The action order alternates correctly in heads-up

## Feature 3: Round Investment in Action Detail

### Problem
Action details show the action and amount, but not how much the player has invested in the current round. This makes it hard to compare against the pot.

### Design

The `ActionRecord` already has `round_bet` field (total invested this round by this player). Changes needed:

**Frontend (GamePlayPage action log):**
```
[flop] Alice  RAISE  200  |  Round: 300  |  Pot: 600
```

**Frontend (ReplayPage action detail panel):**
Add "Round Bet" row showing the cumulative round investment alongside existing fields.

**Backend:** No changes needed — `round_bet` is already computed and serialized.

## Feature 4: Per-Hand Chip Changes

### Problem
After each hand, users can see final chip counts but not how much each player won or lost.

### Design

**Backend Changes:**

1. In `CashGame.run()`, capture `starting_chips` dict before each hand runs
2. Compute `chip_changes = {pid: final - starting for each player}`
3. Include `chip_changes` in the hand result data sent via `on_hand_complete`

**Data Format:**
```python
# Added to hand serialization
"chip_changes": {
  "Alice": +350,   # won 350
  "Bob": -200,     # lost 200
  "Charlie": -150  # lost 150
}
```

**Frontend Changes:**

1. **GamePlayPage**: After each hand completes, show chip change badges on player seats:
   - Green `+350` for winners
   - Red `-200` for losers
   - Animate briefly then settle

2. **ReplayPage**: Show chip changes in the hand summary section

## Feature 5: Multi-Hand Settings + Manual Stop

### Problem
Game setup only allows fixed hand count (default 10). No way to play unlimited hands or stop mid-game.

### Design

**Backend Changes:**

1. Add `stop_event: asyncio.Event` to `GameSession` dataclass
2. New API endpoint: `POST /api/games/{session_id}/stop`
   - Sets the stop_event
   - Returns immediately; game stops after current hand finishes
3. Pass `stop_event` to `CashGame.run()` (already supported in the signature)
4. For "unlimited" mode: frontend sends `num_hands=999999`, backend uses stop_event + player elimination as termination conditions

**Frontend Changes:**

1. **GameSetupPage**:
   - Replace fixed number input with radio: "Set number of hands" / "Unlimited (until stopped)"
   - When "Set number", show number input (default 10)
   - When "Unlimited", hide number input, send num_hands=999999

2. **GamePlayPage**:
   - Show "Stop Game" button (red) when game status is "running"
   - Calls `POST /api/games/{session_id}/stop`
   - Button changes to "Stopping..." while waiting for current hand to complete
   - Once game status changes to "finished", show final results

3. **Auto-elimination display**: When a player reaches 0 chips, show them as eliminated in the seats view. Already handled by `_prepare_hand_players()` filtering.

## Files to Modify

### Backend
- `backend/engine/game_runner.py` — Add on_action callback invocations
- `backend/engine/cash_game.py` — Pass on_action, capture starting chips, compute chip_changes
- `backend/services/game_service.py` — Wire on_action broadcast, add stop_event, add chip_changes to serialization
- `backend/api/game_routes.py` — Add stop endpoint
- `backend/api/websocket_handler.py` — No changes (already generic)

### Frontend
- `frontend/src/pages/GamePlayPage.tsx` — Real-time streaming UI, chip changes, stop button
- `frontend/src/pages/GameSetupPage.tsx` — Unlimited mode toggle
- `frontend/src/pages/ReplayPage.tsx` — Round bet display, chip changes
- `frontend/src/api/client.ts` — Add stopGame API method

### Tests
- Add integration test for heads-up raise cap validation
