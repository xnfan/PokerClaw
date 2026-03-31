# Live Game Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time game streaming, betting display improvements, per-hand chip changes, and multi-hand/stop controls.

**Architecture:** Extend existing WebSocket to push granular per-action events from `GameRunner` through `game_service` to the frontend. Add stop-game API + asyncio.Event. Frontend handles new event types for live streaming and adds chip-change/round-bet displays.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, existing WebSocket infrastructure

---

## File Structure

| File | Change | Responsibility |
|------|--------|----------------|
| `backend/engine/game_runner.py` | Modify | Add on_action callback invocations for street_start, player_thinking, player_action |
| `backend/engine/cash_game.py` | Modify | Pass on_action to GameRunner, capture starting_chips, compute chip_changes |
| `backend/services/game_service.py` | Modify | Wire on_action broadcast, add stop_event, serialize chip_changes + starting_chips |
| `backend/api/game_routes.py` | Modify | Add POST stop endpoint |
| `frontend/src/api/client.ts` | Modify | Add stopGame API method |
| `frontend/src/pages/GamePlayPage.tsx` | Modify | Real-time streaming UI, chip changes, stop button, round-bet display |
| `frontend/src/pages/GameSetupPage.tsx` | Modify | Unlimited mode toggle |
| `frontend/src/pages/ReplayPage.tsx` | Modify | Round-bet display, chip changes |
| `frontend/src/App.css` | Modify | New CSS for thinking indicator, chip-change animations |
| `backend/tests/engine/test_betting_round.py` | Create | Raise cap validation tests |
| `backend/tests/integration/test_full_hand.py` | Modify | Add chip_changes and on_action callback tests |

---

### Task 1: Backend — Add on_action Callback to GameRunner

**Files:**
- Modify: `backend/engine/game_runner.py`

This task adds the callback mechanism to GameRunner so it can emit events for each street start, player thinking start, and player action.

- [ ] **Step 1: Add on_action attribute and type alias to GameRunner**

In `backend/engine/game_runner.py`, add after the imports (line 18):

```python
from typing import TYPE_CHECKING, Any, Callable, Awaitable

# Callback type for real-time action events
ActionCallback = Callable[[dict[str, Any]], Awaitable[None]]
```

And in `GameRunner.__init__` (after line 79):

```python
        self.on_action: ActionCallback | None = None
```

- [ ] **Step 2: Emit street_start event in _deal_community**

Replace the `_deal_community` method (lines 131-135) with:

```python
    async def _deal_community(self, street: Street) -> None:
        if street == Street.FLOP:
            self.state.community_cards.extend(self.deck.deal(3))
        elif street in (Street.TURN, Street.RIVER):
            self.state.community_cards.extend(self.deck.deal(1))
        if self.on_action:
            await self.on_action({
                "type": "street_start",
                "data": {
                    "hand_id": self.hand_id,
                    "street": street.value,
                    "community_cards": [str(c) for c in self.state.community_cards],
                    "pot": self.state.pot_manager.total_pot,
                },
            })
```

Note: `_deal_community` signature changes to `async def`. Update the call site in `run_hand` (line 92) from `self._deal_community(street)` to `await self._deal_community(street)`.

- [ ] **Step 3: Emit player_thinking and player_action events in _run_betting_round**

In `_run_betting_round`, after getting `next_pid` and before calling `agent.decide()` (around line 166), add:

```python
            # Emit player_thinking event
            display_name = self._player_names.get(next_pid, next_pid)
            if self.on_action:
                await self.on_action({
                    "type": "player_thinking",
                    "data": {
                        "hand_id": self.hand_id,
                        "player_id": display_name,
                        "street": street.value,
                    },
                })
```

After the `self.action_history.append(record)` line (line 196), add:

```python
            # Emit player_action event
            if self.on_action:
                await self.on_action({
                    "type": "player_action",
                    "data": {
                        "hand_id": self.hand_id,
                        "player_id": record.player_id,
                        "street": record.street,
                        "action": record.action,
                        "amount": record.amount,
                        "round_bet": record.round_bet,
                        "pot_after": record.pot_after,
                        "thinking": record.thinking,
                        "input_tokens": record.input_tokens,
                        "output_tokens": record.output_tokens,
                        "llm_latency_ms": record.llm_latency_ms,
                    },
                })
```

- [ ] **Step 4: Verify existing tests still pass**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/ -v`
Expected: All existing tests PASS (the on_action callback is optional/None by default)

- [ ] **Step 5: Commit**

```bash
git add backend/engine/game_runner.py
git commit -m "feat: add on_action callback to GameRunner for real-time events"
```

---

### Task 2: Backend — Add Starting Chips + Chip Changes to CashGame

**Files:**
- Modify: `backend/engine/cash_game.py`

Capture starting chips before each hand, compute chip deltas, include in HandResult data flow.

- [ ] **Step 1: Modify CashGame.run() to capture starting chips and pass on_action**

In `backend/engine/cash_game.py`, modify the `run` method. Replace the hand loop body (lines 89-119) with:

```python
        for _ in range(num_hands):
            # Check for stop signal
            if stop_event and stop_event.is_set():
                break
            # Capture starting chips before the hand
            starting_chips = {p.player_id: p.chips for p in self.players}
            # Reset per-hand state for each player
            hand_players = self._prepare_hand_players()
            if len(hand_players) < 2:
                break  # Not enough players to continue
            active_agents = {
                p.player_id: self.agents[p.player_id] for p in hand_players
            }
            runner = GameRunner(
                players=hand_players,
                agents=active_agents,
                small_blind=self.config.small_blind,
                big_blind=self.config.big_blind,
                dealer_index=self.dealer_index % len(hand_players),
            )
            # Pass action callback to runner
            if on_action:
                runner.on_action = on_action
            result = await runner.run_hand()
            self.hand_results.append(result)
            # Sync chips back to session players
            for p in self.players:
                if p.player_id in result.final_chips:
                    p.chips = result.final_chips[p.player_id]
            # Compute chip changes
            chip_changes = {}
            for p in self.players:
                start = starting_chips.get(p.player_id, 0)
                chip_changes[p.player_id] = p.chips - start
            result.starting_chips = starting_chips
            result.chip_changes = chip_changes
            self.dealer_index = (self.dealer_index + 1) % len(self.players)
            self._hand_count += 1
            if on_hand_complete:
                await on_hand_complete(result)
```

- [ ] **Step 2: Add starting_chips and chip_changes fields to HandResult**

In `backend/engine/game_runner.py`, add to the `HandResult` dataclass (after line 50):

```python
    starting_chips: dict[str, int] = field(default_factory=dict)
    chip_changes: dict[str, int] = field(default_factory=dict)
```

Add the missing import at the top of game_runner.py:
```python
from dataclasses import dataclass, field
```
(This import already exists at line 6, so just verify `field` is included.)

- [ ] **Step 3: Verify tests pass**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/engine/cash_game.py backend/engine/game_runner.py
git commit -m "feat: track starting chips and chip changes per hand"
```

---

### Task 3: Backend — Wire on_action Broadcast + Stop Event in game_service

**Files:**
- Modify: `backend/services/game_service.py`

Wire the on_action callback through the service layer to broadcast real-time events via WebSocket. Add stop_event for manual game termination.

- [ ] **Step 1: Add stop_event to GameSession and wire on_action**

In `backend/services/game_service.py`, add import at top:

```python
import asyncio
```
(Already imported — verify it's there.)

Modify the `GameSession` dataclass (around line 36) to add:

```python
@dataclass
class GameSession:
    session_id: str
    game: CashGame
    status: str = "waiting"  # waiting / running / finished
    hand_results: list[dict] = field(default_factory=list)
    on_event: Callable | None = None  # WebSocket broadcast callback
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
```

- [ ] **Step 2: Wire on_action callback in run_game**

In the `run_game` function, add an `on_action` callback before the `result = await session.game.run(...)` call. Replace lines 126-136 with:

```python
    hand_num = 0

    async def on_hand_complete(result: HandResult) -> None:
        nonlocal hand_num
        hand_num += 1
        hand_data = _serialize_hand(result, session_id, hand_num)
        session.hand_results.append(hand_data)
        _save_hand_to_db(hand_data)
        if session.on_event:
            await session.on_event({"type": "hand_complete", "data": hand_data})

    async def on_action(event: dict) -> None:
        if session.on_event:
            await session.on_event(event)

    result = await session.game.run(
        num_hands,
        on_hand_complete=on_hand_complete,
        on_action=on_action,
        stop_event=session.stop_event,
    )
```

- [ ] **Step 3: Add chip_changes and starting_chips to _serialize_hand**

In the `_serialize_hand` function, add these fields to the returned dict (after "player_cards" around line 212):

```python
        "starting_chips": {name_map.get(k, k): v for k, v in result.starting_chips.items()},
        "chip_changes": {name_map.get(k, k): v for k, v in result.chip_changes.items()},
```

- [ ] **Step 4: Add stop_game function**

Add this function after `get_session`:

```python
def stop_game(session_id: str) -> bool:
    """Signal a running game to stop after the current hand."""
    session = _active_games.get(session_id)
    if not session:
        return False
    session.stop_event.set()
    return True
```

- [ ] **Step 5: Verify tests pass**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/services/game_service.py
git commit -m "feat: wire on_action broadcast and stop_event in game service"
```

---

### Task 4: Backend — Add Stop Game API Endpoint

**Files:**
- Modify: `backend/api/game_routes.py`

- [ ] **Step 1: Add POST stop endpoint**

Add after the `start_game` endpoint (after line 45):

```python
@router.post("/{session_id}/stop")
def stop_game(session_id: str):
    success = game_service.stop_game(session_id)
    if not success:
        raise HTTPException(404, "Session not found or not running")
    return {"session_id": session_id, "status": "stopping"}
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/game_routes.py
git commit -m "feat: add POST stop endpoint for manual game termination"
```

---

### Task 5: Backend — Add Raise Cap Validation Tests

**Files:**
- Create: `backend/tests/engine/test_betting_round.py`

Verify the raise cap logic is correct and heads-up action order is proper.

- [ ] **Step 1: Write the raise cap test file**

Create `backend/tests/engine/test_betting_round.py`:

```python
"""Tests for betting round logic, especially raise cap validation."""
import pytest
from backend.engine.betting_round import (
    BettingAction,
    BettingRound,
    PlayerAction,
    PlayerSeat,
)
from backend.engine.pot_manager import PotManager


def _make_seats(num=2, chips=5000, current_bet=0):
    return [
        PlayerSeat(
            player_id=f"p{i}",
            chips=chips,
            is_active=True,
            is_all_in=False,
            current_bet=current_bet,
        )
        for i in range(num)
    ]


class TestRaiseCap:
    def test_max_four_raises_per_round(self):
        """After 4 raises, only fold/call/all-in should be available."""
        seats = _make_seats(2, chips=50000)
        pot = PotManager()
        br = BettingRound(seats=seats, pot_manager=pot, current_bet=0, min_raise=100)

        # Raise 4 times alternating between players
        actions = [
            PlayerAction("p0", BettingAction.RAISE, 200),
            PlayerAction("p1", BettingAction.RAISE, 400),
            PlayerAction("p0", BettingAction.RAISE, 800),
            PlayerAction("p1", BettingAction.RAISE, 1600),
        ]
        for a in actions:
            br.apply_action(a)

        # After 4 raises, RAISE should NOT be in valid actions
        p0_actions = br.get_valid_actions("p0")
        assert BettingAction.RAISE not in p0_actions
        assert BettingAction.FOLD in p0_actions
        assert BettingAction.CALL in p0_actions
        assert BettingAction.ALL_IN in p0_actions

    def test_three_raises_still_allows_fourth(self):
        """After 3 raises, a 4th raise is still allowed."""
        seats = _make_seats(2, chips=50000)
        pot = PotManager()
        br = BettingRound(seats=seats, pot_manager=pot, current_bet=0, min_raise=100)

        actions = [
            PlayerAction("p0", BettingAction.RAISE, 200),
            PlayerAction("p1", BettingAction.RAISE, 400),
            PlayerAction("p0", BettingAction.RAISE, 800),
        ]
        for a in actions:
            br.apply_action(a)

        p1_actions = br.get_valid_actions("p1")
        assert BettingAction.RAISE in p1_actions

    def test_heads_up_preflop_action_order(self):
        """In heads-up, both players get to act and the round completes."""
        seats = _make_seats(2, chips=5000)
        # Simulate preflop: p0 has SB=50, p1 has BB=100
        seats[0].current_bet = 50
        seats[0].chips = 4950
        seats[1].current_bet = 100
        seats[1].chips = 4900
        pot = PotManager()
        pot.add_bet("p0", 50)
        pot.add_bet("p1", 100)

        br = BettingRound(seats=seats, pot_manager=pot, current_bet=100, min_raise=100)

        # p0 should act first (SB in heads-up preflop)
        next_p = br.get_next_player_id()
        assert next_p == "p0"

        # p0 calls
        br.apply_action(PlayerAction("p0", BettingAction.CALL))

        # p1 should act next (BB option)
        next_p = br.get_next_player_id()
        assert next_p == "p1"

        # p1 checks
        br.apply_action(PlayerAction("p1", BettingAction.CHECK))

        # Round should be complete
        assert br.is_complete()
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/engine/test_betting_round.py -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/engine/test_betting_round.py
git commit -m "test: add raise cap and heads-up action order tests"
```

---

### Task 6: Backend — Add Chip Changes Integration Test

**Files:**
- Modify: `backend/tests/integration/test_full_hand.py`

- [ ] **Step 1: Add test for chip_changes in hand results**

Add to the `TestFullHand` class in `backend/tests/integration/test_full_hand.py`:

```python
    async def test_chip_changes_per_hand(self):
        """Each hand should report chip_changes that sum to zero."""
        game, _ = _create_game(num_players=3)
        result = await game.run(3)
        for hand in result.hand_results:
            assert hasattr(hand, 'chip_changes')
            assert len(hand.chip_changes) > 0
            # Chip changes across all players should sum to zero
            total_change = sum(hand.chip_changes.values())
            assert total_change == 0, f"Chip changes don't sum to zero: {hand.chip_changes}"

    async def test_on_action_callback_fires(self):
        """on_action callback should be called during hand execution."""
        game, _ = _create_game(num_players=2)
        events = []

        async def on_action(event):
            events.append(event)

        await game.run(1, on_action=on_action)
        # Should have at least street_start, player_thinking, and player_action events
        event_types = {e["type"] for e in events}
        assert "player_thinking" in event_types
        assert "player_action" in event_types
```

- [ ] **Step 2: Run integration tests**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/integration/test_full_hand.py -v`
Expected: All tests PASS including the 2 new ones

- [ ] **Step 3: Commit**

```bash
git add backend/tests/integration/test_full_hand.py
git commit -m "test: add chip_changes and on_action callback integration tests"
```

---

### Task 7: Frontend — Add stopGame API Method

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add stopGame method**

In `frontend/src/api/client.ts`, add after the `getGameHands` method (line 28):

```typescript
  stopGame: (sessionId: string) => request<any>(`/api/games/${sessionId}/stop`, { method: 'POST' }),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add stopGame API method to frontend client"
```

---

### Task 8: Frontend — GameSetupPage Unlimited Mode

**Files:**
- Modify: `frontend/src/pages/GameSetupPage.tsx`

- [ ] **Step 1: Add unlimited toggle to game setup**

Replace the entire `GameSetupPage.tsx` content with:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function GameSetupPage() {
  const navigate = useNavigate();
  const [agents, setAgents] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [config, setConfig] = useState({ small_blind: 50, big_blind: 100, buy_in: 5000, num_hands: 10 });
  const [unlimited, setUnlimited] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.listAgents().then(setAgents).catch(() => {}); }, []);

  const toggleAgent = (id: string) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleStart = async () => {
    if (selected.length < 2) { alert('Select at least 2 agents'); return; }
    setLoading(true);
    try {
      const numHands = unlimited ? 999999 : config.num_hands;
      const { session_id } = await api.createGame({ agent_ids: selected, ...config });
      await api.startGame(session_id, numHands);
      navigate(`/games/${session_id}`);
    } catch (e: any) { alert(e.message); }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="page-title">New Game</h1>

      <div className="card">
        <h2>Game Settings</h2>
        <div className="grid-4">
          <div>
            <label>Small Blind</label>
            <input type="number" value={config.small_blind} onChange={e => setConfig({...config, small_blind: +e.target.value})} />
          </div>
          <div>
            <label>Big Blind</label>
            <input type="number" value={config.big_blind} onChange={e => setConfig({...config, big_blind: +e.target.value})} />
          </div>
          <div>
            <label>Buy-in</label>
            <input type="number" value={config.buy_in} onChange={e => setConfig({...config, buy_in: +e.target.value})} />
          </div>
          <div>
            <label>Number of Hands</label>
            <div style={{display: 'flex', alignItems: 'center', gap: 8, marginTop: 4}}>
              <label style={{display: 'flex', alignItems: 'center', gap: 4, margin: 0, cursor: 'pointer'}}>
                <input type="radio" checked={!unlimited} onChange={() => setUnlimited(false)} />
                <span>Set:</span>
              </label>
              <input
                type="number"
                value={config.num_hands}
                onChange={e => setConfig({...config, num_hands: +e.target.value})}
                disabled={unlimited}
                style={{width: 80, opacity: unlimited ? 0.4 : 1}}
              />
              <label style={{display: 'flex', alignItems: 'center', gap: 4, margin: 0, cursor: 'pointer'}}>
                <input type="radio" checked={unlimited} onChange={() => setUnlimited(true)} />
                <span>Unlimited</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Select Agents ({selected.length} selected)</h2>
        {agents.length === 0 ? (
          <p className="empty-state">No agents available. <a href="/agents" style={{color:'#22d3ee'}}>Create agents first</a>.</p>
        ) : (
          <div style={{display:'flex', flexWrap:'wrap', gap:10}}>
            {agents.map(a => (
              <div key={a.agent_id}
                onClick={() => toggleAgent(a.agent_id)}
                style={{
                  padding: '12px 20px', borderRadius: 10, cursor: 'pointer',
                  border: selected.includes(a.agent_id) ? '2px solid #0ea5e9' : '2px solid #334155',
                  background: selected.includes(a.agent_id) ? '#0ea5e922' : '#1e293b',
                }}>
                <div style={{fontWeight:600}}>{a.display_name}</div>
                <div style={{fontSize:'0.8rem',color:'#94a3b8'}}>{a.skill_level} / {a.play_style.toUpperCase()}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn btn-primary" onClick={handleStart} disabled={loading || selected.length < 2}
        style={{fontSize:'1rem', padding:'12px 32px'}}>
        {loading ? 'Starting...' : `Start Game (${selected.length} players)`}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GameSetupPage.tsx
git commit -m "feat: add unlimited mode toggle to game setup"
```

---

### Task 9: Frontend — Real-Time Streaming GamePlayPage

**Files:**
- Modify: `frontend/src/pages/GamePlayPage.tsx`

This is the largest frontend change: handle real-time events, show thinking indicators, stop button, chip changes, and round-bet display.

- [ ] **Step 1: Replace GamePlayPage with real-time streaming version**

Replace the entire `frontend/src/pages/GamePlayPage.tsx` with:

```tsx
import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, createGameWS } from '../api/client';

function CardView({ card }: { card: string }) {
  if (!card) return <div className="playing-card facedown">?</div>;
  const suit = card[1];
  const isRed = suit === 'h' || suit === 'd';
  const suitSymbol: Record<string, string> = { h: '\u2665', d: '\u2666', c: '\u2663', s: '\u2660' };
  return <div className={`playing-card ${isRed ? 'red' : ''}`}>{card[0]}{suitSymbol[suit] || suit}</div>;
}

function ActionBadge({ action }: { action: string }) {
  const cls: Record<string, string> = { fold: 'badge-fold', call: 'badge-call', raise: 'badge-raise', check: 'badge-check', all_in: 'badge-allin' };
  return <span className={`badge ${cls[action] || ''}`}>{action}</span>;
}

export default function GamePlayPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [game, setGame] = useState<any>(null);
  const [hands, setHands] = useState<any[]>([]);
  const [selectedHand, setSelectedHand] = useState<any>(null);
  // Real-time state
  const [liveActions, setLiveActions] = useState<any[]>([]);
  const [liveCommunity, setLiveCommunity] = useState<string[]>([]);
  const [livePot, setLivePot] = useState(0);
  const [thinkingPlayer, setThinkingPlayer] = useState<string | null>(null);
  const [currentHandId, setCurrentHandId] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const liveLogRef = useRef<HTMLDivElement>(null);

  // Poll game status
  useEffect(() => {
    if (!sessionId) return;
    const poll = () => {
      api.getGame(sessionId).then(setGame).catch(() => {});
      api.getGameHands(sessionId).then(h => {
        setHands(h);
        if (h.length > 0 && !selectedHand) setSelectedHand(h[h.length - 1]);
      }).catch(() => {});
    };
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [sessionId]);

  // WebSocket for real-time updates
  useEffect(() => {
    if (!sessionId) return;
    const ws = createGameWS(sessionId);
    wsRef.current = ws;
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'hand_complete') {
        setHands(prev => [...prev, msg.data]);
        setSelectedHand(msg.data);
        // Clear live state for next hand
        setLiveActions([]);
        setLiveCommunity([]);
        setLivePot(0);
        setThinkingPlayer(null);
        setCurrentHandId(null);
      } else if (msg.type === 'street_start') {
        setCurrentHandId(msg.data.hand_id);
        setLiveCommunity(msg.data.community_cards || []);
        setLivePot(msg.data.pot || 0);
        setThinkingPlayer(null);
      } else if (msg.type === 'player_thinking') {
        setCurrentHandId(msg.data.hand_id);
        setThinkingPlayer(msg.data.player_id);
      } else if (msg.type === 'player_action') {
        setThinkingPlayer(null);
        setLivePot(msg.data.pot_after || 0);
        setLiveActions(prev => [...prev, msg.data]);
      }
    };
    return () => ws.close();
  }, [sessionId]);

  // Auto-scroll live action log
  useEffect(() => {
    if (liveLogRef.current) {
      liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
    }
  }, [liveActions]);

  const handleStop = async () => {
    if (!sessionId) return;
    setStopping(true);
    try {
      await api.stopGame(sessionId);
    } catch (e: any) {
      alert(e.message);
      setStopping(false);
    }
  };

  const lastHand = selectedHand || (hands.length > 0 ? hands[hands.length - 1] : null);
  const isRunning = game?.status === 'running';
  const isLive = isRunning && (liveActions.length > 0 || thinkingPlayer);

  // Use live community cards during active play, otherwise last hand's
  const displayCommunity = isLive ? liveCommunity : (lastHand?.community_cards || []);
  const displayPot = isLive ? livePot : (lastHand?.pot_total || 0);

  return (
    <div>
      <div className="flex-between mb-16">
        <h1 className="page-title">Game: {sessionId}</h1>
        <div style={{display: 'flex', gap: 8, alignItems: 'center'}}>
          {isRunning && (
            <button
              className="btn btn-danger"
              onClick={handleStop}
              disabled={stopping}
              style={{padding: '8px 20px'}}
            >
              {stopping ? 'Stopping...' : 'Stop Game'}
            </button>
          )}
          <span className={`tag ${game?.status === 'finished' ? 'tag-expert' : 'tag-intermediate'}`}>
            {game?.status || 'loading'}
          </span>
        </div>
      </div>

      {/* Poker Table */}
      <div className="poker-table">
        {lastHand || isLive ? (
          <>
            <div className="pot-display">Pot: {displayPot}</div>
            <div className="community-cards">
              {displayCommunity.length > 0
                ? displayCommunity.map((c: string, i: number) => <CardView key={i} card={c} />)
                : [1,2,3,4,5].map(i => <CardView key={i} card="" />)
              }
            </div>
          </>
        ) : (
          <div className="pot-display">Waiting for game...</div>
        )}
      </div>

      {/* Seats with chip changes */}
      {game?.current_chips && (
        <div className="seats-container">
          {Object.entries(game.current_chips).map(([pid, chips]) => {
            const isThinking = thinkingPlayer === pid;
            const chipChange = lastHand?.chip_changes?.[pid];
            return (
              <div key={pid} className={`seat ${isThinking ? 'seat-thinking' : ''}`}>
                <div className="name">
                  {pid}
                  {isThinking && <span className="thinking-dot"> ...</span>}
                </div>
                <div className="chips">{String(chips)} chips</div>
                {chipChange != null && chipChange !== 0 && !isLive && (
                  <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                    {chipChange > 0 ? `+${chipChange}` : chipChange}
                  </div>
                )}
                {lastHand?.winners?.[pid] && !chipChange && (
                  <div className="text-green" style={{fontSize:'0.85rem'}}>+{lastHand.winners[pid]}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Live Action Stream (during game) */}
      {isRunning && (
        <div className="card">
          <h2>Live Actions {currentHandId ? `- Hand ${currentHandId}` : ''}</h2>
          {liveActions.length > 0 ? (
            <div className="timeline" ref={liveLogRef} style={{maxHeight: 300}}>
              {liveActions.map((a: any, i: number) => (
                <div key={i}>
                  <div className="timeline-item">
                    <span style={{width:70, color:'#64748b', fontWeight:600}}>{a.street}</span>
                    <span style={{width:90}}>{a.player_id}</span>
                    <ActionBadge action={a.action} />
                    {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
                    {a.round_bet > 0 && (
                      <span style={{marginLeft:8, fontSize:'0.75rem', color:'#94a3b8'}}>
                        Round: {a.round_bet}
                      </span>
                    )}
                    <span style={{marginLeft:'auto', fontSize:'0.75rem', color:'#64748b'}}>
                      Pot: {a.pot_after}
                    </span>
                  </div>
                  {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                </div>
              ))}
            </div>
          ) : thinkingPlayer ? (
            <p style={{color:'#94a3b8', padding: '12px'}}>{thinkingPlayer} is thinking...</p>
          ) : (
            <p className="empty-state">Waiting for actions...</p>
          )}
        </div>
      )}

      <div className="grid-2 mt-12">
        {/* Hand list */}
        <div className="card">
          <h2>Hands ({hands.length})</h2>
          <div className="timeline">
            {hands.map((h, i) => (
              <div key={h.hand_id} className="timeline-item" style={{cursor:'pointer'}}
                onClick={() => setSelectedHand(h)}>
                <span style={{width:30, color:'#64748b'}}>#{h.hand_number}</span>
                <span style={{flex:1}}>{h.community_cards?.join(' ') || 'no showdown'}</span>
                <span className="text-yellow">Pot: {h.pot_total}</span>
                <Link to={`/replay/${h.hand_id}`} className="btn btn-sm btn-primary" style={{marginLeft:8}}>Replay</Link>
              </div>
            ))}
          </div>
        </div>

        {/* Action log for selected hand */}
        <div className="card">
          <h2>Actions {selectedHand ? `- Hand #${selectedHand.hand_number}` : ''}</h2>

          {/* Chip changes summary */}
          {selectedHand?.chip_changes && (
            <div style={{display:'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap'}}>
              {Object.entries(selectedHand.chip_changes).map(([pid, change]: [string, any]) => (
                <span key={pid} style={{fontSize:'0.8rem'}}>
                  {pid}: <span className={change > 0 ? 'text-green' : change < 0 ? 'text-red' : 'text-yellow'}>
                    {change > 0 ? `+${change}` : change}
                  </span>
                </span>
              ))}
            </div>
          )}

          {selectedHand?.actions ? (
            <div className="timeline">
              {selectedHand.actions.map((a: any, i: number) => (
                <div key={i}>
                  <div className="timeline-item">
                    <span style={{width:70, color:'#64748b', fontWeight:600}}>{a.street}</span>
                    <span style={{width:90}}>{a.player_id}</span>
                    <ActionBadge action={a.action} />
                    {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
                    {a.round_bet > 0 && (
                      <span style={{marginLeft:8, fontSize:'0.75rem', color:'#94a3b8'}}>
                        Round: {a.round_bet}
                      </span>
                    )}
                    {a.is_timeout && <span className="badge badge-fold" style={{marginLeft:4}}>TIMEOUT</span>}
                    {a.input_tokens > 0 && (
                      <span style={{marginLeft:'auto', fontSize:'0.75rem', color:'#64748b'}}>
                        {a.input_tokens}+{a.output_tokens}tok / {a.llm_latency_ms?.toFixed(0)}ms
                      </span>
                    )}
                  </div>
                  {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                </div>
              ))}
            </div>
          ) : (
            <p className="empty-state">Select a hand to view actions</p>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/GamePlayPage.tsx
git commit -m "feat: real-time streaming game view with stop button and chip changes"
```

---

### Task 10: Frontend — ReplayPage Enhancements

**Files:**
- Modify: `frontend/src/pages/ReplayPage.tsx`

Add round-bet display in action detail and chip changes summary.

- [ ] **Step 1: Add round_bet to action detail table**

In `frontend/src/pages/ReplayPage.tsx`, in the Action Detail table (around line 166-167), add a row after the Action row:

Find this block:
```tsx
                <tr><td>Action</td><td><span className={`badge badge-${currentAction.action}`}>{currentAction.action}</span> {currentAction.amount > 0 && currentAction.amount}</td></tr>
                <tr><td>Pot After</td><td className="text-yellow">{currentAction.pot_after}</td></tr>
```

Replace with:
```tsx
                <tr><td>Action</td><td><span className={`badge badge-${currentAction.action}`}>{currentAction.action}</span> {currentAction.amount > 0 && currentAction.amount}</td></tr>
                {currentAction.round_bet > 0 && (
                  <tr><td>Round Bet</td><td className="text-cyan">{currentAction.round_bet}</td></tr>
                )}
                <tr><td>Pot After</td><td className="text-yellow">{currentAction.pot_after}</td></tr>
```

- [ ] **Step 2: Add chip changes summary section**

After the page title (line 71), add a chip changes summary card. Find:
```tsx
      <h1 className="page-title">Replay: Hand {hand.hand_id}</h1>
```

Replace with:
```tsx
      <h1 className="page-title">Replay: Hand {hand.hand_id}</h1>

      {/* Chip Changes Summary */}
      {hand.chip_changes && (
        <div className="card" style={{marginBottom: 16}}>
          <h2>Chip Changes</h2>
          <div style={{display: 'flex', gap: 20, flexWrap: 'wrap'}}>
            {Object.entries(hand.chip_changes).map(([pid, change]: [string, any]) => (
              <div key={pid} style={{textAlign: 'center'}}>
                <div style={{fontWeight: 600, fontSize: '0.9rem'}}>{pid}</div>
                <div className={change > 0 ? 'text-green' : change < 0 ? 'text-red' : 'text-yellow'}
                  style={{fontSize: '1.1rem', fontWeight: 700}}>
                  {change > 0 ? `+${change}` : change}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
```

- [ ] **Step 3: Add round_bet to the timeline items**

In the Full Timeline section (around line 201), find:
```tsx
              {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
```

Replace with:
```tsx
              {a.amount > 0 && <span className="text-yellow" style={{marginLeft:4}}>{a.amount}</span>}
              {a.round_bet > 0 && <span style={{marginLeft:4, fontSize:'0.75rem', color:'#94a3b8'}}>R:{a.round_bet}</span>}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ReplayPage.tsx
git commit -m "feat: add round-bet display and chip changes to replay page"
```

---

### Task 11: Frontend — CSS for Thinking Indicator and Chip Changes

**Files:**
- Modify: `frontend/src/App.css`

- [ ] **Step 1: Add CSS classes for new UI elements**

Append to the end of `frontend/src/App.css`:

```css

/* Thinking indicator */
.seat-thinking { border-color: #22d3ee; box-shadow: 0 0 12px #22d3ee44; }
.thinking-dot { color: #22d3ee; animation: pulse 1.2s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

/* Chip changes */
.chip-change-positive { color: #4ade80; font-size: 0.85rem; font-weight: 600; }
.chip-change-negative { color: #f87171; font-size: 0.85rem; font-weight: 600; }
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.css
git commit -m "feat: add CSS for thinking indicator and chip change display"
```

---

### Task 12: Backend — Include chip_changes in Replay API Response

**Files:**
- Modify: `backend/api/replay_routes.py`

The replay endpoint reads from DB where `actions_json` is stored. We need to also store and return `chip_changes`.

- [ ] **Step 1: Check replay routes**

Read `backend/api/replay_routes.py` to see what data is returned.

- [ ] **Step 2: Add chip_changes to DB schema and serialization**

In `backend/database.py`, add `chip_changes_json` column to the `hand_records` CREATE TABLE statement (after `player_cards_json`):

Find:
```python
            player_cards_json TEXT DEFAULT '{}',
```

Add after it:
```python
            chip_changes_json TEXT DEFAULT '{}',
```

In `backend/services/game_service.py`, update `_save_hand_to_db` to include chip_changes. Replace the INSERT statement (lines 219-230):

```python
def _save_hand_to_db(hand: dict) -> None:
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO hand_records (hand_id, session_id, hand_number, community_cards, pot_total, winners_json, actions_json, player_cards_json, chip_changes_json, started_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            hand["hand_id"], hand["session_id"], hand["hand_number"],
            json.dumps(hand["community_cards"]),
            hand["pot_total"],
            json.dumps(hand["winners"]),
            json.dumps(hand["actions"]),
            json.dumps(hand.get("player_cards", {})),
            json.dumps(hand.get("chip_changes", {})),
            now_iso(),
        ),
    )
    db.commit()
    db.close()
```

In `backend/api/replay_routes.py`, add `chip_changes` to the response. Find where the response dict is built and add:

```python
        "chip_changes": json.loads(row["chip_changes_json"]) if row["chip_changes_json"] else {},
```

- [ ] **Step 3: Handle DB migration for existing databases**

Since this is an SQLite project and the table uses `CREATE TABLE IF NOT EXISTS`, the simplest approach is to add the column with ALTER TABLE if it doesn't exist. In `backend/database.py`, after the CREATE TABLE statements, add:

```python
    # Migration: add chip_changes_json column if missing
    try:
        c.execute("ALTER TABLE hand_records ADD COLUMN chip_changes_json TEXT DEFAULT '{}'")
    except Exception:
        pass  # column already exists
```

- [ ] **Step 4: Verify existing tests pass**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/services/game_service.py backend/api/replay_routes.py
git commit -m "feat: persist and return chip_changes in hand records"
```

---

### Task 13: Full Integration Test — Run Backend and Verify

- [ ] **Step 1: Run all backend tests**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m pytest backend/tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Verify frontend builds**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw/frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 3: Final commit**

If any fixes were needed, commit them:

```bash
git add -A
git commit -m "fix: resolve any build/test issues from live game enhancements"
```
