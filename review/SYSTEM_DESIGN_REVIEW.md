# PokerClaw 系统设计 Review 报告

**Review 日期**: 2026-03-28
**Review 范围**: docs/ 设计文档 vs 实际代码实现
**Reviewer**: Claude Code

---

## 执行摘要

PokerClaw 的核心牌局引擎（engine/）实现相对完整，但**数据持久化层、手牌实验室、学习系统、GTO 辅助**等关键模块尚未实现或实现不完整。

**关键风险**：
1. 🔴 **高**：PotManager 边池计算逻辑存在缺陷
2. 🔴 **高**：数据库 schema 与设计文档严重不符
3. 🟡 **中**：多个 P0/P1 功能模块缺失
4. 🟡 **中**：API Key 明文存储安全风险

---

## 1. 设计文档与实现不一致

| 设计文档 (SYSTEM_DESIGN.md) | 实际实现 | 问题等级 |
|------------------------------|----------|----------|
| `hand_lab.py` 模块 | 存在目录 `learning/`、`gto/`，但只有 `__init__.py` | 🔴 高 |
| `action_logs` 表 (详细字段) | `hand_records` 表中的 `actions_json` 字段 | 🔴 高 |
| `session_players` 表 | 不存在 | 🔴 高 |
| `hand_players` 表 | 不存在 | 🔴 高 |
| `agent_memories` 表 (RAG向量存储) | 不存在 | 🟡 中 |
| `human_agent.py` | 不存在 | 🔴 高 |
| `tournament.py` | 不存在 | 🟡 中 |

### 1.1 数据库 Schema 差异详情

**设计文档定义的表**: 11 个表
- agents, game_sessions, session_players, hand_records, hand_players
- action_logs, hand_lab_scenarios, hand_lab_runs
- llm_call_logs, decision_logs, agent_memories

**实际实现的表**: 5 个表 [database.py:12-77]
- agents ✅
- game_sessions ✅
- hand_records ⚠️ (字段大幅简化)
- llm_call_logs ✅
- decision_logs ✅

**缺失的表**:
- ❌ session_players - 无法关联 session 与 player
- ❌ hand_players - 无法记录每手牌的玩家数据
- ❌ action_logs - 动作日志粒度不够，丢失关键字段
- ❌ hand_lab_scenarios - 手牌实验室场景无法保存
- ❌ hand_lab_runs - 实验运行记录无法保存
- ❌ agent_memories - RAG 向量存储完全缺失

---

## 2. 数据库设计问题 [database.py]

### 2.1 Schema 结构问题

```sql
-- 当前实现：使用 JSON 字段存储复杂数据
CREATE TABLE hand_records (
    hand_id         TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    hand_number     INTEGER NOT NULL,
    community_cards TEXT DEFAULT '[]',
    pot_total       INTEGER DEFAULT 0,
    winners_json    TEXT DEFAULT '{}',
    actions_json    TEXT DEFAULT '[]',  -- 丢失详细字段
    started_at      TEXT NOT NULL
);
```

**问题**:
1. **字段冗余**：使用 JSON 字段存储 winners 和 actions，丢失关系型查询能力
2. **数据丢失**：无法存储 thinking_text、is_timeout、is_fallback 等关键调试信息
3. **无外键约束**：表之间没有 FOREIGN KEY，数据完整性无法保证
4. **缺少索引**：除 llm_call_logs 外，其他表无索引，查询性能差

### 2.2 连接管理问题

```python
def get_db(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)  # 每次创建新连接
    conn.row_factory = sqlite3.Row
    return conn
```

**问题**：
- 无连接池，高并发时性能差
- 连接生命周期管理混乱

---

## 3. 核心逻辑缺陷

### 3.1 PotManager 边池计算逻辑问题 [pot_manager.py:35-66]

```python
# 问题代码：
if pid in active_player_ids and bet >= threshold:
    eligible.append(pid)
elif pid in active_player_ids and bet > prev_threshold:
    eligible.append(pid)
```

**问题**：
- 逻辑重复：`bet >= threshold` 已包含 `bet > prev_threshold`
- 边池资格判断不正确，可能导致错误的边池分配
- 未考虑 all-in 玩家的精确贡献计算

**影响**：多人 all-in 场景下底池分配可能错误

### 3.2 BettingRound 无限循环风险 [betting_round.py:131-153]

```python
def get_next_player_id(self) -> str | None:
    for _ in range(len(self._action_order)):
        idx = self._action_index % len(self._action_order)
        self._action_index += 1
        # ...
```

**问题**：
- 循环退出条件复杂，某些边界情况可能无限循环
- 未覆盖复杂的多人 all-in + 边池场景

### 3.3 ActionParser 解析不够健壮 [action_parser.py:12-52]

```python
_ACTION_RE = re.compile(
    r"ACTION:\s*(fold|check|call|raise|all_in|all-in|allin)",
    re.IGNORECASE,
)
```

**问题**：
1. 缺少对 all_in 金额的校验（应该是玩家全部筹码）
2. 加注金额超出玩家筹码时没有自动调整为 all_in
3. 无法解析自然语言中的动作描述

---

## 4. 缺失的关键功能模块

| 模块 | 设计文档 | 实际状态 | PRD 优先级 | 影响 |
|------|----------|----------|------------|------|
| hand_lab.py | 完整设计 | ❌ 不存在 | P0 | 手牌实验室功能缺失 |
| tournament.py | 完整设计 | ❌ 不存在 | P1 | 锦标赛模式无法使用 |
| human_agent.py | 完整设计 | ❌ 不存在 | P0 | 人机对战无法实现 |
| learning/ | RAG、历史摘要 | ⚠️ 空目录 | P1 | Agent 无法学习 |
| gto/ | Equity计算、翻前表 | ⚠️ 空目录 | P1 | GTO 辅助无法使用 |
| websocket_handler.py | 完整设计 | ⚠️ 基础实现 | P0 | 实时通信不完整 |

### 4.1 手牌实验室 (Hand Lab) 缺失

**设计文档功能**:
- ScenarioConfig: 预设场景配置
- HandLab.run_once(): 单次运行
- HandLab.run_multiple(): 多次运行观察决策稳定性
- 场景保存与加载

**实际状态**: 完全未实现

### 4.2 学习系统缺失

**设计文档功能**:
- HistorySummarizer: 历史手牌摘要
- EmbeddingStore: 向量存储
- MemoryRetriever: 相似场景检索

**实际状态**: 只有空目录 `learning/__init__.py`

### 4.3 GTO 辅助缺失

**设计文档功能**:
- EquityCalculator: 蒙特卡洛胜率计算
- PreflopChart: 翻前起手牌表
- GTOAdvisor: 综合策略建议

**实际状态**: 只有空目录 `gto/__init__.py`

---

## 5. 测试设计问题

### 5.1 测试文件缺失

| 应有测试文件 | 状态 |
|--------------|------|
| test_betting_round.py | ❌ 缺失 |
| test_game_state.py | ❌ 缺失 |
| test_game_runner.py | ❌ 缺失 |
| test_decision_context.py | ❌ 缺失 |
| test_personality.py | ❌ 缺失 |
| test_cash_game.py | ❌ 缺失 |
| test_tournament.py | ❌ 缺失 (模块也不存在) |
| test_hand_lab.py | ❌ 缺失 (模块也不存在) |

### 5.2 测试覆盖不足

当前实现的测试：
- ✅ test_card.py
- ✅ test_deck.py
- ✅ test_hand_evaluator.py
- ✅ test_pot_manager.py
- ✅ test_action_parser.py
- ✅ test_llm_agent.py
- ✅ test_metrics.py
- ✅ test_full_hand.py

**缺失的关键测试场景**：
- 多人 all-in + 边池分配的复杂场景
- WebSocket 通信测试
- 超时和降级逻辑的边界测试
- LLM 重试机制测试

---

## 6. 代码规范问题

### 6.1 类型提示不一致

**问题示例** [llm_agent.py:47]:
```python
async def decide(
    self,
    game_view: dict[str, Any],
    valid_actions: list[BettingAction],
) -> tuple[PlayerAction, dict[str, Any]]:  # 返回类型与基类可能不一致
```

### 6.2 错误处理不完善

**问题示例** [game_runner.py:164-167]:
```python
action, metadata = await agent.decide(player_view, valid_actions)
# Ensure action is valid
if action.action not in valid_actions:
    action = PlayerAction(next_pid, BettingAction.FOLD)
```

- Agent 返回的动作只做了简单验证
- 未处理 action.amount 的合法性
- 未处理异常情况下的状态恢复

### 6.3 常量定义分散

| 常量 | 定义位置 | 问题 |
|------|----------|------|
| DEFAULT_DECISION_TIMEOUT = 30.0 | llm_agent.py:18 | 多处可能使用，应统一配置 |
| MAX_RAISES_PER_ROUND = 4 | betting_round.py:38 | 应可配置，不应硬编码 |

---

## 7. 性能与可扩展性问题

### 7.1 数据库连接无池化

**问题**：每次数据库操作都创建新连接

**影响**：高并发时性能急剧下降

### 7.2 LLM 调用资源管理

**问题** [llm_agent.py:61-64]:
```python
action = await asyncio.wait_for(
    self._decide_inner(game_view, valid_actions, metadata),
    timeout=self.decision_timeout,
)
```

- 使用 `asyncio.wait_for` 实现超时
- 超时后后台任务未取消，可能导致资源泄漏

### 7.3 向量存储性能

**设计文档**: 使用 `SQLite + numpy 余弦相似度`

**问题**：
- 大数据量时性能下降严重
- 没有使用专业向量数据库（如 FAISS、Milvus）

---

## 8. 安全问题

### 8.1 API Key 明文存储

**问题** [database.py:20]:
```sql
llm_api_key     TEXT DEFAULT '',  -- 明文存储，无加密
```

**风险**：API Key 泄露可能导致 LLM 服务被滥用

**建议**：
- 使用对称加密存储
- 或使用环境变量/密钥管理服务

### 8.2 CORS 配置过于宽松

**问题** [main.py:23-28]:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**风险**：生产环境可能遭受 CSRF/XSS 攻击

**建议**：限制为前端实际域名

---

## 9. API 设计问题

### 9.1 Router 注册缺少统一前缀

**问题** [main.py:32-36]:
```python
app.include_router(agent_router)
app.include_router(game_router)
```

**设计文档要求**：
- `/api/agents`
- `/api/games`

**实际**：前缀不一致，可能导致 API 路径混乱

---

## 10. 改进建议优先级

### 🔴 P0 - 必须立即修复

| 序号 | 改进项 | 原因 | 涉及文件 |
|------|--------|------|----------|
| 1 | 修复 PotManager 边池计算逻辑 | 影响核心游戏规则正确性 | pot_manager.py |
| 2 | 补全数据库 schema | 影响数据持久化完整性 | database.py |
| 3 | 实现 hand_lab.py | PRD 中 P0 功能 | engine/hand_lab.py |
| 4 | 实现 human_agent.py | PRD 中 P0 功能 | agent/human_agent.py |

### 🟡 P1 - 尽快修复

| 序号 | 改进项 | 原因 | 涉及文件 |
|------|--------|------|----------|
| 5 | 添加数据库连接池 | 影响性能和并发能力 | database.py |
| 6 | 加密 API Key 存储 | 安全风险 | database.py |
| 7 | 限制 CORS 配置 | 安全风险 | main.py |
| 8 | 补全测试覆盖 | 保证代码质量 | tests/ |

### 🟢 P2 - 建议修复

| 序号 | 改进项 | 原因 | 涉及文件 |
|------|--------|------|----------|
| 9 | 实现 learning/ 模块 | PRD 中 P1 功能 | learning/* |
| 10 | 实现 gto/ 模块 | PRD 中 P1 功能 | gto/* |
| 11 | 统一错误处理和常量定义 | 代码可维护性 | 多处 |
| 12 | 完善 WebSocket 处理 | PRD 中 P0 功能 | api/websocket_handler.py |

---

## 附录：关键代码位置

### 核心引擎
- [engine/card.py](backend/engine/card.py) - 扑克牌定义
- [engine/deck.py](backend/engine/deck.py) - 牌堆管理
- [engine/hand_evaluator.py](backend/engine/hand_evaluator.py) - 手牌评估
- [engine/pot_manager.py](backend/engine/pot_manager.py) - ⚠️ 边池计算有缺陷
- [engine/betting_round.py](backend/engine/betting_round.py) - 下注轮次
- [engine/game_state.py](backend/engine/game_state.py) - 游戏状态
- [engine/game_runner.py](backend/engine/game_runner.py) - 游戏执行器

### Agent 系统
- [agent/base_agent.py](backend/agent/base_agent.py) - Agent 基类
- [agent/llm_agent.py](backend/agent/llm_agent.py) - LLM Agent
- [agent/action_parser.py](backend/agent/action_parser.py) - 动作解析
- [agent/personality.py](backend/agent/personality.py) - 性格模板
- [agent/decision_context.py](backend/agent/decision_context.py) - 决策上下文

### 数据层
- [database.py](backend/database.py) - ⚠️ Schema 不完整
- [models/](backend/models/) - 只有空 __init__.py

### API 层
- [main.py](backend/main.py) - FastAPI 入口
- [api/agent_routes.py](backend/api/agent_routes.py) - Agent API
- [api/game_routes.py](backend/api/game_routes.py) - 游戏 API
- [api/monitoring_routes.py](backend/api/monitoring_routes.py) - 监控 API
- [api/replay_routes.py](backend/api/replay_routes.py) - 回放 API
- [api/websocket_handler.py](backend/api/websocket_handler.py) - ⚠️ 基础实现

---

**报告生成时间**: 2026-03-28
**报告版本**: v1.0
