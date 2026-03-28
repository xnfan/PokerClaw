# PokerClaw

> 基于 LLM 的德州扑克 Agent 竞技平台

## 项目简介

PokerClaw 是一个基于大语言模型（LLM）的德州扑克 Agent 竞技平台。用户可以创建、配置并持久化 AI Agent，让它们在不同规则的德扑牌局中自主对战或与人类玩家竞技。

**核心特性：**
- 可配置性格的 LLM Agent（新手/中级/高手 × LAG/TAG/鱼/石头）
- 现金局模式（支持人机对战）
- 完整的牌局回放与 Agent 思维过程展示
- 手牌实验室：预设场景测试 Agent 决策
- LLM 调用监控（Token、耗时、成功率）
- Agent 历史学习（短期摘要 + 长期 RAG）
- GTO 策略辅助参考

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, WebSocket |
| 数据库 | SQLite (预留 PostgreSQL 支持) |
| 前端 | React 18, TypeScript, Vite, Tailwind CSS |
| 手牌评估 | 自建评估器 + Monte Carlo Equity |
| LLM | Anthropic Claude (可扩展其他 Provider) |
| 向量存储 | SQLite + numpy 余弦相似度 |

## 快速开始

### 后端启动

```bash
# 进入项目目录
cd PokerClaw

# 安装依赖
pip install -r backend/requirements.txt

# 启动服务
uvicorn backend.main:app --reload --port 8000
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173 即可使用。

## 项目结构

```
PokerClaw/
├── backend/              # 后端服务
│   ├── engine/           # 德扑规则引擎
│   ├── agent/            # Agent 系统
│   ├── llm/              # LLM Provider 适配器
│   ├── monitoring/       # 监控与指标
│   ├── api/              # REST API & WebSocket
│   ├── services/         # 业务逻辑服务
│   ├── database.py       # Schema 待完善
│   ├── main.py           # FastAPI 入口
│   └── tests/            # 测试套件
├── frontend/             # React 前端
├── docs/                 # 项目文档
├── review/               # Review 报告
└── scripts/              # 工具脚本
```

## 当前进度

### 已实现

| 模块 | 状态 | 说明 |
|------|------|------|
| 德扑引擎 | 核心完成 | 发牌、下注、边池计算 |
| 手牌评估 | 完成 | 牌型判断、胜负比较 |
| LLM Agent | 核心完成 | 决策、解析、超时兜底 |
| Agent 性格 | 完成 | 5种风格模板 |
| 监控指标 | 基础完成 | Token、耗时、成功率统计 |
| API 接口 | 基础完成 | REST + WebSocket |

### 待实现/优化

| 模块 | 优先级 | 状态 |
|------|--------|------|
| 手牌实验室 (hand_lab) | P0 | 未开始 |
| 人机对战 (human_agent) | P0 | 未开始 |
| 锦标赛模式 (tournament) | P1 | 未开始 |
| 学习系统 (learning/) | P1 | 空目录 |
| GTO 辅助 (gto/) | P1 | 空目录 |

## 已知问题

1. **PotManager 边池计算** - 多人 all-in 场景下底池分配逻辑需优化
2. **数据库 Schema** - 实际实现(5表)与设计文档(11表)存在差距

详见 [review/SYSTEM_DESIGN_REVIEW.md](review/SYSTEM_DESIGN_REVIEW.md)

## 运行测试

```bash
# 运行所有测试
pytest backend/tests/ -v
```

## 文档索引

- [产品需求文档 (PRD)](docs/PRD.md) - 功能需求、用户故事、里程碑
- [系统设计文档](docs/SYSTEM_DESIGN.md) - 架构设计、数据库 Schema、API 设计
- [测试策略文档](docs/TEST_ANALYSIS.md) - 测试覆盖、测试用例
- [设计 Review 报告](review/SYSTEM_DESIGN_REVIEW.md) - 问题分析、改进建议
