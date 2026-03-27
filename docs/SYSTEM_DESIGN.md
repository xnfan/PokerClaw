# PokerClaw — 系统设计文档

## 1. 项目目录结构

```
PokerClaw/
├── docs/                          # 文档
│   ├── PRD.md
│   ├── SYSTEM_DESIGN.md
│   └── TEST_ANALYSIS.md
├── backend/
│   ├── main.py                    # FastAPI 入口 (<100行)
│   ├── requirements.txt
│   ├── config.py                  # 全局配置
│   ├── database.py                # 数据库连接与初始化
│   ├── models/                    # 数据模型 (SQLAlchemy)
│   │   ├── __init__.py
│   │   ├── agent_model.py         # Agent 表
│   │   ├── game_session_model.py  # 牌局 session 表
│   │   ├── hand_record_model.py   # 手牌记录表
│   │   └── action_log_model.py    # 动作日志表
│   ├── engine/                    # 德扑规则引擎
│   │   ├── __init__.py
│   │   ├── card.py                # 扑克牌与牌组定义
│   │   ├── deck.py                # 牌堆(洗牌、发牌)
│   │   ├── hand_evaluator.py      # 手牌评估(牌型判断、比较)
│   │   ├── pot_manager.py         # 底池与边池管理
│   │   ├── betting_round.py       # 下注轮次逻辑
│   │   ├── game_state.py          # 牌局状态管理
│   │   ├── game_runner.py         # 单手牌执行器
│   │   ├── cash_game.py           # 现金局管理
│   │   ├── tournament.py          # 锦标赛管理
│   │   └── hand_lab.py            # 手牌实验室(预设场景运行器)
│   ├── agent/                     # Agent 系统
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Agent 基类/接口
│   │   ├── llm_agent.py           # LLM Agent 实现
│   │   ├── human_agent.py         # 人类玩家代理
│   │   ├── personality.py         # 性格与水平 prompt 模板
│   │   ├── decision_context.py    # 决策上下文构建
│   │   └── action_parser.py       # LLM 输出 → 游戏动作解析
│   ├── llm/                       # LLM 适配层
│   │   ├── __init__.py
│   │   ├── base_provider.py       # LLM Provider 抽象接口
│   │   ├── anthropic_provider.py  # Claude 实现
│   │   ├── openai_provider.py     # OpenAI 实现 (预留)
│   │   └── provider_factory.py    # Provider 工厂
│   ├── learning/                  # Agent 学习系统
│   │   ├── __init__.py
│   │   ├── history_summarizer.py  # 历史手牌摘要生成
│   │   ├── embedding_store.py     # 向量存储 (RAG)
│   │   └── memory_retriever.py    # 相似场景检索
│   ├── gto/                       # GTO 辅助
│   │   ├── __init__.py
│   │   ├── equity_calculator.py   # 手牌胜率计算
│   │   ├── preflop_chart.py       # 翻前起手牌表
│   │   └── gto_advisor.py         # GTO 策略建议
│   ├── monitoring/                # 监控与可观测性
│   │   ├── __init__.py
│   │   ├── llm_metrics.py         # LLM调用指标采集(token/耗时/状态)
│   │   ├── agent_monitor.py       # Agent决策监控(成功率/超时/异常)
│   │   └── metrics_aggregator.py  # 指标汇总(按Agent/Session/Provider)
│   ├── api/                       # API 路由
│   │   ├── __init__.py
│   │   ├── agent_routes.py        # Agent CRUD
│   │   ├── game_routes.py         # 牌局管理
│   │   ├── replay_routes.py       # 回放 API
│   │   ├── hand_lab_routes.py     # 手牌实验室 API
│   │   ├── monitoring_routes.py   # 监控数据 API
│   │   └── websocket_handler.py   # WebSocket 处理
│   ├── services/                  # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── agent_service.py       # Agent 业务逻辑
│   │   ├── game_service.py        # 牌局业务逻辑
│   │   ├── replay_service.py      # 回放业务逻辑
│   │   └── hand_lab_service.py    # 手牌实验室业务逻辑
│   └── tests/                     # 测试
│       ├── __init__.py
│       ├── engine/
│       │   ├── test_card.py
│       │   ├── test_deck.py
│       │   ├── test_hand_evaluator.py
│       │   ├── test_pot_manager.py
│       │   ├── test_betting_round.py
│       │   ├── test_game_state.py
│       │   ├── test_game_runner.py
│       │   ├── test_cash_game.py
│       │   ├── test_tournament.py
│       │   └── test_hand_lab.py
│       ├── agent/
│       │   ├── test_llm_agent.py
│       │   ├── test_personality.py
│       │   ├── test_decision_context.py
│       │   └── test_action_parser.py
│       ├── llm/
│       │   └── test_provider_factory.py
│       ├── learning/
│       │   ├── test_history_summarizer.py
│       │   └── test_memory_retriever.py
│       ├── gto/
│       │   ├── test_equity_calculator.py
│       │   └── test_preflop_chart.py
│       ├── monitoring/
│       │   ├── test_llm_metrics.py
│       │   ├── test_agent_monitor.py
│       │   └── test_metrics_aggregator.py
│       ├── api/
│       │   ├── test_agent_routes.py
│       │   ├── test_game_routes.py
│       │   ├── test_replay_routes.py
│       │   └── test_hand_lab_routes.py
│       └── integration/
│           ├── test_full_hand.py
│           └── test_agent_vs_agent.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                   # API 客户端
│       │   ├── client.ts
│       │   ├── agentApi.ts
│       │   ├── gameApi.ts
│       │   └── websocket.ts
│       ├── components/
│       │   ├── table/             # 牌桌组件
│       │   │   ├── PokerTable.tsx
│       │   │   ├── Seat.tsx
│       │   │   ├── Card.tsx
│       │   │   ├── CommunityCards.tsx
│       │   │   ├── PotDisplay.tsx
│       │   │   └── ActionPanel.tsx
│       │   ├── replay/            # 回放组件
│       │   │   ├── ReplayPlayer.tsx
│       │   │   ├── ReplayControls.tsx
│       │   │   ├── HandTimeline.tsx
│       │   │   └── ThinkingPanel.tsx
│       │   ├── agent/             # Agent 管理组件
│       │   │   ├── AgentList.tsx
│       │   │   ├── AgentForm.tsx
│       │   │   └── AgentStats.tsx
│       │   ├── game/              # 牌局配置组件
│       │   │   ├── GameSetup.tsx
│       │   │   ├── RuleConfig.tsx
│       │   │   └── PlayerSlots.tsx
│       │   ├── handlab/           # 手牌实验室组件
│       │   │   ├── HandLabSetup.tsx
│       │   │   ├── CardPicker.tsx
│       │   │   ├── ScenarioConfig.tsx
│       │   │   └── RunComparison.tsx
│       │   ├── monitoring/        # 监控组件
│       │   │   ├── TokenUsageChart.tsx
│       │   │   ├── LatencyChart.tsx
│       │   │   ├── SuccessRateCard.tsx
│       │   │   ├── ProviderStatus.tsx
│       │   │   └── AgentDecisionLog.tsx
│       │   └── common/            # 通用组件
│       │       ├── Layout.tsx
│       │       ├── Sidebar.tsx
│       │       └── Loading.tsx
│       ├── pages/
│       │   ├── DashboardPage.tsx
│       │   ├── TablePage.tsx
│       │   ├── ReplayPage.tsx
│       │   ├── AgentManagePage.tsx
│       │   ├── GameSetupPage.tsx
│       │   ├── HandLabPage.tsx
│       │   └── MonitoringPage.tsx
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   ├── useGameState.ts
│       │   └── useReplay.ts
│       ├── store/                 # 状态管理 (Zustand)
│       │   ├── gameStore.ts
│       │   ├── agentStore.ts
│       │   └── replayStore.ts
│       ├── types/
│       │   ├── game.ts
│       │   ├── agent.ts
│       │   └── replay.ts
│       └── styles/
│           └── globals.css
└── scripts/
    ├── run_cli_game.py            # CLI 模式快速试跑
    └── seed_agents.py             # 预置几个默认 Agent
```

---

## 2. 后端架构

### 2.1 分层架构

```
┌─────────────┐
│  API Layer  │  FastAPI routes + WebSocket
├─────────────┤
│  Service    │  业务编排逻辑
├─────────────┤
│  Engine     │  纯德扑规则，无外部依赖
├─────────────┤
│  Agent      │  Agent 决策管道
├─────────────┤
│  LLM        │  可插拔 LLM Provider
├─────────────┤
│  Learning   │  历史学习与 RAG
├─────────────┤
│  Database   │  SQLAlchemy + SQLite
└─────────────┘
```

### 2.2 德扑引擎层 (engine/)

#### 2.2.1 Card & Deck

```python
# engine/card.py
class Rank(IntEnum):
    TWO = 2
    THREE = 3
    ...
    ACE = 14

class Suit(Enum):
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"
    SPADES = "s"

@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.name[0]}{self.suit.value}"  # e.g. "Ah", "Td"
```

```python
# engine/deck.py
class Deck:
    def __init__(self):
        self.cards: list[Card] = [Card(r, s) for r in Rank for s in Suit]

    def shuffle(self) -> None: ...
    def deal(self, count: int = 1) -> list[Card]: ...
    def remaining(self) -> int: ...
```

#### 2.2.2 手牌评估器 (hand_evaluator.py)

自建手牌评估器，不依赖外部库（可选集成 eval7 加速 equity 计算）。

```python
class HandRank(IntEnum):
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

@dataclass(frozen=True, order=True)
class HandScore:
    """可直接比较大小的手牌得分"""
    hand_rank: HandRank
    tie_breakers: tuple[int, ...]  # 用于同牌型比较的 kicker

class HandEvaluator:
    @staticmethod
    def evaluate(hole_cards: list[Card], community_cards: list[Card]) -> HandScore:
        """从 7 张牌中选出最佳 5 张，返回 HandScore"""
        ...

    @staticmethod
    def find_best_hand(seven_cards: list[Card]) -> tuple[HandRank, list[Card]]:
        """暴力枚举 C(7,5)=21 种组合，返回最优"""
        ...
```

#### 2.2.3 底池管理 (pot_manager.py)

```python
@dataclass
class SidePot:
    amount: int
    eligible_player_ids: list[str]

class PotManager:
    def __init__(self):
        self.main_pot: int = 0
        self.side_pots: list[SidePot] = []
        self.player_contributions: dict[str, int] = {}  # 本手总投入

    def add_bet(self, player_id: str, amount: int) -> None: ...
    def calculate_side_pots(self, all_in_players: set[str]) -> None: ...
    def distribute_winnings(self, hand_scores: dict[str, HandScore]) -> dict[str, int]: ...
```

#### 2.2.4 下注轮次 (betting_round.py)

```python
class BettingAction(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"

@dataclass
class PlayerAction:
    player_id: str
    action: BettingAction
    amount: int = 0

class BettingRound:
    def __init__(self, players: list[PlayerState], pot_manager: PotManager):
        ...

    def get_valid_actions(self, player_id: str) -> list[BettingAction]: ...
    def apply_action(self, action: PlayerAction) -> None: ...
    def is_round_complete(self) -> bool: ...
    def get_next_player_id(self) -> str | None: ...
```

#### 2.2.5 游戏状态 (game_state.py)

```python
class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

@dataclass
class PlayerState:
    player_id: str
    display_name: str
    chips: int
    hole_cards: list[Card]
    is_active: bool       # 仍在本手中
    is_all_in: bool
    current_bet: int      # 本轮已下注
    total_bet: int        # 本手总下注
    seat_index: int

class GameState:
    """单手牌的完整状态"""
    hand_id: str
    street: Street
    players: list[PlayerState]
    community_cards: list[Card]
    pot_manager: PotManager
    dealer_index: int
    small_blind: int
    big_blind: int
    current_player_index: int

    def to_player_view(self, player_id: str) -> dict:
        """返回特定玩家可见的信息（隐藏他人手牌）"""
        ...

    def to_full_view(self) -> dict:
        """返回完整信息（用于回放/观战上帝视角）"""
        ...
```

#### 2.2.6 单手牌执行器 (game_runner.py)

```python
class GameRunner:
    """执行一手完整的牌局"""

    def __init__(self, game_state: GameState, agents: dict[str, BaseAgent]):
        self.state = game_state
        self.agents = agents
        self.action_history: list[ActionRecord] = []

    async def run_hand(self) -> HandResult:
        """执行一手完整牌局：发牌 → preflop → flop → turn → river → 摊牌"""
        self._post_blinds()
        self._deal_hole_cards()

        for street in [Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER]:
            if self._count_active_players() <= 1:
                break
            if street != Street.PREFLOP:
                self._deal_community(street)
            await self._run_betting_round(street)

        return self._resolve_showdown()

    async def _request_player_action(self, player_id: str) -> PlayerAction:
        """向 Agent 或人类请求动作"""
        agent = self.agents[player_id]
        valid_actions = self.state.get_valid_actions(player_id)
        player_view = self.state.to_player_view(player_id)
        action = await agent.decide(player_view, valid_actions)
        return action
```

#### 2.2.7 现金局 (cash_game.py) 与 锦标赛 (tournament.py)

```python
class CashGame:
    """现金局管理器 - 连续运行多手牌"""
    def __init__(self, config: CashGameConfig): ...
    async def run(self, num_hands: int) -> SessionResult: ...
    def add_player(self, player_id: str, buy_in: int) -> None: ...
    def remove_player(self, player_id: str) -> None: ...
    def rebuy(self, player_id: str, amount: int) -> None: ...

class Tournament:
    """锦标赛管理器 - 盲注递增、淘汰制"""
    def __init__(self, config: TournamentConfig): ...
    async def run(self) -> TournamentResult: ...
    def _increase_blinds(self) -> None: ...
    def _eliminate_player(self, player_id: str) -> None: ...
```

#### 2.2.8 手牌实验室 (hand_lab.py)

```python
@dataclass
class PlayerSetup:
    """单个玩家的预设配置"""
    agent_id: str
    chips: int
    hole_cards: list[Card] | None = None  # None 表示随机发牌
    seat_index: int = 0

@dataclass
class ScenarioConfig:
    """手牌实验室场景配置"""
    players: list[PlayerSetup]
    community_cards: list[Card] | None = None  # None = 随机; 可设 3/4/5 张
    start_street: Street = Street.PREFLOP      # 从哪条街开始
    small_blind: int = 50
    big_blind: int = 100
    dealer_index: int = 0

class HandLab:
    """手牌实验室 - 在预设场景下运行 Agent 决策"""

    def __init__(self, scenario: ScenarioConfig, agents: dict[str, BaseAgent]):
        self.scenario = scenario
        self.agents = agents

    async def run_once(self) -> HandResult:
        """运行一次预设场景，返回结果"""
        # 1. 构建 GameState，注入预设手牌和公共牌
        state = self._build_preset_state()
        # 2. 用 GameRunner 从指定街开始执行
        runner = GameRunner(state, self.agents)
        return await runner.run_hand_from(self.scenario.start_street)

    async def run_multiple(self, times: int) -> list[HandResult]:
        """同一场景运行多次，收集结果（随机部分每次不同）"""
        results = []
        for _ in range(times):
            result = await self.run_once()
            results.append(result)
        return results

    def _build_preset_state(self) -> GameState:
        """构建预设状态：指定的牌固定，未指定的随机"""
        deck = Deck()
        deck.shuffle()
        # 从牌堆中移除已预设的牌
        preset_cards = self._collect_preset_cards()
        deck.remove_cards(preset_cards)
        # 为未指定手牌的玩家随机发牌
        for player in self.scenario.players:
            if player.hole_cards is None:
                player.hole_cards = deck.deal(2)
        # 为未指定的公共牌随机发牌
        if self.scenario.community_cards is None:
            community = []  # 随机发（在对应街时发）
        else:
            community = list(self.scenario.community_cards)
        ...
```

**关键设计点**：
- `ScenarioConfig` 允许部分预设、部分随机：手牌和公共牌均可选择性指定
- `start_street` 支持从任意街开始（如直接从 flop 开始，跳过 preflop 下注）
- `run_multiple` 支持同一场景多次运行，随机部分每次不同，可观察决策稳定性
- 预设牌从牌堆中移除，保证不会重复发出
- 所有运行结果通过正常的 `HandResult` 和 `action_logs` 记录，可复用回放系统

### 2.3 Agent 系统 (agent/)

#### 2.3.1 Agent 基类

```python
# agent/base_agent.py
class BaseAgent(ABC):
    agent_id: str
    display_name: str

    @abstractmethod
    async def decide(
        self, game_view: dict, valid_actions: list[BettingAction]
    ) -> PlayerAction:
        """根据当前局面做出决策"""
        ...

    @abstractmethod
    async def notify_hand_result(self, result: HandResult) -> None:
        """手牌结束通知，用于学习"""
        ...
```

#### 2.3.2 LLM Agent

```python
# agent/llm_agent.py
class LLMAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str,
        display_name: str,
        personality: PersonalityProfile,
        llm_provider: BaseLLMProvider,
        memory_retriever: MemoryRetriever | None = None,
    ): ...

    async def decide(self, game_view: dict, valid_actions: list[BettingAction]) -> PlayerAction:
        decision_start = time.monotonic()
        try:
            # 1. 构建决策上下文
            context = self.context_builder.build(game_view, valid_actions)
            # 2. 检索历史相似场景 (RAG)
            if self.memory_retriever:
                similar_hands = await self.memory_retriever.retrieve(context)
                context.add_history_reference(similar_hands)
            # 3. 构建 prompt (含性格、水平、历史)
            prompt = self.personality.build_prompt(context)
            # 4. 调用 LLM (30秒超时)
            llm_result = await asyncio.wait_for(
                self.llm_provider.chat(prompt),
                timeout=30.0,
            )
            # 5. 记录 LLM 调用指标
            self.monitor.record_llm_call(self.agent_id, llm_result)
            # 6. 如果 LLM 调用失败，重试 1 次
            if llm_result.status == "error":
                llm_result = await asyncio.wait_for(
                    self.llm_provider.chat(prompt), timeout=30.0,
                )
                self.monitor.record_llm_call(self.agent_id, llm_result, is_retry=True)
            # 7. 仍然失败则降级 fold
            if llm_result.status != "success":
                self.monitor.record_decision(self.agent_id, "error_fallback", decision_start)
                return self._fallback_action(valid_actions)
            # 8. 解析 LLM 输出为游戏动作
            action = self.action_parser.parse(llm_result.text, valid_actions)
            # 9. 记录思考过程
            self.last_thinking = llm_result.text
            self.last_llm_metrics = llm_result
            self.monitor.record_decision(self.agent_id, "success", decision_start)
            return action
        except asyncio.TimeoutError:
            # 30 秒超时 → 自动弃牌
            self.monitor.record_decision(self.agent_id, "timeout", decision_start)
            return self._fallback_action(valid_actions)
        except Exception as e:
            # 其他异常 → 自动弃牌
            self.monitor.record_decision(self.agent_id, "exception", decision_start, str(e))
            return self._fallback_action(valid_actions)

    def _fallback_action(self, valid_actions: list[BettingAction]) -> PlayerAction:
        """兜底逻辑：能 check 就 check，否则 fold"""
        if BettingAction.CHECK in valid_actions:
            return PlayerAction(self.agent_id, BettingAction.CHECK)
        return PlayerAction(self.agent_id, BettingAction.FOLD)
```

#### 2.3.3 人类 Agent 代理

```python
# agent/human_agent.py
class HumanAgent(BaseAgent):
    """通过 WebSocket 等待人类玩家输入"""
    def __init__(self, agent_id: str, websocket_manager: WebSocketManager): ...

    async def decide(self, game_view: dict, valid_actions: list[BettingAction]) -> PlayerAction:
        # 发送游戏状态到前端
        await self.ws_manager.send_game_state(self.agent_id, game_view, valid_actions)
        # 等待人类输入 (带超时)
        action = await self.ws_manager.wait_for_action(self.agent_id, timeout=60)
        if action is None:
            return PlayerAction(self.agent_id, BettingAction.FOLD)
        return action
```

#### 2.3.4 性格模板 (personality.py)

```python
class SkillLevel(Enum):
    NOVICE = "novice"       # 新手
    INTERMEDIATE = "intermediate"  # 中级
    EXPERT = "expert"       # 高手

class PlayStyle(Enum):
    TAG = "tag"             # 紧凶 (Tight-Aggressive)
    LAG = "lag"             # 松凶 (Loose-Aggressive)
    CALLING_STATION = "calling_station"  # 松弱跟注站
    ROCK = "rock"           # 紧弱 (极紧被动)
    FISH = "fish"           # 鱼 (随机/不合理打法)
    MANIAC = "maniac"       # 疯子 (极松极凶)

@dataclass
class PersonalityProfile:
    skill_level: SkillLevel
    play_style: PlayStyle
    custom_traits: str = ""  # 用户自定义性格描述

    def build_system_prompt(self) -> str:
        """生成体现性格和水平的 system prompt"""
        ...

    def build_prompt(self, context: DecisionContext) -> list[dict]:
        """构建完整的 LLM 消息列表"""
        ...
```

**性格 Prompt 示例 (TAG高手)**：
```
你是一个经验丰富的德州扑克高手，打法风格为紧凶(TAG)。
- 你只在起手牌优质时参与手牌，翻前范围紧
- 一旦参与手牌，你倾向于主动加注而非跟注
- 你善于读牌，能根据对手的下注模式判断其手牌范围
- 你懂得在正确的时机弃牌，不会被底池套住
- 你有时会选择性诈唬(bluff)，但频率适中
- 你的决策基于底池赔率和隐含赔率
```

**性格 Prompt 示例 (鱼/新手)**：
```
你是一个德州扑克新手，经验不足，经常犯错。
- 你倾向于玩太多手牌，很难弃掉任何像样的牌
- 你经常跟注过大的下注，不太理解底池赔率
- 你有时会用弱牌过度下注
- 你很少诈唬，即使诈唬也选择不合适的时机
- 你偶尔会做出不合逻辑的决策
```

### 2.4 LLM 适配层 (llm/)

```python
# llm/base_provider.py

@dataclass
class LLMCallResult:
    """LLM 调用结果，包含响应文本和监控指标"""
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float               # 调用耗时(毫秒)
    status: str                     # "success" / "error" / "timeout"
    error_message: str | None = None
    provider_name: str = ""
    model_name: str = ""

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict]) -> LLMCallResult:
        """发送消息列表，返回包含指标的 LLMCallResult"""
        ...

    @abstractmethod
    def get_provider_name(self) -> str: ...
```

```python
# llm/anthropic_provider.py
class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages: list[dict]) -> LLMCallResult:
        start_time = time.monotonic()
        try:
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )
            latency_ms = (time.monotonic() - start_time) * 1000
            return LLMCallResult(
                text=response.content[0].text,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
                status="success",
                provider_name="anthropic",
                model_name=self.model,
            )
        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            return LLMCallResult(
                text="",
                input_tokens=0, output_tokens=0, total_tokens=0,
                latency_ms=latency_ms,
                status="error",
                error_message=str(e),
                provider_name="anthropic",
                model_name=self.model,
            )
```

```python
# llm/provider_factory.py
class ProviderFactory:
    _registry: dict[str, type[BaseLLMProvider]] = {
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type[BaseLLMProvider]) -> None: ...

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> BaseLLMProvider: ...
```

### 2.5 监控与可观测性 (monitoring/)

#### 2.5.1 LLM 调用指标采集 (llm_metrics.py)

```python
@dataclass
class LLMCallRecord:
    """单次 LLM 调用的完整指标"""
    record_id: str
    agent_id: str
    hand_id: str | None
    provider_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    status: str              # success / error / timeout
    error_message: str | None
    is_retry: bool
    created_at: str

class LLMMetricsCollector:
    """采集并存储 LLM 调用指标"""

    def __init__(self, db_session): ...

    def record(self, agent_id: str, hand_id: str | None,
               llm_result: LLMCallResult, is_retry: bool = False) -> None:
        """记录一次 LLM 调用"""
        ...

    def get_by_agent(self, agent_id: str, limit: int = 100) -> list[LLMCallRecord]: ...
    def get_by_session(self, session_id: str) -> list[LLMCallRecord]: ...
    def get_by_hand(self, hand_id: str) -> list[LLMCallRecord]: ...
```

#### 2.5.2 Agent 决策监控 (agent_monitor.py)

```python
@dataclass
class DecisionRecord:
    """单次 Agent 决策的监控记录"""
    record_id: str
    agent_id: str
    hand_id: str | None
    decision_status: str     # success / timeout / error_fallback / exception
    total_decision_ms: float # 整个决策流程耗时(含context构建、RAG检索、LLM调用)
    error_message: str | None
    created_at: str

class AgentMonitor:
    """Agent 决策行为监控"""

    def __init__(self, llm_metrics: LLMMetricsCollector, db_session): ...

    def record_llm_call(self, agent_id: str, llm_result: LLMCallResult,
                        is_retry: bool = False) -> None:
        """记录 LLM 调用指标（委托给 LLMMetricsCollector）"""
        ...

    def record_decision(self, agent_id: str, status: str,
                        start_time: float, error: str | None = None) -> None:
        """记录一次决策结果"""
        ...
```

#### 2.5.3 指标汇总 (metrics_aggregator.py)

```python
@dataclass
class AgentMetricsSummary:
    """Agent 级汇总指标"""
    agent_id: str
    total_decisions: int
    successful_decisions: int
    timeout_count: int
    error_count: int
    success_rate: float             # 成功率 0.0-1.0
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    avg_latency_ms: float           # 平均 LLM 调用耗时
    avg_decision_ms: float          # 平均决策总耗时
    p95_latency_ms: float           # P95 耗时
    total_llm_calls: int
    retry_count: int

@dataclass
class SessionMetricsSummary:
    """Session 级汇总指标"""
    session_id: str
    total_hands: int
    total_tokens: int
    total_cost_estimate: float      # 费用估算(基于 token 数)
    agent_summaries: list[AgentMetricsSummary]

@dataclass
class ProviderMetricsSummary:
    """Provider 级汇总指标"""
    provider_name: str
    total_calls: int
    success_count: int
    error_count: int
    timeout_count: int
    availability_rate: float        # 可用率
    avg_latency_ms: float
    p95_latency_ms: float

class MetricsAggregator:
    """汇总各维度的指标"""

    def __init__(self, db_session): ...

    def get_agent_summary(self, agent_id: str,
                          time_range: tuple | None = None) -> AgentMetricsSummary: ...
    def get_session_summary(self, session_id: str) -> SessionMetricsSummary: ...
    def get_provider_summary(self, provider_name: str,
                             time_range: tuple | None = None) -> ProviderMetricsSummary: ...
    def get_all_providers_summary(self) -> list[ProviderMetricsSummary]: ...
```

### 2.6 学习系统 (learning/)

```python
# learning/history_summarizer.py
class HistorySummarizer:
    """将 Agent 的历史手牌压缩为摘要"""

    def summarize_recent(self, agent_id: str, limit: int = 20) -> str:
        """最近 N 手牌的摘要（注入 prompt 用）"""
        ...

    def extract_key_lessons(self, hand_records: list[HandRecord]) -> list[str]:
        """从手牌记录中提取关键教训"""
        ...
```

```python
# learning/embedding_store.py
class EmbeddingStore:
    """基于 SQLite 的简易向量存储"""

    def store(self, agent_id: str, text: str, embedding: list[float], metadata: dict) -> None: ...
    def search(self, query_embedding: list[float], agent_id: str, top_k: int = 5) -> list[dict]: ...
```

```python
# learning/memory_retriever.py
class MemoryRetriever:
    """检索与当前局面相似的历史场景"""

    def __init__(self, embedding_store: EmbeddingStore, llm_provider: BaseLLMProvider): ...

    async def retrieve(self, context: DecisionContext) -> list[str]:
        # 1. 将当前上下文编码为向量
        # 2. 从向量存储中检索 top-k 相似场景
        # 3. 返回相关历史摘要
        ...
```

### 2.6 GTO 辅助 (gto/)

```python
# gto/equity_calculator.py
class EquityCalculator:
    """基于蒙特卡洛模拟的手牌胜率计算"""

    @staticmethod
    def calculate_equity(
        hole_cards: list[Card],
        community_cards: list[Card],
        num_opponents: int,
        simulations: int = 10000,
    ) -> float:
        """返回胜率 0.0-1.0"""
        ...
```

```python
# gto/preflop_chart.py
class PreflopChart:
    """翻前起手牌 GTO 参考表"""

    # 基于位置的翻前范围
    OPEN_RAISE_RANGE: dict[Position, set[str]] = {
        Position.UTG: {"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", ...},
        Position.MP: {...},
        Position.CO: {...},
        Position.BTN: {...},
        Position.SB: {...},
    }

    @classmethod
    def get_recommendation(
        cls, hole_cards: list[Card], position: Position, action_before: list[str]
    ) -> str:
        """返回 GTO 推荐动作"""
        ...
```

```python
# gto/gto_advisor.py
class GTOAdvisor:
    """综合 GTO 建议器"""

    def __init__(self, equity_calc: EquityCalculator, preflop_chart: PreflopChart): ...

    def advise(self, game_view: dict, valid_actions: list[BettingAction]) -> dict:
        """返回 GTO 建议：推荐动作 + 理由 + equity"""
        ...
```

### 2.7 数据库设计

#### agents 表
```sql
CREATE TABLE agents (
    agent_id        TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    skill_level     TEXT NOT NULL,  -- novice/intermediate/expert
    play_style      TEXT NOT NULL,  -- tag/lag/fish/...
    custom_traits   TEXT DEFAULT '',
    llm_provider    TEXT NOT NULL,  -- anthropic/openai/...
    llm_model       TEXT NOT NULL,
    llm_api_key     TEXT,           -- 加密存储
    total_hands     INTEGER DEFAULT 0,
    total_profit    INTEGER DEFAULT 0,
    win_rate        REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

#### game_sessions 表
```sql
CREATE TABLE game_sessions (
    session_id      TEXT PRIMARY KEY,
    game_type       TEXT NOT NULL,  -- cash/tournament
    status          TEXT NOT NULL,  -- waiting/running/finished
    small_blind     INTEGER NOT NULL,
    big_blind       INTEGER NOT NULL,
    max_players     INTEGER NOT NULL,
    config_json     TEXT,           -- 额外配置 JSON
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT NOT NULL
);
```

#### session_players 表
```sql
CREATE TABLE session_players (
    session_id      TEXT NOT NULL,
    player_id       TEXT NOT NULL,  -- agent_id 或 human player id
    player_type     TEXT NOT NULL,  -- agent/human
    seat_index      INTEGER NOT NULL,
    buy_in          INTEGER NOT NULL,
    final_chips     INTEGER,
    profit          INTEGER,
    PRIMARY KEY (session_id, player_id)
);
```

#### hand_records 表
```sql
CREATE TABLE hand_records (
    hand_id         TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    hand_number     INTEGER NOT NULL,
    dealer_seat     INTEGER NOT NULL,
    community_cards TEXT,           -- JSON: ["Ah","Kd","Qc","Js","Td"]
    pot_total       INTEGER,
    winners_json    TEXT,           -- JSON: {"player_id": amount}
    started_at      TEXT NOT NULL,
    finished_at     TEXT
);
```

#### hand_players 表
```sql
CREATE TABLE hand_players (
    hand_id         TEXT NOT NULL,
    player_id       TEXT NOT NULL,
    seat_index      INTEGER NOT NULL,
    hole_cards      TEXT,           -- JSON: ["Ah","Kd"]
    final_hand_rank TEXT,           -- "flush", "two_pair" 等
    chips_before    INTEGER NOT NULL,
    chips_after     INTEGER NOT NULL,
    profit          INTEGER NOT NULL,
    PRIMARY KEY (hand_id, player_id)
);
```

#### action_logs 表
```sql
CREATE TABLE action_logs (
    action_id       TEXT PRIMARY KEY,
    hand_id         TEXT NOT NULL,
    player_id       TEXT NOT NULL,
    street          TEXT NOT NULL,  -- preflop/flop/turn/river
    action_type     TEXT NOT NULL,  -- fold/check/call/raise/all_in
    amount          INTEGER DEFAULT 0,
    pot_before      INTEGER,
    thinking_text   TEXT,           -- Agent 的思考过程原文
    is_timeout      BOOLEAN DEFAULT FALSE,  -- 是否因超时自动fold
    is_fallback     BOOLEAN DEFAULT FALSE,  -- 是否因异常降级的动作
    input_tokens    INTEGER DEFAULT 0,      -- 本次决策的 input token
    output_tokens   INTEGER DEFAULT 0,      -- 本次决策的 output token
    llm_latency_ms  REAL DEFAULT 0,         -- LLM 调用耗时
    decision_ms     REAL DEFAULT 0,         -- 决策总耗时
    action_order    INTEGER NOT NULL,
    created_at      TEXT NOT NULL
);
```

#### hand_lab_scenarios 表 (手牌实验室场景模板)
```sql
CREATE TABLE hand_lab_scenarios (
    scenario_id     TEXT PRIMARY KEY,
    scenario_name   TEXT NOT NULL,
    description     TEXT DEFAULT '',
    config_json     TEXT NOT NULL,      -- ScenarioConfig 序列化 JSON
                                        -- 包含: players(agent_id, chips, hole_cards),
                                        -- community_cards, start_street, blinds
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

#### hand_lab_runs 表 (实验室运行记录)
```sql
CREATE TABLE hand_lab_runs (
    run_id          TEXT PRIMARY KEY,
    scenario_id     TEXT NOT NULL,
    hand_id         TEXT NOT NULL,      -- 关联到 hand_records 表（复用回放系统）
    run_index       INTEGER NOT NULL,   -- 第几次运行 (多次运行时的序号)
    created_at      TEXT NOT NULL,
    FOREIGN KEY (scenario_id) REFERENCES hand_lab_scenarios(scenario_id),
    FOREIGN KEY (hand_id) REFERENCES hand_records(hand_id)
);
```

#### llm_call_logs 表 (LLM 调用指标)
```sql
CREATE TABLE llm_call_logs (
    record_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    hand_id         TEXT,
    session_id      TEXT,
    provider_name   TEXT NOT NULL,     -- anthropic / openai / ...
    model_name      TEXT NOT NULL,     -- claude-sonnet-4-20250514 等
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    latency_ms      REAL NOT NULL,     -- 调用耗时(毫秒)
    status          TEXT NOT NULL,     -- success / error / timeout
    error_message   TEXT,
    is_retry        BOOLEAN DEFAULT FALSE,
    created_at      TEXT NOT NULL
);
CREATE INDEX idx_llm_logs_agent ON llm_call_logs(agent_id);
CREATE INDEX idx_llm_logs_session ON llm_call_logs(session_id);
CREATE INDEX idx_llm_logs_provider ON llm_call_logs(provider_name);
```

#### decision_logs 表 (Agent 决策监控)
```sql
CREATE TABLE decision_logs (
    record_id           TEXT PRIMARY KEY,
    agent_id            TEXT NOT NULL,
    hand_id             TEXT,
    session_id          TEXT,
    decision_status     TEXT NOT NULL,  -- success / timeout / error_fallback / exception
    total_decision_ms   REAL NOT NULL,  -- 决策总耗时(含context构建+RAG+LLM)
    error_message       TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX idx_decision_logs_agent ON decision_logs(agent_id);
CREATE INDEX idx_decision_logs_session ON decision_logs(session_id);
```

#### agent_memories 表 (RAG 向量存储)
```sql
CREATE TABLE agent_memories (
    memory_id       TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    hand_id         TEXT,
    summary_text    TEXT NOT NULL,
    embedding_blob  BLOB,           -- numpy array 序列化
    lesson_type     TEXT,           -- win/loss/bluff/bad_call/...
    created_at      TEXT NOT NULL
);
```

### 2.8 API 设计

#### REST API

```
# Agent 管理
POST   /api/agents                  创建 Agent
GET    /api/agents                  列表所有 Agent
GET    /api/agents/{agent_id}       获取 Agent 详情
PUT    /api/agents/{agent_id}       更新 Agent 配置
DELETE /api/agents/{agent_id}       删除 Agent
GET    /api/agents/{agent_id}/stats 获取 Agent 统计数据
GET    /api/agents/{agent_id}/hands 获取 Agent 历史手牌

# 牌局管理
POST   /api/games                   创建新牌局
GET    /api/games                   列表所有牌局
GET    /api/games/{session_id}      获取牌局详情
POST   /api/games/{session_id}/start  启动牌局
POST   /api/games/{session_id}/stop   停止牌局
POST   /api/games/{session_id}/players  添加玩家到牌局

# 回放
GET    /api/replay/sessions/{session_id}        获取某 session 的所有手牌列表
GET    /api/replay/hands/{hand_id}              获取单手牌完整回放数据
GET    /api/replay/hands/{hand_id}/actions      获取动作序列(含 thinking)
GET    /api/replay/players/{player_id}/hands    按玩家查询手牌历史

# 手牌实验室
POST   /api/handlab/scenarios              创建/保存场景模板
GET    /api/handlab/scenarios              列表已保存场景
GET    /api/handlab/scenarios/{id}         获取场景详情
DELETE /api/handlab/scenarios/{id}         删除场景
POST   /api/handlab/run                    运行一次场景 (返回结果)
POST   /api/handlab/run-multiple           运行多次场景 (返回结果列表)
GET    /api/handlab/runs/{scenario_id}     获取某场景的历次运行结果

# 监控
GET    /api/monitoring/agents/{agent_id}          Agent 级指标汇总(token/耗时/成功率)
GET    /api/monitoring/agents/{agent_id}/llm-calls Agent 的 LLM 调用明细列表
GET    /api/monitoring/agents/{agent_id}/decisions Agent 的决策记录明细列表
GET    /api/monitoring/sessions/{session_id}       Session 级指标汇总(总token/总耗时/费用)
GET    /api/monitoring/hands/{hand_id}/llm-calls   单手牌中的 LLM 调用明细
GET    /api/monitoring/providers                   所有 Provider 可用性汇总
GET    /api/monitoring/providers/{name}            单个 Provider 指标详情
GET    /api/monitoring/overview                    全局概览(总调用/总token/各Provider状态)
```

#### WebSocket API

```
WS /ws/game/{session_id}

# 服务端推送消息类型:
{
    "type": "game_state_update",   # 牌局状态更新
    "type": "action_required",     # 请求人类玩家操作
    "type": "hand_complete",       # 一手牌结束
    "type": "agent_thinking",      # Agent 思考中(加载动画)
    "type": "agent_action",        # Agent 做出动作(含思考过程+token/耗时指标)
    "type": "agent_timeout",       # Agent 决策超时，自动 fold/check
    "type": "agent_error",         # Agent LLM 调用异常，已降级处理
    "type": "session_complete",    # 整个 session 结束
}

# 客户端发送消息类型:
{
    "type": "player_action",       # 人类玩家提交操作
    "type": "spectate",            # 请求观战
}
```

---

## 3. 前端架构

### 3.1 页面结构

| 页面 | 路由 | 描述 |
|------|------|------|
| 仪表盘 | `/` | 概览：活跃牌局、Agent 列表、快速开始 |
| Agent 管理 | `/agents` | CRUD Agent、查看统计 |
| 创建牌局 | `/games/new` | 配置规则、选择参与者 |
| 牌桌 | `/games/:id` | 实时牌局页面（打牌/观战） |
| 回放 | `/replay/:handId` | 手牌回放播放器 |
| 历史 | `/history` | 牌局和手牌历史列表 |
| 手牌实验室 | `/handlab` | 创建预设场景、运行、查看结果对比 |
| 实验室结果 | `/handlab/:scenarioId` | 某场景的运行结果和对比分析 |
| 监控中心 | `/monitoring` | Token消耗、耗时、成功率、Provider稳定性 |

### 3.2 牌桌 UI 布局

```
┌──────────────────────────────────────────┐
│  Agent思考面板(右侧抽屉)                  │
│ ┌──────────────────────────────────────┐ │
│ │          社区公共牌区域                │ │
│ │        [Ah] [Kd] [Qc] [?] [?]       │ │
│ │                                      │ │
│ │    座位2         底池: 1500    座位3   │ │
│ │   [Avatar]    ┌──────────┐  [Avatar] │ │
│ │   Chips:800   │  POT区域  │  Chips:1200│
│ │               └──────────┘           │ │
│ │  座位1                        座位4   │ │
│ │  [Avatar]                   [Avatar] │ │
│ │  Chips:500                  Chips:2000│ │
│ │                                      │ │
│ │           ┌──────────────┐           │ │
│ │           │  [你的手牌]    │           │ │
│ │           │  [Ks] [Qs]   │           │ │
│ │           └──────────────┘           │ │
│ │  ┌─────┐ ┌─────┐ ┌───────────────┐  │ │
│ │  │ 弃牌 │ │ 跟注 │ │ 加注 [slider] │  │ │
│ │  └─────┘ └─────┘ └───────────────┘  │ │
│ └──────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### 3.3 实时通信流程

```
人类操作:
  前端 ActionPanel → WebSocket send → 后端 websocket_handler
  → game_service → game_runner → 更新 game_state
  → WebSocket broadcast → 前端 PokerTable 更新

Agent 决策:
  game_runner → agent.decide() → LLM API 调用
  → WebSocket broadcast "agent_thinking"
  → 收到 LLM 响应 → 解析动作
  → WebSocket broadcast "agent_action" (含思考过程)
  → 前端 Seat 组件展示动画 + ThinkingPanel 展示思考

观战:
  前端 connect WebSocket → send {type: "spectate"}
  → 收到所有 game_state_update 事件 → 只读渲染
```

### 3.4 回放系统

```
回放数据结构:
{
  hand_id: "xxx",
  players: [{id, name, seat, hole_cards, chips_before, chips_after}],
  community_cards: ["Ah", "Kd", "Qc", "Js", "Td"],
  actions: [
    {order: 1, player_id, street: "preflop", action: "raise", amount: 100,
     pot_before: 150, thinking: "我有AA，应该加注..."},
    {order: 2, player_id, street: "preflop", action: "call", amount: 100,
     pot_before: 250, thinking: "KQs在位置上可以跟注..."},
    ...
  ],
  result: {winners: [{player_id, amount, hand_rank: "flush"}]}
}

回放播放器:
  ReplayPlayer 组件 → 按 action_order 逐步推进
  → 每步更新牌桌状态 + 高亮当前玩家
  → ThinkingPanel 展示当前步骤的 Agent 思考
  → ReplayControls: ▶ ⏸ ⏩ ⏪ 进度条
```

---

## 4. 关键数据流

### 4.1 Agent 决策管道

```
GameRunner.request_player_action(player_id)
  │
  ├─ 1. GameState.to_player_view(player_id)
  │     → 生成该玩家可见的牌局信息 (隐藏他人手牌)
  │
  ├─ 2. DecisionContext.build(player_view, valid_actions)
  │     → 结构化决策上下文: 手牌、位置、底池赔率、对手动作历史
  │
  ├─ 3. HistorySummarizer.get_recent_summary(agent_id)
  │     → 近期手牌摘要 (短期记忆)
  │
  ├─ 4. MemoryRetriever.retrieve(context)  [可选,P1]
  │     → RAG 检索相似历史场景 (长期记忆)
  │
  ├─ 5. GTOAdvisor.advise(game_view)  [可选,P1]
  │     → GTO 策略参考
  │
  ├─ 6. PersonalityProfile.build_prompt(context, history, gto_advice)
  │     → 组装完整 prompt (system + user messages)
  │
  ├─ 7. LLMProvider.chat(messages)
  │     → 调用 LLM API 获取决策
  │
  ├─ 8. ActionParser.parse(llm_response, valid_actions)
  │     → 解析 LLM 输出为合法游戏动作
  │     → 如果解析失败，重试或降级为默认动作(check/fold)
  │
  └─ 9. 记录 action_log (含 thinking_text)
```

### 4.2 LLM Prompt 结构

```
System Message:
  你是 {agent_name}，一个德州扑克{skill_level}。
  {personality_description}
  {gto_reference (可选)}

User Message:
  ## 当前牌局信息
  - 你的手牌: {hole_cards}
  - 公共牌: {community_cards}
  - 你的位置: {position}
  - 底池: {pot}
  - 你的筹码: {chips}
  - 当前需跟注: {to_call}
  - 底池赔率: {pot_odds}

  ## 本手行动历史
  {action_history_this_hand}

  ## 对手信息
  {opponents_summary}

  ## 你的近期表现回顾
  {recent_history_summary}

  ## 相似场景参考 (RAG)
  {similar_scenarios}

  ## 可用动作
  {valid_actions_with_ranges}

  请分析当前局面，给出你的决策。
  格式: ACTION: {fold/check/call/raise} [AMOUNT: xxx]
  先给出你的思考过程，再给出最终决策。
```

---

## 5. 开发阶段规划

### Phase 1: 引擎核心 + CLI 试跑
**文件**: engine/*, agent/base_agent.py, scripts/run_cli_game.py
- 完成德扑规则引擎全部模块
- 实现简单随机 Agent (用于测试)
- CLI 脚本可运行一手完整牌局

### Phase 2: Agent 系统 + LLM 集成 + 监控
**文件**: agent/*, llm/*, monitoring/*
- LLM Agent 决策管道（含 30s 超时兜底、失败重试 1 次）
- LLMCallResult 结构（携带 token/latency/status 指标）
- Anthropic Provider 实现
- 性格模板系统
- 监控模块：LLMMetricsCollector、AgentMonitor、MetricsAggregator
- Agent 可通过 CLI 对战，CLI 打印 token 消耗和耗时

### Phase 3: 数据持久化 + API
**文件**: models/*, database.py, api/*, services/*
- 数据库 schema + ORM 模型（含 llm_call_logs、decision_logs 表）
- REST API (Agent CRUD, 牌局管理, 监控查询)
- WebSocket 处理器
- 手牌记录存储（action_logs 含 token/latency 字段）

### Phase 4: 前端核心
**文件**: frontend/*
- React 项目搭建
- 牌桌 UI 组件（Agent 超时时展示倒计时 + 超时提示）
- 实时对局页面 (WebSocket)
- Agent 管理页面
- 监控中心页面（Token 用量图表、耗时图表、成功率、Provider 状态）

### Phase 5: 回放 + 历史 + 手牌实验室
**文件**: api/replay_routes.py, services/replay_service.py, frontend/replay/*, engine/hand_lab.py, api/hand_lab_routes.py, services/hand_lab_service.py, frontend/handlab/*
- 回放数据 API
- 前端回放播放器
- 按玩家/Agent 筛选
- 手牌实验室后端：ScenarioConfig、HandLab 运行器
- 手牌实验室 API：场景 CRUD、运行、多次运行
- 手牌实验室前端：CardPicker 选牌器、场景配置、运行结果对比

### Phase 6: 学习 + GTO + 打磨
**文件**: learning/*, gto/*
- 历史摘要生成 (短期学习)
- RAG 向量存储 + 检索 (长期学习)
- GTO equity 计算 + 翻前表
- 锦标赛模式完善
- UI 打磨 + 全面测试
