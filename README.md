# PokerClaw

> 基于 LLM 的德州扑克 Agent 竞技平台

## 项目简介

PokerClaw 是一个基于大语言模型（LLM）的德州扑克 Agent 竞技平台。用户可以创建、配置并持久化 AI Agent，让它们在不同规则的德扑牌局中自主对战或与人类玩家竞技。

**核心特性：**
- 可配置性格的 LLM Agent（新手/中级/高手 × TAG/LAG/鱼/石头/跟注站/疯子）
- 现金局模式（Agent 自动对战）
- 实时观战模式（实时显示发牌、思考过程、下注行为）
- 完整的牌局回放与 Agent 思维过程展示
- 回放支持查看所有玩家底牌（包括弃牌玩家）和全部公共牌
- 每手牌结束后展示各玩家筹码增减
- Action 详情中显示本轮投入筹码（Round Bet）
- 无限局数模式 + 手动停止游戏
- LLM 调用监控（Token、耗时、成功率、P95 延迟）
- 实时 WebSocket 推送牌局更新
- 82+ 单元测试覆盖核心逻辑

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, SQLAlchemy, WebSocket |
| 数据库 | SQLite |
| 前端 | React 19, TypeScript, Vite |
| 手牌评估 | 自建评估器（10种牌型、7选5比较）|
| LLM | Anthropic Claude / Mock Provider |

## 快速开始

### 后端启动

```bash
# 进入项目目录
cd PokerClaw

# 安装依赖
pip install fastapi uvicorn websockets sqlalchemy pydantic anthropic

# 启动服务（Windows）
set PYTHONPATH=c:\Users\X1C-G9\Documents\claudecode\PokerClaw
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 或 Linux/Mac
PYTHONPATH=/path/to/PokerClaw python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev -- --host
```

访问 http://localhost:5173 即可使用。

## 项目结构

```
PokerClaw/
├── backend/              # 后端服务
│   ├── engine/           # 德扑规则引擎（Card, Deck, HandEvaluator, PotManager, BettingRound, GameRunner, CashGame）
│   ├── agent/            # Agent 系统（BaseAgent, LLMAgent, Personality, ActionParser）
│   ├── llm/              # LLM Provider 适配器（Base, Anthropic, Mock）
│   ├── monitoring/       # 监控与指标（AgentMonitor, LLMMetricsCollector, MetricsAggregator）
│   ├── api/              # REST API & WebSocket 路由
│   ├── services/         # 业务逻辑服务（GameService）
│   ├── database.py       # SQLite 数据库初始化
│   ├── main.py           # FastAPI 入口
│   └── tests/            # 77+ 测试套件
├── frontend/             # React 前端
│   ├── src/pages/        # 6个页面（Dashboard, AgentManage, GameSetup, GamePlay, Replay, Monitoring）
│   └── src/api/          # API 客户端
├── docs/                 # 项目文档（PRD, SYSTEM_DESIGN, TEST_ANALYSIS）
├── scripts/              # 工具脚本（run_cli_game.py）
└── PROCESS.md            # 开发进度跟踪
```

## 已实现功能

### Phase 1: 引擎核心 ✅
- [x] Card, Deck, HandEvaluator（10种牌型评估 + 7选5）
- [x] PotManager（底池 + 边池计算）
- [x] BettingRound（下注轮次逻辑，4次加注上限）
- [x] GameState（牌局状态管理）
- [x] GameRunner（单手牌执行器）
- [x] CashGame（多手牌现金局）

### Phase 2: Agent 系统 ✅
- [x] BaseAgent 接口
- [x] LLMAgent（30秒超时 + 1次重试 + fallback）
- [x] Personality 模板（6种风格 × 3个等级）
- [x] ActionParser（LLM 输出解析）
- [x] MockLLMProvider（测试用）
- [x] AnthropicProvider（Claude API）

### Phase 3: 数据持久化 + API ✅
- [x] SQLite 数据库（agents, sessions, hands, llm_logs, decisions 表）
- [x] FastAPI REST 接口
- [x] WebSocket 实时通信
- [x] Agent CRUD API
- [x] 游戏创建/启动/查询 API
- [x] 监控指标 API

### Phase 4: 前端 ✅
- [x] React + TypeScript + Vite 项目
- [x] Dashboard（统计概览）
- [x] Agent 管理（创建/删除/配置）
- [x] 游戏配置（选择 Agent、设置盲注、无限局数模式）
- [x] 游戏实况（实时观战、思考指示、底牌展示、Stop 按钮）
- [x] **回放页面（步骤导航、手牌显示、筹码变化、Round Bet）**
- [x] 监控中心（Provider 状态、Agent 指标）

### Phase 5: 修复与优化 ✅
- [x] 游戏速度调整（800ms 延迟，可观看）
- [x] Agent 名字显示修复（display_name 替代 UUID）
- [x] 回放手牌可见性控制（全显/全隐/单独控制）

### Phase 6: 实时观战增强 ✅
- [x] WebSocket 实时推送（street_start / player_thinking / player_action / hand_complete）
- [x] 实时观战页面显示所有玩家底牌（观战模式）
- [x] 弃牌玩家底牌可见 + 未发公共牌补全显示
- [x] 每手牌结束后显示各玩家筹码增减
- [x] Action 详情中显示本轮投入筹码（Round Bet）
- [x] 无限局数模式 + 手动停止游戏（POST stop 端点）
- [x] Raise cap 验证测试（最多 4 次加注/轮）
- [x] 82+ 测试全部通过

## 待实现功能

| 模块 | 优先级 | 状态 |
|------|--------|------|
| 手牌实验室 (Hand Lab) | P1 | 未开始 |
| 人机对战 (Human Agent) | P1 | 未开始 |
| 锦标赛模式 (Tournament) | P2 | 未开始 |
| Agent 学习系统 (Learning) | P2 | 未开始 |
| GTO 策略辅助 | P2 | 未开始 |

## 运行测试

```bash
# 运行所有测试
python -m pytest backend/tests/ -v

# 运行特定模块测试
python -m pytest backend/tests/test_engine.py -v
python -m pytest backend/tests/test_agent.py -v
```

## API 端点

- `GET /` - 服务状态
- `GET /docs` - Swagger 文档

### Agent
- `GET /api/agents` - 列出所有 Agent
- `POST /api/agents` - 创建 Agent
- `GET /api/agents/{id}` - 获取 Agent 详情
- `PUT /api/agents/{id}` - 更新 Agent
- `DELETE /api/agents/{id}` - 删除 Agent

### 游戏
- `GET /api/games` - 列出所有游戏
- `POST /api/games` - 创建游戏
- `GET /api/games/{session_id}` - 获取游戏状态
- `POST /api/games/{session_id}/start` - 开始游戏
- `POST /api/games/{session_id}/stop` - 停止游戏（当前手牌完成后停止）
- `GET /api/games/{session_id}/hands` - 获取手牌记录

### 回放
- `GET /api/replay/sessions/{session_id}` - 获取会话手牌列表
- `GET /api/replay/hands/{hand_id}` - 获取手牌详情（含 player_cards）

### 监控
- `GET /api/monitoring/overview` - 全局概览
- `GET /api/monitoring/agents/{agent_id}` - Agent 指标
- `GET /api/monitoring/providers` - Provider 状态

### WebSocket
- `WS /ws/game/{session_id}` - 实时游戏更新（hand_start / street_start / player_thinking / player_action / hand_complete / game_finished）

## 文档索引

- [产品需求文档 (PRD)](docs/PRD.md) - 功能需求、用户故事、里程碑
- [系统设计文档](docs/SYSTEM_DESIGN.md) - 架构设计、数据库 Schema、API 设计
- [测试策略文档](docs/TEST_ANALYSIS.md) - 测试覆盖、测试用例
- [开发进度](PROCESS.md) - 任务跟踪、会话记录

## 更新日志

### 2026-04-02 (Session 6)
- 修复实时渲染：hand_start 事件数据解析错误导致底牌不显示（嵌套对象 vs 数组）
- 修复实时状态管理：新增 handInProgress 标志，正确控制实时/回放切换
- 修复 Stop Game：stop 路由改为 async、增加状态检查、游戏结束发送 game_finished 事件
- 修复 All-in 公共牌：重写街道循环逻辑，all-in 时跳过下注但继续发牌
- 修复回放底牌可见性：统一使用 displayPlayerCards（实时=livePlayerCards，回放=lastHand.player_cards）
- WebSocket handler 增加日志（broadcast 事件类型、连接/断开、死连接清理）
- 82 测试全部通过

### 2026-04-02 (Session 5)
- 新增实时观战模式（WebSocket 推送发牌、思考、下注等所有事件）
- 弃牌玩家底牌在回放中可见，未发公共牌补全显示
- 每手牌结束后展示各玩家筹码增减
- Action 详情中新增 Round Bet（本轮投入筹码）
- 新增无限局数模式 + 手动停止游戏
- 新增 Stop Game API 端点
- 新增 Raise cap 验证测试
- 82+ 测试全部通过

### 2026-03-29
- MVP 完整实现（后端 + 前端）
- 修复游戏速度问题（delay 10ms → 800ms）
- 修复 Agent 名字显示（display_name 替代 UUID）
- 新增回放页面手牌可见性控制
- 77+ 测试全部通过

## License

MIT License
