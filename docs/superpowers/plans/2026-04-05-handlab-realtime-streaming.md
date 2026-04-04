# Hand Lab Real-Time Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Hand Lab stream poker events in real-time via WebSocket instead of returning all results after completion.

**Architecture:** Hand Lab creates a temporary `GameSession` stored in `_active_games`. Frontend connects via existing `/ws/game/{session_id}` WebSocket. A new `run_lab_game` function in `game_service.py` runs hands with preset cards and augments events with equity data before broadcasting. The frontend `HandLabPage.tsx` is rewritten to connect to WebSocket and render live events, matching `GamePlayPage`'s real-time rendering pattern.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript (frontend), existing WebSocket infrastructure

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/services/game_service.py` | Modify | Add `start_lab_session()`, `run_lab_game()`, extend `GameSession` with `lab_config`, modify `trigger_game_start()` |
| `backend/api/handlab_routes.py` | Modify | Add `POST /api/handlab/start` endpoint |
| `backend/services/hand_lab.py` | Modify | Extract `compute_equity()` as module-level function for reuse |
| `frontend/src/api/client.ts` | Modify | Add `startLab()` API method |
| `frontend/src/pages/HandLabPage.tsx` | Modify | Major rewrite: WebSocket connection, live state, state machine |
| `backend/tests/engine/test_hand_lab.py` | Modify | Add tests for `start_lab_session` and `run_lab_game` |

---

### Task 1: Extract equity computation to reusable function

**Files:**
- Modify: `backend/services/hand_lab.py`

The `_compute_equity` method on `HandLab` class needs to be callable from `game_service.py`. Extract it as a module-level function.

- [ ] **Step 1: Extract `_compute_equity` to module-level `compute_equity` function**

In `backend/services/hand_lab.py`, add this function at module level (after the imports, before the `PlayerSetup` class) and update the class method to delegate to it:

```python
def compute_equity(
    player_cards: dict[str, list[Card]],
    community: list[Card],
    folded: set[str],
    name_map: dict[str, str],
) -> list[dict]:
    """Compute equity for active (non-folded) players with known cards."""
    active_ids = [pid for pid in player_cards if pid not in folded and player_cards[pid]]
    if len(active_ids) < 2:
        return [
            {
                "player_id": name_map.get(pid, pid),
                "win_pct": 100.0 if pid in active_ids else 0.0,
                "tie_pct": 0.0,
            }
            for pid in player_cards
        ]

    active_cards = [player_cards[pid] for pid in active_ids]
    try:
        results = EquityCalculator.calculate(active_cards, community, num_simulations=2000)
    except (ValueError, Exception):
        return []

    equity = []
    active_idx = 0
    for pid in player_cards:
        if pid in folded or not player_cards[pid]:
            equity.append({"player_id": name_map.get(pid, pid), "win_pct": 0.0, "tie_pct": 0.0})
        else:
            r = results[active_idx]
            equity.append({
                "player_id": name_map.get(pid, pid),
                "win_pct": round(r.win_pct * 100, 1),
                "tie_pct": round(r.tie_pct * 100, 1),
            })
            active_idx += 1
    return equity
```

Then update the `HandLab` class `_compute_equity` method to just call it:

```python
def _compute_equity(self, player_cards, community, folded, name_map):
    return compute_equity(player_cards, community, folded, name_map)
```

- [ ] **Step 2: Run existing tests to verify no regression**

Run: `python -m pytest backend/tests/engine/test_hand_lab.py -v`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/services/hand_lab.py
git commit -m "refactor: extract compute_equity as module-level function for reuse"
```

---

### Task 2: Extend GameSession and add `start_lab_session` in game_service

**Files:**
- Modify: `backend/services/game_service.py`

- [ ] **Step 1: Add lab_config field to GameSession**

In `backend/services/game_service.py`, add an import for the types and a new field to the `GameSession` dataclass:

Add to the imports at the top:

```python
from backend.services.hand_lab import PlayerSetup, ScenarioConfig, compute_equity
from backend.engine.card import Card
from backend.engine.game_state import PlayerState
```

Add a new field to `GameSession`:

```python
@dataclass
class GameSession:
    session_id: str
    game: CashGame
    status: str = "waiting"
    hand_results: list[dict] = field(default_factory=list)
    on_event: Callable | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _num_hands: int = 10
    lab_config: ScenarioConfig | None = None  # NEW: set for Hand Lab sessions
```

- [ ] **Step 2: Add `start_lab_session` function**

Add after the `create_game` function in `backend/services/game_service.py`:

```python
def start_lab_session(config: ScenarioConfig, count: int = 1) -> GameSession:
    """Create a Hand Lab session that will stream events via WebSocket."""
    # Build name map
    name_map: dict[str, str] = {}
    for ps in config.players:
        name_map[ps.agent_id] = _get_agent_name(ps.agent_id)

    # Create CashGame with pacing delays
    game_config = CashGameConfig(
        small_blind=config.small_blind,
        big_blind=config.big_blind,
        street_delay_ms=1200.0,
        hand_delay_ms=2000.0,
    )
    game = CashGame(game_config)
    session_id = game.session_id

    # Add players with agents
    for ps in config.players:
        agent = create_agent_from_db(ps.agent_id)
        game.add_player(ps.agent_id, name_map[ps.agent_id], agent, buy_in=ps.chips)

    session = GameSession(
        session_id=session_id,
        game=game,
        status="pending_start",
        _num_hands=count,
        lab_config=config,
    )
    _active_games[session_id] = session
    return session
```

- [ ] **Step 3: Run existing tests to make sure nothing is broken**

Run: `python -m pytest backend/tests/ -v --timeout=30`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/services/game_service.py
git commit -m "feat: add lab_config to GameSession and start_lab_session function"
```

---

### Task 3: Add `run_lab_game` function

**Files:**
- Modify: `backend/services/game_service.py`

- [ ] **Step 1: Add `run_lab_game` function**

Add after `run_game` in `backend/services/game_service.py`:

```python
async def run_lab_game(session_id: str) -> dict:
    """Run a Hand Lab session: execute hands with preset cards, streaming events via WebSocket."""
    session = _active_games.get(session_id)
    if not session or not session.lab_config:
        raise ValueError(f"Lab session {session_id} not found")

    config = session.lab_config
    num_hands = session._num_hands
    session.status = "running"

    # Parse preset cards once
    preset_hole: dict[str, list[Card]] = {}
    all_preset_cards: list[Card] = []
    for p in config.players:
        if p.hole_cards:
            cards = [Card.from_string(c) for c in p.hole_cards]
            preset_hole[p.agent_id] = cards
            all_preset_cards.extend(cards)

    preset_community = [Card.from_string(c) for c in config.community_cards]
    all_preset_cards.extend(preset_community)

    name_map: dict[str, str] = {
        ps.agent_id: _get_agent_name(ps.agent_id) for ps in config.players
    }

    hand_num = 0
    all_hand_results: list[dict] = []

    for _ in range(num_hands):
        if session.stop_event.is_set():
            break

        hand_num += 1
        # Capture starting chips
        starting_chips = {p.player_id: p.chips for p in session.game.players}

        # Prepare players for this hand
        hand_players = []
        for p in session.game.players:
            if p.chips <= 0:
                continue
            ps = PlayerState(
                player_id=p.player_id,
                display_name=p.display_name,
                chips=p.chips,
                seat_index=p.seat_index,
                hole_cards=list(preset_hole.get(p.player_id, [])),
            )
            hand_players.append(ps)

        if len(hand_players) < 2:
            break

        active_agents = {p.player_id: session.game.agents[p.player_id] for p in hand_players}
        runner = GameRunner(
            players=hand_players,
            agents=active_agents,
            small_blind=config.small_blind,
            big_blind=config.big_blind,
            dealer_index=session.game.dealer_index % len(hand_players),
            street_delay_ms=session.game.config.street_delay_ms,
        )

        # Remove preset cards from deck
        if all_preset_cards:
            runner.deck.remove_cards(all_preset_cards)
        # Preset community cards
        if preset_community:
            runner.state.community_cards = list(preset_community)

        # Track equity state for this hand
        folded: set[str] = set()
        live_player_cards: dict[str, list[Card]] = {}

        async def on_action(event: dict, _folded=folded, _live_cards=live_player_cards, _runner=runner) -> None:
            etype = event.get("type")
            data = event.get("data", {})

            if etype == "hand_start":
                # Collect hole cards for equity
                for pid, info in data.get("players", {}).items():
                    for ps in config.players:
                        if name_map[ps.agent_id] == pid:
                            hole = info.get("hole_cards", [])
                            if hole:
                                _live_cards[ps.agent_id] = [Card.from_string(c) for c in hole]
                            break
                # Augment with equity
                equity = compute_equity(
                    _live_cards, list(_runner.state.community_cards), _folded, name_map,
                )
                event["data"]["equity"] = equity

            elif etype == "street_start":
                equity = compute_equity(
                    _live_cards, list(_runner.state.community_cards), _folded, name_map,
                )
                event["data"]["equity"] = equity

            elif etype == "player_action":
                display_pid = data.get("player_id", "")
                if data.get("action") == "fold":
                    for ps in config.players:
                        if name_map[ps.agent_id] == display_pid:
                            _folded.add(ps.agent_id)
                            break

            # Broadcast via WebSocket
            if session.on_event:
                await session.on_event(event)

        runner.on_action = on_action
        result = await runner.run_hand()

        # Sync chips back
        for p in session.game.players:
            if p.player_id in result.final_chips:
                p.chips = result.final_chips[p.player_id]

        # Compute chip changes
        chip_changes = {}
        for p in session.game.players:
            start = starting_chips.get(p.player_id, 0)
            chip_changes[p.player_id] = p.chips - start
        result.starting_chips = starting_chips
        result.chip_changes = chip_changes

        session.game.dealer_index = (session.game.dealer_index + 1) % len(session.game.players)

        # Build hand_complete data
        hand_data = _serialize_hand(result, session_id, hand_num)

        # Add equity to hand_complete
        final_equity = compute_equity(
            live_player_cards, list(result.community_cards), folded, name_map,
        )
        hand_data["equity"] = final_equity

        session.hand_results.append(hand_data)
        all_hand_results.append(hand_data)

        if session.on_event:
            await session.on_event({"type": "hand_complete", "data": hand_data})

        # Reset per-hand tracking for next hand
        folded.clear()
        live_player_cards.clear()

        # Pause between hands
        if session.game.config.hand_delay_ms > 0 and hand_num < num_hands:
            await asyncio.sleep(session.game.config.hand_delay_ms / 1000)

    # Build summary for multi-run
    session.status = "finished"
    player_names = [name_map[ps.agent_id] for ps in config.players]
    summary = None
    if num_hands > 1:
        from backend.services.hand_lab import _build_summary
        summary = _build_summary(all_hand_results, player_names)

    if session.on_event:
        await session.on_event({
            "type": "lab_finished",
            "data": {
                "session_id": session_id,
                "total_hands": hand_num,
                "final_chips": {name_map.get(p.player_id, p.player_id): p.chips for p in session.game.players},
                "summary": summary,
            },
        })

    return {"session_id": session_id, "total_hands": hand_num}
```

- [ ] **Step 2: Modify `trigger_game_start` to detect lab sessions**

Replace the existing `trigger_game_start` function:

```python
def trigger_game_start(session_id: str) -> bool:
    """Called by WebSocket handler to start the game after on_event is registered.
    Returns True if game was started, False if already running/finished."""
    session = _active_games.get(session_id)
    if not session or session.status != "pending_start":
        return False
    if not session.on_event:
        return False
    # Launch game as background task — lab or regular
    if session.lab_config:
        asyncio.create_task(run_lab_game(session_id))
    else:
        asyncio.create_task(run_game(session_id, session._num_hands))
    return True
```

- [ ] **Step 3: Run existing tests**

Run: `python -m pytest backend/tests/ -v --timeout=30`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/services/game_service.py
git commit -m "feat: add run_lab_game for WebSocket-streamed Hand Lab sessions"
```

---

### Task 4: Add `POST /api/handlab/start` endpoint

**Files:**
- Modify: `backend/api/handlab_routes.py`

- [ ] **Step 1: Add the start endpoint**

In `backend/api/handlab_routes.py`, add a new request model and endpoint:

Add import at top:

```python
from backend.services import game_service
```

Add new request model after `RunMultipleRequest`:

```python
class StartLabRequest(BaseModel):
    scenario: ScenarioRequest
    count: int = 1
```

Add new endpoint after the existing routes:

```python
@router.post("/start")
def start_lab(body: StartLabRequest):
    try:
        config = _to_config(body.scenario)
        session = game_service.start_lab_session(config, count=body.count)
        return {"session_id": session.session_id}
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 2: Verify the server starts without errors**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -c "from backend.api.handlab_routes import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/api/handlab_routes.py
git commit -m "feat: add POST /api/handlab/start endpoint for WebSocket streaming"
```

---

### Task 5: Add `startLab` to frontend API client

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `startLab` method**

In `frontend/src/api/client.ts`, add inside the `api` object after `runLabMultiple`:

```typescript
  // Hand Lab streaming
  startLab: (data: { scenario: any; count?: number }) =>
    request<{ session_id: string }>('/api/handlab/start', { method: 'POST', body: JSON.stringify(data) }),
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add startLab API method for streaming Hand Lab"
```

---

### Task 6: Rewrite HandLabPage for real-time streaming

**Files:**
- Modify: `frontend/src/pages/HandLabPage.tsx`

This is the largest task. The page needs a state machine:
- **Setup**: Scenario config (keep existing)
- **Live**: WebSocket streaming, poker table, live actions, equity
- **Finished**: Summary + replay

- [ ] **Step 1: Rewrite HandLabPage.tsx**

Replace the entire contents of `frontend/src/pages/HandLabPage.tsx` with:

```tsx
import { useEffect, useState, useRef, useCallback } from 'react';
import { api, createGameWS } from '../api/client';
import CardPicker from '../components/CardPicker';

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

function EquityBar({ winPct, label }: { winPct: number; label: string }) {
  const color = winPct > 60 ? '#22c55e' : winPct > 30 ? '#eab308' : winPct > 0 ? '#f87171' : '#334155';
  return (
    <div style={{ marginTop: 4 }}>
      <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginBottom: 2 }}>{label}: {winPct}%</div>
      <div style={{ background: '#334155', borderRadius: 4, height: 6, width: 100 }}>
        <div style={{
          background: color, borderRadius: 4, height: 6,
          width: `${winPct}%`, transition: 'width 0.5s ease, background 0.5s ease',
        }} />
      </div>
    </div>
  );
}

interface PlayerConfig {
  agent_id: string;
  chips: number;
  hole_cards: string[];
}

type LabPhase = 'setup' | 'live' | 'finished';

export default function HandLabPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [players, setPlayers] = useState<PlayerConfig[]>([
    { agent_id: '', chips: 5000, hole_cards: [] },
    { agent_id: '', chips: 5000, hole_cards: [] },
  ]);
  const [communityCards, setCommunityCards] = useState<string[]>([]);
  const [smallBlind, setSmallBlind] = useState(50);
  const [bigBlind, setBigBlind] = useState(100);
  const [runCount, setRunCount] = useState(10);
  const [loading, setLoading] = useState(false);

  // State machine
  const [phase, setPhase] = useState<LabPhase>('setup');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Live state (during WebSocket streaming)
  const [liveActions, setLiveActions] = useState<any[]>([]);
  const [liveCommunity, setLiveCommunity] = useState<string[]>([]);
  const [livePot, setLivePot] = useState(0);
  const [liveEquity, setLiveEquity] = useState<any[]>([]);
  const [livePlayerCards, setLivePlayerCards] = useState<Record<string, any>>({});
  const [thinkingPlayer, setThinkingPlayer] = useState<string | null>(null);
  const [handInProgress, setHandInProgress] = useState(false);
  const [currentHandNum, setCurrentHandNum] = useState(0);
  const [totalHands, setTotalHands] = useState(1);

  // Completed hands + summary
  const [completedHands, setCompletedHands] = useState<any[]>([]);
  const [multiSummary, setMultiSummary] = useState<any>(null);
  const [selectedHandIdx, setSelectedHandIdx] = useState<number | null>(null);

  // Step playback for reviewing completed hands
  const [currentStep, setCurrentStep] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<any>(null);
  const PLAYBACK_SPEED = 600;

  const liveLogRef = useRef<HTMLDivElement>(null);

  useEffect(() => { api.listAgents().then(setAgents).catch(() => {}); }, []);

  // Auto-scroll live log
  useEffect(() => {
    if (liveLogRef.current) {
      liveLogRef.current.scrollTop = liveLogRef.current.scrollHeight;
    }
  }, [liveActions]);

  const allUsedCards = [...communityCards, ...players.flatMap(p => p.hole_cards)];

  const updatePlayer = (idx: number, update: Partial<PlayerConfig>) => {
    setPlayers(prev => prev.map((p, i) => i === idx ? { ...p, ...update } : p));
  };
  const addPlayer = () => { if (players.length < 6) setPlayers(prev => [...prev, { agent_id: '', chips: 5000, hole_cards: [] }]); };
  const removePlayer = (idx: number) => { if (players.length > 2) setPlayers(prev => prev.filter((_, i) => i !== idx)); };
  const canRun = players.every(p => p.agent_id) && players.length >= 2;

  const buildScenario = () => ({
    players: players.map((p, i) => ({ agent_id: p.agent_id, chips: p.chips, hole_cards: p.hole_cards, seat_index: i })),
    community_cards: communityCards, small_blind: smallBlind, big_blind: bigBlind, dealer_index: 0,
  });

  const cleanupWs = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const handleStart = async (count: number) => {
    setLoading(true);
    setCompletedHands([]);
    setMultiSummary(null);
    setSelectedHandIdx(null);
    setCurrentHandNum(0);
    setTotalHands(count);

    try {
      const { session_id } = await api.startLab({ scenario: buildScenario(), count });
      setSessionId(session_id);
      setPhase('live');

      // Connect WebSocket
      const ws = createGameWS(session_id);
      wsRef.current = ws;

      ws.onopen = () => { console.log('[Lab WS] connected'); };
      ws.onclose = () => { console.log('[Lab WS] disconnected'); };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        console.log('[Lab WS] event:', msg.type);

        if (msg.type === 'hand_start') {
          setHandInProgress(true);
          setCurrentHandNum(prev => prev + 1);
          const playerCards: Record<string, any> = {};
          const playersData = msg.data.players || {};
          for (const [name, info] of Object.entries(playersData) as [string, any][]) {
            playerCards[name] = { hole_cards: info.hole_cards || [], chips: info.chips };
          }
          setLivePlayerCards(playerCards);
          setLivePot(msg.data.pot || 0);
          setLiveActions([]);
          setLiveCommunity([]);
          setThinkingPlayer(null);
          setLiveEquity(msg.data.equity || []);

        } else if (msg.type === 'street_start') {
          setLiveCommunity(msg.data.community_cards || []);
          setLivePot(msg.data.pot || 0);
          setThinkingPlayer(null);
          if (msg.data.equity) setLiveEquity(msg.data.equity);

        } else if (msg.type === 'player_thinking') {
          setThinkingPlayer(msg.data.player_id);

        } else if (msg.type === 'player_action') {
          setThinkingPlayer(null);
          setLivePot(msg.data.pot_after || 0);
          setLiveActions(prev => [...prev, msg.data]);

        } else if (msg.type === 'hand_complete') {
          setHandInProgress(false);
          setThinkingPlayer(null);
          setCompletedHands(prev => [...prev, msg.data]);

        } else if (msg.type === 'lab_finished') {
          setPhase('finished');
          if (msg.data.summary) setMultiSummary(msg.data.summary);
          setHandInProgress(false);
          setThinkingPlayer(null);
          cleanupWs();
        }
      };
    } catch (e: any) {
      alert(e.message);
      setPhase('setup');
    }
    setLoading(false);
  };

  const handleStop = () => {
    if (sessionId) {
      api.stopGame(sessionId).catch(() => {});
    }
  };

  const handleBackToSetup = () => {
    cleanupWs();
    setPhase('setup');
    setSessionId(null);
    setCompletedHands([]);
    setMultiSummary(null);
    setSelectedHandIdx(null);
    setLiveActions([]);
    setLiveCommunity([]);
    setLivePot(0);
    setLiveEquity([]);
    setLivePlayerCards({});
    setThinkingPlayer(null);
    setHandInProgress(false);
    setCurrentHandNum(0);
  };

  // Cleanup WebSocket on unmount
  useEffect(() => { return () => cleanupWs(); }, [cleanupWs]);

  // Get equity for a player
  const getEquity = (name: string, eqList: any[]) => {
    const eq = eqList.find((e: any) => e.player_id === name);
    return eq ? eq.win_pct : null;
  };

  // Review a completed hand with step playback
  const selectedHand = selectedHandIdx != null ? completedHands[selectedHandIdx] : null;

  // -- RENDER --
  return (
    <div>
      <h1 className="page-title">Hand Lab</h1>

      {/* === SETUP PHASE === */}
      {phase === 'setup' && (
        <div className="card">
          <h2>Scenario Setup</h2>
          {players.map((p, idx) => (
            <div key={idx} style={{
              display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 12,
              padding: 12, background: '#0f172a', borderRadius: 8,
            }}>
              <div style={{ minWidth: 60 }}>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Player {idx + 1}</label>
                <select value={p.agent_id} onChange={e => updatePlayer(idx, { agent_id: e.target.value })}
                  style={{ width: '100%', marginTop: 4 }}>
                  <option value="">Select agent</option>
                  {agents.map(a => <option key={a.agent_id} value={a.agent_id}>{a.display_name}</option>)}
                </select>
              </div>
              <div style={{ minWidth: 80 }}>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Chips</label>
                <input type="number" value={p.chips} onChange={e => updatePlayer(idx, { chips: +e.target.value })}
                  style={{ width: 80, marginTop: 4 }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Hole Cards</label>
                <CardPicker selectedCards={p.hole_cards} maxCards={2} usedCards={allUsedCards}
                  onChange={cards => updatePlayer(idx, { hole_cards: cards })} />
              </div>
              {players.length > 2 && (
                <button onClick={() => removePlayer(idx)}
                  style={{ padding: '4px 8px', color: '#f87171', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.1rem' }}>x</button>
              )}
            </div>
          ))}
          {players.length < 6 && <button className="btn btn-sm" onClick={addPlayer} style={{ marginBottom: 12 }}>+ Add Player</button>}

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Community Cards (optional, 0-5)</label>
            <CardPicker selectedCards={communityCards} maxCards={5} usedCards={allUsedCards} onChange={setCommunityCards} />
          </div>

          <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Small Blind</label>
              <input type="number" value={smallBlind} onChange={e => setSmallBlind(+e.target.value)} style={{ width: 80 }} />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Big Blind</label>
              <input type="number" value={bigBlind} onChange={e => setBigBlind(+e.target.value)} style={{ width: 80 }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <button className="btn btn-primary" onClick={() => handleStart(1)} disabled={!canRun || loading}>
              {loading ? 'Starting...' : 'Run Once'}
            </button>
            <button className="btn btn-primary" onClick={() => handleStart(runCount)} disabled={!canRun || loading}
              style={{ background: '#7c3aed' }}>
              Run {runCount} Times
            </button>
            <input type="number" value={runCount} onChange={e => setRunCount(+e.target.value)} min={2} max={100} style={{ width: 60 }} />
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>times</span>
          </div>
        </div>
      )}

      {/* === LIVE PHASE === */}
      {phase === 'live' && (
        <>
          <div className="card">
            <div className="flex-between mb-16">
              <h2>
                Live {totalHands > 1 ? `- Hand ${currentHandNum} / ${totalHands}` : ''}
              </h2>
              <button className="btn btn-danger" onClick={handleStop} style={{ padding: '8px 16px' }}>
                Stop
              </button>
            </div>

            {/* Poker Table */}
            <div className="poker-table" style={{ marginBottom: 16 }}>
              <div className="pot-display">Pot: {livePot}</div>
              <div className="community-cards">
                {liveCommunity.length > 0
                  ? liveCommunity.map((c, i) => <CardView key={i} card={c} />)
                  : [1, 2, 3, 4, 5].map(i => <CardView key={i} card="" />)
                }
              </div>
            </div>

            {/* Player Seats */}
            <div className="seats-container" style={{ marginBottom: 16 }}>
              {Object.entries(livePlayerCards).map(([pid, info]: [string, any]) => {
                const eq = getEquity(pid, liveEquity);
                const isThinking = thinkingPlayer === pid;
                const isFolded = liveActions.some((a: any) => a.player_id === pid && a.action === 'fold');
                return (
                  <div key={pid} className={`seat ${isThinking ? 'seat-thinking' : ''} ${isFolded ? 'seat-folded' : ''}`}>
                    <div className="name">
                      {pid}
                      {isThinking && <span className="thinking-dot"> ...</span>}
                    </div>
                    <div className="hole-cards">
                      {(info.hole_cards || []).map((c: string, i: number) => <CardView key={i} card={c} />)}
                    </div>
                    {eq != null && <EquityBar winPct={eq} label="Win" />}
                    <div className="chips">{info.chips} chips</div>
                  </div>
                );
              })}
            </div>

            {/* Live Action Stream */}
            {liveActions.length > 0 ? (
              <div className="timeline" ref={liveLogRef} style={{ maxHeight: 300, overflowY: 'auto' }}>
                {liveActions.map((a: any, i: number) => (
                  <div key={i}>
                    <div className="timeline-item">
                      <span style={{ width: 70, color: '#64748b', fontWeight: 600 }}>{a.street}</span>
                      <span style={{ width: 90 }}>{a.player_id}</span>
                      <ActionBadge action={a.action} />
                      {a.amount > 0 && <span className="text-yellow" style={{ marginLeft: 4 }}>{a.amount}</span>}
                      {a.round_bet > 0 && (
                        <span style={{ marginLeft: 8, fontSize: '0.75rem', color: '#94a3b8' }}>Round: {a.round_bet}</span>
                      )}
                      <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#64748b' }}>Pot: {a.pot_after}</span>
                    </div>
                    {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                  </div>
                ))}
              </div>
            ) : thinkingPlayer ? (
              <p style={{ color: '#94a3b8', padding: '12px' }}>{thinkingPlayer} is thinking...</p>
            ) : handInProgress ? (
              <p style={{ color: '#94a3b8', padding: '12px' }}>Cards dealt, waiting for actions...</p>
            ) : (
              <p className="empty-state">Waiting for hand to start...</p>
            )}
          </div>

          {/* Completed Hands So Far (during multi-run) */}
          {completedHands.length > 0 && totalHands > 1 && (
            <div className="card">
              <h2>Completed Hands ({completedHands.length})</h2>
              <div className="timeline">
                {completedHands.map((h, i) => (
                  <div key={i} className="timeline-item">
                    <span style={{ width: 30, color: '#64748b' }}>#{i + 1}</span>
                    <span style={{ flex: 1 }}>{h.community_cards?.join(' ') || 'no showdown'}</span>
                    <span className="text-yellow">Pot: {h.pot_total}</span>
                    {Object.entries(h.winners || {}).map(([name, amt]: [string, any]) => (
                      <span key={name} className="text-green" style={{ marginLeft: 8 }}>{name} +{amt}</span>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* === FINISHED PHASE === */}
      {phase === 'finished' && (
        <>
          <div style={{ marginBottom: 16 }}>
            <button className="btn btn-primary" onClick={handleBackToSetup}>
              Back to Setup
            </button>
          </div>

          {/* Multi-Run Summary */}
          {multiSummary && (
            <div className="card">
              <h2>Summary ({multiSummary.total_runs} runs)</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
                {Object.entries(multiSummary.win_rate || {}).map(([name, rate]: [string, any]) => (
                  <div key={name} style={{ background: '#0f172a', padding: 16, borderRadius: 8 }}>
                    <div style={{ fontWeight: 700, marginBottom: 8 }}>{name}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#94a3b8' }}>Win Rate</span>
                      <span className="text-green">{rate}%</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ color: '#94a3b8' }}>Avg Profit</span>
                      <span className={multiSummary.avg_profit[name] >= 0 ? 'text-green' : 'text-red'}>
                        {multiSummary.avg_profit[name] >= 0 ? '+' : ''}{multiSummary.avg_profit[name]}
                      </span>
                    </div>
                    <div style={{ background: '#334155', borderRadius: 4, height: 8, marginTop: 8 }}>
                      <div style={{ background: '#22c55e', borderRadius: 4, height: 8, width: `${rate}%`, transition: 'width 0.3s' }} />
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                Average Pot: {multiSummary.avg_pot}
              </div>
            </div>
          )}

          {/* Hand List + Detail */}
          {completedHands.length > 0 && (
            <div className="card">
              <h2>Hands ({completedHands.length})</h2>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 16 }}>
                {completedHands.map((h, i) => (
                  <button key={i}
                    className={`btn btn-sm ${selectedHandIdx === i ? 'btn-primary' : ''}`}
                    onClick={() => setSelectedHandIdx(i)}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', minWidth: 44 }}>
                    #{i + 1}
                  </button>
                ))}
              </div>

              {selectedHand && (
                <>
                  {/* Poker Table for selected hand */}
                  <div className="poker-table" style={{ marginBottom: 16 }}>
                    <div className="pot-display">Pot: {selectedHand.pot_total}</div>
                    <div className="community-cards">
                      {(selectedHand.community_cards || []).map((c: string, i: number) => <CardView key={i} card={c} />)}
                    </div>
                  </div>

                  {/* Player results */}
                  <div className="seats-container" style={{ marginBottom: 16 }}>
                    {Object.entries(selectedHand.player_cards || {}).map(([pid, cards]: [string, any]) => {
                      const isWinner = selectedHand.winners && selectedHand.winners[pid];
                      const chipChange = selectedHand.chip_changes?.[pid];
                      const eq = selectedHand.equity ? getEquity(pid, selectedHand.equity) : null;
                      return (
                        <div key={pid} className="seat"
                          style={isWinner ? { border: '2px solid #22c55e' } : {}}>
                          <div className="name">{pid}</div>
                          <div className="hole-cards">
                            {cards.map((c: string, i: number) => <CardView key={i} card={c} />)}
                          </div>
                          {eq != null && <EquityBar winPct={eq} label="Win" />}
                          <div className="chips">{selectedHand.final_chips?.[pid]} chips</div>
                          {chipChange != null && chipChange !== 0 && (
                            <div className={chipChange > 0 ? 'chip-change-positive' : 'chip-change-negative'}>
                              {chipChange > 0 ? `+${chipChange}` : chipChange}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Action log for selected hand */}
                  {selectedHand.actions?.length > 0 && (
                    <div className="timeline" style={{ maxHeight: 300, overflowY: 'auto' }}>
                      {selectedHand.actions.map((a: any, i: number) => (
                        <div key={i}>
                          <div className="timeline-item">
                            <span style={{ width: 70, color: '#64748b', fontWeight: 600 }}>{a.street}</span>
                            <span style={{ width: 90 }}>{a.player_id}</span>
                            <ActionBadge action={a.action} />
                            {a.amount > 0 && <span className="text-yellow" style={{ marginLeft: 4 }}>{a.amount}</span>}
                            {a.round_bet > 0 && (
                              <span style={{ marginLeft: 8, fontSize: '0.75rem', color: '#94a3b8' }}>Round: {a.round_bet}</span>
                            )}
                            <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#64748b' }}>Pot: {a.pot_after}</span>
                          </div>
                          {a.thinking && <div className="thinking-panel">{a.thinking}</div>}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend compiles**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw/frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors (or only pre-existing warnings)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HandLabPage.tsx
git commit -m "feat: rewrite HandLabPage for real-time WebSocket streaming"
```

---

### Task 7: Add `stopGame` for lab sessions (use existing endpoint)

**Files:**
- Modify: `backend/services/game_service.py`

The `stop_game` function already works for any session in `_active_games`. Since `start_lab_session` registers the session there, stopping already works. The frontend already calls `api.stopGame(sessionId)` which hits `POST /api/games/{session_id}/stop`.

However, we need `get_session` to return lab sessions too — and `get_game` endpoint needs to handle lab sessions gracefully.

- [ ] **Step 1: Verify stop works for lab sessions**

No code changes needed — `stop_game` checks `_active_games` which includes lab sessions. The `stop_event` is set, and `run_lab_game` checks it at the top of each hand loop.

- [ ] **Step 2: Run full backend test suite**

Run: `python -m pytest backend/tests/ -v --timeout=30`
Expected: All tests PASS

- [ ] **Step 3: Commit (only if any changes needed)**

Skip if no changes were needed.

---

### Task 8: Integration test

**Files:**
- Modify: `backend/tests/engine/test_hand_lab.py`

- [ ] **Step 1: Add test for `start_lab_session`**

Add to `backend/tests/engine/test_hand_lab.py`:

```python
import asyncio
from unittest.mock import patch, MagicMock
from backend.services.game_service import start_lab_session, run_lab_game, _active_games


class TestLabStreaming:
    """Test the streaming lab session setup."""

    @patch("backend.services.game_service.create_agent_from_db")
    @patch("backend.services.game_service._get_agent_name")
    def test_start_lab_session_creates_session(self, mock_name, mock_agent):
        mock_name.side_effect = lambda aid: f"Agent-{aid}"
        mock_agent.side_effect = lambda aid: _make_agent(aid, f"Agent-{aid}")

        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", chips=5000, hole_cards=["Ah", "Kd"]),
                PlayerSetup(agent_id="a2", chips=5000, hole_cards=["Qs", "Qc"]),
            ],
            community_cards=["Ts", "Js", "2d"],
        )
        session = start_lab_session(config, count=3)

        assert session.session_id in _active_games
        assert session.lab_config is config
        assert session._num_hands == 3
        assert session.status == "pending_start"
        assert len(session.game.players) == 2

        # Cleanup
        del _active_games[session.session_id]

    @patch("backend.services.game_service.create_agent_from_db")
    @patch("backend.services.game_service._get_agent_name")
    @pytest.mark.asyncio
    async def test_run_lab_game_streams_events(self, mock_name, mock_agent):
        mock_name.side_effect = lambda aid: f"Agent-{aid}"
        mock_agent.side_effect = lambda aid: _make_agent(aid, f"Agent-{aid}")

        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", chips=5000, hole_cards=["Ah", "Kd"]),
                PlayerSetup(agent_id="a2", chips=5000, hole_cards=["Qs", "Qc"]),
            ],
        )
        session = start_lab_session(config, count=1)

        # Collect events
        events: list[dict] = []
        async def collect(event: dict):
            events.append(event)
        session.on_event = collect

        await run_lab_game(session.session_id)

        # Should have received standard event types
        event_types = [e["type"] for e in events]
        assert "hand_start" in event_types
        assert "hand_complete" in event_types
        assert "lab_finished" in event_types

        # hand_start should have equity
        hand_start = next(e for e in events if e["type"] == "hand_start")
        assert "equity" in hand_start["data"]

        # lab_finished should have no summary for single run
        lab_finished = next(e for e in events if e["type"] == "lab_finished")
        assert lab_finished["data"]["total_hands"] == 1

        # Cleanup
        del _active_games[session.session_id]

    @patch("backend.services.game_service.create_agent_from_db")
    @patch("backend.services.game_service._get_agent_name")
    @pytest.mark.asyncio
    async def test_run_lab_game_multiple_hands_has_summary(self, mock_name, mock_agent):
        mock_name.side_effect = lambda aid: f"Agent-{aid}"
        mock_agent.side_effect = lambda aid: _make_agent(aid, f"Agent-{aid}")

        config = ScenarioConfig(
            players=[
                PlayerSetup(agent_id="a1", chips=5000),
                PlayerSetup(agent_id="a2", chips=5000),
            ],
        )
        session = start_lab_session(config, count=3)

        events: list[dict] = []
        async def collect(event: dict):
            events.append(event)
        session.on_event = collect

        await run_lab_game(session.session_id)

        # Should have 3 hand_complete events
        hand_completes = [e for e in events if e["type"] == "hand_complete"]
        assert len(hand_completes) == 3

        # lab_finished should have summary
        lab_finished = next(e for e in events if e["type"] == "lab_finished")
        assert lab_finished["data"]["summary"] is not None
        assert lab_finished["data"]["summary"]["total_runs"] == 3
        assert "win_rate" in lab_finished["data"]["summary"]

        # Cleanup
        del _active_games[session.session_id]
```

- [ ] **Step 2: Run the new tests**

Run: `python -m pytest backend/tests/engine/test_hand_lab.py::TestLabStreaming -v --timeout=60`
Expected: All 3 tests PASS

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `python -m pytest backend/tests/ -v --timeout=60`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/engine/test_hand_lab.py
git commit -m "test: add integration tests for Hand Lab WebSocket streaming"
```

---

### Task 9: Manual end-to-end test

- [ ] **Step 1: Start the backend**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw && python -m backend.main`
Verify: Server starts on port 8000

- [ ] **Step 2: Start the frontend**

Run: `cd c:/Users/X1C-G9/Documents/claudecode/PokerClaw/frontend && npm run dev`
Verify: Dev server starts

- [ ] **Step 3: Test Run Once**

1. Navigate to Hand Lab page
2. Select 2 agents, optionally set hole cards
3. Click "Run Once"
4. Verify: Live table appears, cards dealt, thinking animations, actions appear in real-time, community cards revealed progressively, hand completes and transitions to Finished phase

- [ ] **Step 4: Test Run N Times**

1. Back to Setup
2. Click "Run 3 Times"
3. Verify: Hands play live one after another with hand counter updating, completed hands list grows during play, after all 3 finish summary appears with win rates

- [ ] **Step 5: Test Stop**

1. Back to Setup, start "Run 10 Times"
2. Click Stop during play
3. Verify: Current hand finishes, then transitions to Finished with partial results

- [ ] **Step 6: Commit final state**

```bash
git add -A
git commit -m "feat: Hand Lab real-time WebSocket streaming complete"
```
