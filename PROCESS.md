# PokerClaw Development Progress

## Project Overview
Texas Hold'em poker agent platform with LLM-powered agents, hand replay, monitoring, and Hand Lab for scenario testing.

---

## Completed Tasks

### Phase 1: Project Setup & Documentation
- [x] Created PRD.md, SYSTEM_DESIGN.md, TEST_ANALYSIS.md
- [x] Initialized Git repository
- [x] Created project structure (backend/, frontend/, docs/)

### Phase 2: Poker Engine Core
- [x] Card, Deck, HandEvaluator (10 hand ranks, 7选5)
- [x] PotManager with side pot calculation
- [x] BettingRound with 4-raise cap
- [x] GameState management
- [x] GameRunner for single hand execution
- [x] CashGame for multi-hand sessions
- [x] All engine tests passing (40+ tests)

### Phase 3: Agent System
- [x] BaseAgent interface
- [x] LLMCallResult dataclass
- [x] LLM Provider interface with factory pattern
- [x] AnthropicProvider implementation
- [x] MockLLMProvider for testing
- [x] Personality templates (TAG/LAG/fish/rock/calling_station/maniac)
- [x] Decision context builder
- [x] Action parser for LLM output
- [x] LLMAgent with 30s timeout + 1 retry + fallback
- [x] Agent monitoring (decisions, tokens, latency)

### Phase 4: Backend API
- [x] FastAPI main application with CORS
- [x] Database schema (SQLite) - agents, sessions, hands, llm_logs, decisions
- [x] Game service with background task runner
- [x] Agent CRUD API routes
- [x] Game creation/start routes
- [x] Monitoring/metrics routes
- [x] WebSocket handler for real-time updates
- [x] All backend tests passing (77 total)

### Phase 5: Frontend Implementation
- [x] React + TypeScript + Vite setup
- [x] React Router configuration (6 routes)
- [x] API client with all endpoints
- [x] Dashboard page with stats
- [x] Agent management page (CRUD + personality)
- [x] Game setup page (agent selection, blind config)
- [x] Game play page (poker table, WebSocket, action log)
- [x] Replay page (step-by-step navigation)
- [x] Monitoring page (provider status, agent metrics drill-down)
- [x] Dark theme CSS styling
- [x] TypeScript compilation passes

### Phase 6: CLI Prototype
- [x] run_cli_game.py for testing without frontend
- [x] Verified working with 3 hands, 4 players

### Phase 7: Integration & E2E Testing
- [x] Install FastAPI dependencies (fastapi, uvicorn, sqlalchemy, pydantic, anthropic)
- [x] Start backend server on http://localhost:8000
- [x] Start frontend dev server on http://localhost:5173
- [x] Verified API endpoints responding (/api/agents, /api/games, /api/monitoring/*)
- [x] WebSocket endpoint available at /ws/games/{session_id}

---

## In Progress Tasks

None - all planned features for MVP completed.

## Running the Application

### Backend
```bash
cd /c/Users/X1C-G9/Documents/claudecode/PokerClaw
PYTHONPATH=/c/Users/X1C-G9/Documents/claudecode/PokerClaw python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd /c/Users/X1C-G9/Documents/claudecode/PokerClaw/frontend
npm run dev -- --host
```

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Pending Tasks

### Phase 7: Hand Lab (Scenario Testing)
- [ ] Preset scenario definitions (premium hands, draws, all-in)
- [ ] Scenario runner for single-hand testing
- [ ] Hand Lab UI page

### Phase 8: Learning & GTO
- [ ] Historical summary generation
- [ ] RAG for similar hand lookup
- [ ] Equity calculation (Monte Carlo)
- [ ] Preflop GTO table

### Phase 9: Tournament Support
- [ ] Tournament engine (blind increases, elimination)
- [ ] Multi-table support
- [ ] Leaderboard/stats

### Phase 10: Deployment
- [ ] Docker configuration
- [ ] Production build scripts
- [ ] Documentation updates

---

## Known Issues
- None currently

## Session History

### Session 1 (Initial - 2026-03-28)
- Created project structure and documentation
- Implemented full poker engine
- Built agent system with LLM integration
- Completed backend API
- Finished all frontend pages

### Session 2 (Integration - 2026-03-28)
- Created PROCESS.md for progress tracking
- Installed FastAPI dependencies
- Started backend server on port 8000
- Started frontend dev server on port 5173
- Verified all API endpoints working
- Full stack integration complete

### Session 3 (Bug Fixes - 2026-03-29)
- Fixed: Game ended instantly (MockLLMProvider delay 10ms → 800ms)
- Fixed: Agent names showed as UUID instead of display_name
  - Updated game_runner.py to use display_name in ActionRecord
  - Updated game_service.py _serialize_hand to map agent IDs to names
  - Updated game_routes.py get_game to return display_name as key
- Fixed: MockLLMProvider aggressive strategy always raised
  - Added 50% chance to call/check to allow game to proceed to flop/turn/river
- Verified: community_cards now displays correctly in API response

### Session 4 (Replay Enhancement - 2026-03-29)
- Added player hole cards display to ReplayPage
- Implemented hand visibility controls:
  - Show All / Hide All buttons
  - Individual checkbox for each player
  - Cards displayed on poker table
- Backend changes:
  - Added player_cards_json column to hand_records table
  - Updated _serialize_hand to include player_cards
  - Updated replay_routes.py to return player_cards in API
- Updated README.md with complete feature documentation
- Pushed MVP to GitHub: https://github.com/xnfan/PokerClaw

### Next Session Focus
- Implement Hand Lab for preset scenario testing
- Add equity calculation (Monte Carlo)
- Create preflop GTO reference table
