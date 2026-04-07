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

---

## Session 8: Human vs AI Gameplay (2026-04-08)

### 新增功能
- **人机对战**：人类玩家通过 WebSocket 与 AI Agent 实时对战
  - 新增 HumanAgent 类（backend/agent/human_agent.py）
    - 继承 BaseAgent 接口
    - asyncio.Future 等待人类决策
    - 60秒超时自动 FOLD
  - WebSocket 支持 human_turn 和 human_decision 事件
  - GameSetupPage 新增"Human vs AI"模式选择
  - GamePlayPage 新增人类玩家操作界面（Fold/Check/Call/Raise/All-in）

- **Dealer/Blind 位置显示**
  - hand_start 事件包含 dealer、small_blind、big_blind 位置
  - 座位显示 [D]/[SB]/[BB] 标记
  - 扑克桌显示盲注金额

### 技术实现
- `backend/agent/human_agent.py` (新建):
  - HumanAgent 类
  - _registry 类变量管理所有实例
  - decide() 方法等待人类输入
  - submit_decision() 方法供 WebSocket 调用

- `backend/services/game_service.py`:
  - create_game() 支持 human_player 参数
  - GameSession 新增 human_player_id 字段
  - run_game() 设置 HumanAgent 回调

- `backend/api/websocket_handler.py`:
  - 处理 human_decision 消息类型
  - 验证并提交人类决策

- `backend/api/game_routes.py`:
  - 新增 POST /api/games/human 端点
  - HumanGameCreate 请求模型

- `frontend/src/pages/GameSetupPage.tsx`:
  - 新增游戏模式选择（AI vs AI / Human vs AI）
  - 新增人类玩家名字输入

- `frontend/src/pages/GamePlayPage.tsx`:
  - 新增人类玩家操作按钮
  - 新增倒计时显示
  - 修复人类玩家只能看自己牌的逻辑
  - 新增 Dealer/SB/BB 位置标记显示

- `backend/engine/game_runner.py`:
  - hand_start 事件新增 dealer、small_blind、big_blind 字段

### 文件变更
- `backend/agent/human_agent.py` - 新建
- `backend/services/game_service.py` - 修改
- `backend/api/websocket_handler.py` - 修改
- `backend/api/game_routes.py` - 修改
- `frontend/src/pages/GameSetupPage.tsx` - 修改
- `frontend/src/pages/GamePlayPage.tsx` - 修改
- `frontend/src/api/client.ts` - 修改
- `backend/engine/game_runner.py` - 修改

### 测试
- 后端 API 测试通过
- 前端编译通过

---

## Session 7: Hand Lab Real-time Streaming (2026-04-07)

### 新增功能
- **Hand Lab 实时流式传输**：将 Hand Lab 从批量运行改为实时 WebSocket 流式传输
  - 新增 `POST /api/handlab/start` 端点创建 Lab Session
  - 新增 `run_lab_game()` 函数处理预设牌面的实时游戏
  - WebSocket 事件：hand_start, street_start, player_thinking, player_action, hand_complete, lab_finished
  - 实时显示胜率（Equity）计算

### 技术实现
- `game_service.py`:
  - `GameSession` 新增 `lab_config` 字段支持 Hand Lab 配置
  - `start_lab_session()` 创建 Lab Session
  - `run_lab_game()` 处理预设牌面并流式传输事件
  - `trigger_game_start()` 根据 `lab_config` 分发到对应 runner

- `handlab_routes.py`:
  - 新增 `StartLabRequest` 模型
  - 新增 `POST /api/handlab/start` 端点

- `HandLabPage.tsx` (完全重写):
  - 状态机：setup → live → finished
  - WebSocket 连接实时接收事件
  - 实时扑克桌显示（公共牌、玩家底牌、胜率条）
  - 多手牌汇总统计（胜率、平均收益）
  - 已完成手牌浏览器

### API 变更
- 新增端点：
  - `POST /api/handlab/start` - 创建 Hand Lab Session
  - WebSocket `/ws/game/{session_id}` 支持 Lab 事件

### 文件变更
- `backend/services/game_service.py` - Lab Session 支持和 run_lab_game
- `backend/services/hand_lab.py` - compute_equity 提取为模块函数
- `backend/api/handlab_routes.py` - 新增 start 端点
- `frontend/src/api/client.ts` - 新增 startLab API
- `frontend/src/pages/HandLabPage.tsx` - 完全重写为实时流式界面
- `backend/tests/engine/test_hand_lab.py` - 新增流式测试

### 测试
- 新增 3 个集成测试验证 Hand Lab 流式功能
- 全部测试通过

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

### Phase 7: Hand Lab (Scenario Testing) ✅
- [x] Preset scenario definitions (premium hands, draws, all-in)
- [x] Scenario runner for single-hand and multi-hand testing
- [x] Hand Lab UI page with real-time streaming
- [x] WebSocket streaming for Hand Lab (like normal games)
- [x] Equity calculation (Monte Carlo) displayed in real-time
- [x] Multi-run summary with win rates and average profit

### Phase 8: Human vs AI Gameplay ✅
- [x] HumanAgent class with WebSocket decision waiting
- [x] POST /api/games/human endpoint
- [x] Human player UI with Fold/Check/Call/Raise/All-in
- [x] Card visibility control (human sees own cards only)
- [x] 60-second timeout with auto-fold
- [x] Dealer/SB/BB position display

### Phase 9: Learning & GTO
- [ ] Historical summary generation
- [ ] RAG for similar hand lookup
- [ ] Equity calculation (Monte Carlo)
- [ ] Preflop GTO table

### Phase 10: Tournament Support
- [ ] Tournament engine (blind increases, elimination)
- [ ] Multi-table support
- [ ] Leaderboard/stats

### Phase 11: Deployment
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

### Session 5 (Live Game Enhancements - 2026-04-02)
- Real-time streaming via WebSocket:
  - Added on_action callback to GameRunner
  - Events: hand_start, street_start, player_thinking, player_action, hand_complete
  - Frontend GamePlayPage: live action log, thinking indicators, community cards
- Card visibility fixes:
  - _resolve() now includes ALL players' hole cards (folded players too)
  - Deal remaining community cards before result for full board display
  - ReplayPage: folded players' cards visible, all 5 community cards shown
- Chip changes per hand:
  - CashGame captures starting_chips, computes chip_changes delta
  - Displayed in GamePlayPage (seats) and ReplayPage (summary card)
- Action detail improvements:
  - Added Round Bet (本轮投入) to action log and replay detail
- Multi-hand settings + stop:
  - GameSetupPage: Set/Unlimited radio toggle
  - POST /api/games/{session_id}/stop endpoint with asyncio.Event
  - GamePlayPage: Stop Game button during running games
- Raise cap validation tests (3 new tests)
- Chip changes integration tests (2 new tests)
- Total: 82 tests passing
- Updated README.md and PROCESS.md

### Session 6 (Critical Bug Fixes - 2026-04-02)
- Fixed: Real-time rendering broken — hand_start event sent nested objects `{chips, is_active, hole_cards}` but frontend expected `string[]`
  - Rewrote GamePlayPage WebSocket handler to correctly extract `hole_cards` from nested player data
  - Added `handInProgress` state flag: true on hand_start, false on hand_complete
  - `isLive = handInProgress` instead of checking liveActions/thinkingPlayer
- Fixed: Folded player cards not visible
  - Unified card display: `displayPlayerCards` selects between livePlayerCards (real-time) and lastHand.player_cards (review)
  - All players' cards always visible in spectator mode
- Fixed: Stop Game button not working
  - `stop_game` route changed to `async def`
  - Added status validation (only running/pending_start can be stopped)
  - Added `game_finished` WebSocket event after game loop ends
  - Frontend handles game_finished to update UI state
- Fixed: All-in preflop skipped community card dealing
  - Rewrote street loop: checks `active_players` (not folded) vs `active_non_allin` (can bet)
  - Multiple active + all committed → deal board cards, skip betting round
  - Single active player → break (everyone else folded)
- Added logging to WebSocket handler (broadcast events, connect/disconnect, dead connection cleanup)
- Files changed: game_runner.py, game_service.py, game_routes.py, websocket_handler.py, GamePlayPage.tsx
- 82 tests passing, frontend build clean

### Next Session Focus
- Human vs Agent gameplay mode
- Tournament mode with blind increases
- Agent learning from historical hands
