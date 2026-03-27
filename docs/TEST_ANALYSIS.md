# PokerClaw — 测试分析文档

## 1. 测试策略概览

```
测试金字塔:

        ┌──────────┐
        │  E2E 测试 │   少量：完整对局端到端
        ├──────────┤
        │ 集成测试  │   中量：模块间协作
        ├──────────┤
        │ 单元测试  │   大量：每个子函数
        └──────────┘
```

| 层级 | 数量 | 工具 | 关注点 |
|------|------|------|--------|
| 单元测试 | ~120+ | pytest | 每个函数的输入/输出正确性 |
| 集成测试 | ~20+ | pytest + pytest-asyncio | 模块间协作，数据流通 |
| E2E 测试 | ~5+ | pytest + httpx (后端) / Playwright (前端) | 完整用户流程 |
| 最小原型试跑 | 3 | scripts/ | CLI 可运行的最小完整场景 |

**测试框架**: pytest + pytest-asyncio + pytest-cov
**Mock 工具**: unittest.mock / pytest-mock
**前端测试**: Vitest + React Testing Library

---

## 2. 单元测试详细设计

### 2.1 引擎层 (engine/) — 最关键

#### test_card.py
```
test_card_creation              创建 Card 对象，验证 rank 和 suit
test_card_string_representation Card 的字符串表示（如 "Ah", "Td"）
test_card_equality              两张相同牌相等
test_card_from_string           从字符串 "Ah" 解析为 Card
test_card_invalid_string        无效字符串抛出异常
```

#### test_deck.py
```
test_deck_has_52_cards          新牌堆有 52 张不重复的牌
test_deck_shuffle_randomness    洗牌后顺序改变
test_deal_reduces_count         发牌后牌堆数量减少
test_deal_no_duplicate          连续发牌不出现重复
test_deal_from_empty_deck       空牌堆发牌抛异常
```

#### test_hand_evaluator.py — 核心，需覆盖所有牌型
```
# 牌型识别
test_royal_flush                皇家同花顺识别
test_straight_flush             同花顺识别
test_four_of_a_kind             四条识别
test_full_house                 葫芦识别
test_flush                      同花识别
test_straight                   顺子识别
test_straight_ace_low           A-2-3-4-5 最小顺子
test_three_of_a_kind            三条识别
test_two_pair                   两对识别
test_one_pair                   一对识别
test_high_card                  高牌识别

# 比较
test_flush_beats_straight       同花 > 顺子
test_higher_pair_wins           大对子赢小对子
test_kicker_comparison          同牌型比 kicker
test_split_pot_same_hand        完全相同牌型平分底池
test_two_pair_comparison        两对比较（先比大对，再比小对，再比 kicker）
test_full_house_comparison      葫芦比较（先比三条，再比对子）

# 七选五
test_best_five_from_seven       从 7 张中选最优 5 张
test_community_plays            5 张公共牌本身是最优时
```

#### test_pot_manager.py
```
test_simple_pot                 简单底池累加
test_side_pot_single_allin      一人 all-in 产生边池
test_side_pot_multiple_allin    多人不同筹码 all-in
test_side_pot_distribution      边池正确分配给获胜者
test_three_way_allin            三人不同筹码 all-in 的底池拆分
test_odd_chip_distribution      奇数筹码的分配规则
```

#### test_betting_round.py
```
test_valid_actions_first_to_act 首个行动者的合法动作
test_valid_actions_after_raise  加注后的合法动作
test_fold_removes_player        弃牌后玩家不再参与
test_call_matches_bet           跟注金额正确
test_raise_minimum              最小加注额度正确
test_raise_maximum_allin        加注到 all-in
test_round_complete_all_check   全部过牌结束轮次
test_round_complete_after_call  跟注完毕结束轮次
test_big_blind_option           大盲位的特殊行动权
test_heads_up_blinds            单挑时盲注位置正确
```

#### test_game_state.py
```
test_initial_state              初始状态正确
test_player_view_hides_others   玩家视角隐藏他人手牌
test_full_view_shows_all        完整视角显示所有信息
test_active_player_count        正确计算活跃玩家数
test_dealer_rotation            庄家位置轮转
```

#### test_game_runner.py
```
test_complete_hand_to_showdown  完整一手牌到摊牌
test_hand_ends_on_fold          所有人弃牌提前结束
test_allin_and_runout           all-in 后自动发完公共牌
test_blind_posting              盲注正确收取
test_dealer_button_advance      庄家按钮正确移动
```

#### test_cash_game.py
```
test_cash_game_runs_n_hands     运行 N 手牌
test_player_join_mid_session    中途加入玩家
test_player_leave               玩家离开
test_rebuy                      重新买入
test_chip_tracking              筹码追踪准确
```

#### test_tournament.py
```
test_tournament_elimination     玩家淘汰机制
test_blind_increase_schedule    盲注递增
test_tournament_winner          最终冠军判定
test_limited_rebuy              有限次买入
test_single_buy_in              单次买入不可重购
```

#### test_hand_lab.py
```
test_preset_hole_cards          指定手牌正确分配给玩家
test_random_hole_cards          未指定手牌的玩家随机发牌
test_preset_community_cards     指定公共牌正确设置
test_random_community_cards     未指定公共牌时随机发牌
test_no_duplicate_cards         预设牌不会在随机发牌中重复出现
test_start_from_flop            从 flop 街开始运行
test_start_from_turn            从 turn 街开始运行
test_start_from_river           从 river 街开始运行
test_run_once_returns_result    单次运行返回完整 HandResult
test_run_multiple_times         多次运行返回对应数量的结果
test_run_multiple_random_varies 多次运行中随机部分每次不同
test_mixed_preset_and_random    部分玩家指定手牌、部分随机
test_preset_partial_community   只指定 flop(3张)，turn/river 随机
test_scenario_recorded_to_db    实验结果正确写入数据库（复用回放系统）
```

### 2.2 Agent 层 (agent/)

#### test_personality.py
```
test_tag_system_prompt          TAG 性格生成正确的 system prompt
test_lag_system_prompt          LAG 性格生成正确的 prompt
test_fish_system_prompt         鱼的 prompt 包含新手特征
test_custom_traits_included     自定义特征被包含在 prompt 中
test_skill_level_affects_prompt 不同水平影响 prompt 内容
```

#### test_decision_context.py
```
test_context_includes_hole_cards    上下文包含手牌信息
test_context_includes_pot_odds      上下文包含底池赔率
test_context_includes_position      上下文包含位置信息
test_context_includes_action_history 上下文包含历史动作
test_context_formatting             上下文格式化为可读文本
```

#### test_action_parser.py
```
test_parse_fold                 解析 "ACTION: fold"
test_parse_call                 解析 "ACTION: call"
test_parse_raise_with_amount    解析 "ACTION: raise AMOUNT: 200"
test_parse_from_natural_text    从自然文本中提取动作
test_parse_invalid_fallback     无法解析时降级为 fold/check
test_validate_against_valid_actions 验证解析结果在合法动作范围内
test_raise_amount_clamping      加注金额超范围时裁剪到合法范围
```

#### test_llm_agent.py
```
test_decide_calls_llm           decide 方法调用 LLM
test_decide_records_thinking    思考过程被记录
test_decide_with_history        历史摘要被注入 prompt
test_decide_with_rag            RAG 检索结果被注入 prompt
test_notify_hand_result         手牌结果通知更新统计
test_decide_timeout_30s_folds   LLM 超过30秒未响应自动 fold
test_decide_timeout_can_check   超时时如果可 check 则 check 而非 fold
test_decide_error_retry_once    LLM 调用失败自动重试 1 次
test_decide_retry_fail_folds    重试仍失败则降级 fold
test_decide_exception_folds     未预期异常时降级 fold
test_decide_records_llm_metrics 决策后记录 token 数和耗时到监控
test_decide_records_decision_status 决策状态(success/timeout/error)被记录
```

### 2.3 LLM 层 (llm/)

#### test_provider_factory.py
```
test_create_anthropic_provider  创建 Anthropic Provider
test_register_custom_provider   注册自定义 Provider
test_provider_returns_llm_call_result  Provider 返回 LLMCallResult 对象
test_provider_result_has_token_counts  返回结果包含 input/output token
test_provider_result_has_latency       返回结果包含 latency_ms
test_provider_error_returns_error_status  异常时返回 status="error"
test_create_unknown_provider    创建未知 Provider 抛异常
test_provider_interface         Provider 实现了所有接口方法
```

> **注意**: LLM 的实际 API 调用在单元测试中通过 mock 模拟。集成测试中可选真实调用。

### 2.4 学习层 (learning/)

#### test_history_summarizer.py
```
test_summarize_winning_hand     赢牌总结包含关键信息
test_summarize_losing_hand      输牌总结包含教训
test_summarize_empty_history    无历史时返回空摘要
test_extract_key_lessons        正确提取经验教训
test_summary_length_limit       摘要在 token 限制内
```

#### test_memory_retriever.py
```
test_store_and_retrieve         存储后可检索
test_retrieve_similar_scenario  检索返回相似场景
test_retrieve_empty_store       空存储返回空列表
test_top_k_limit                检索结果数量限制
```

### 2.5 GTO 层 (gto/)

#### test_equity_calculator.py
```
test_pocket_aces_equity         AA 对随机手牌胜率 ~85%
test_dominated_hand             AK vs AQ 的胜率差异
test_flush_draw_equity          同花听牌的胜率 ~35%
test_set_vs_overpair            暗三条 vs 超对的胜率
test_equity_with_community      有公共牌时的胜率计算
```

#### test_preflop_chart.py
```
test_premium_hands_utg          UTG 位置 AA/KK/QQ 推荐加注
test_marginal_hands_btn         BTN 位置边缘牌推荐加注
test_weak_hands_utg_fold        UTG 位置弱牌推荐弃牌
test_facing_raise_range         面对加注的跟注/再加注范围
```

### 2.6 监控层 (monitoring/)

#### test_llm_metrics.py
```
test_record_successful_call         记录成功的 LLM 调用
test_record_error_call              记录失败的 LLM 调用
test_record_timeout_call            记录超时的 LLM 调用
test_record_retry_call              记录重试调用(is_retry=True)
test_get_by_agent                   按 agent_id 查询调用记录
test_get_by_session                 按 session_id 查询调用记录
test_get_by_hand                    按 hand_id 查询调用记录
test_token_counts_accurate          token 数与 LLMCallResult 一致
test_latency_recorded               耗时正确记录
```

#### test_agent_monitor.py
```
test_record_success_decision        记录成功决策
test_record_timeout_decision        记录超时决策
test_record_error_fallback          记录错误降级决策
test_record_exception_decision      记录异常决策
test_decision_ms_calculated         决策总耗时正确计算
test_delegates_to_llm_metrics       LLM 调用委托给 LLMMetricsCollector
```

#### test_metrics_aggregator.py
```
test_agent_summary_success_rate     Agent 成功率正确计算
test_agent_summary_token_totals     Agent token 合计正确
test_agent_summary_avg_latency      Agent 平均耗时正确
test_agent_summary_p95_latency      Agent P95 耗时正确
test_agent_summary_timeout_count    Agent 超时次数正确
test_session_summary                Session 级汇总正确
test_session_cost_estimate          Session 费用估算合理
test_provider_availability          Provider 可用率正确计算
test_provider_summary_all           所有 Provider 汇总列表正确
test_time_range_filter              时间范围筛选生效
test_empty_data_returns_zeros       无数据时返回零值不报错
```

### 2.7 API 层 (api/)

#### test_agent_routes.py
```
test_create_agent               POST /api/agents 创建成功
test_create_agent_validation    缺少必填字段返回 422
test_list_agents                GET /api/agents 返回列表
test_get_agent_detail           GET /api/agents/{id} 返回详情
test_update_agent               PUT /api/agents/{id} 更新成功
test_delete_agent               DELETE /api/agents/{id} 删除成功
test_agent_not_found            访问不存在的 Agent 返回 404
test_agent_stats                GET /api/agents/{id}/stats 返回统计
test_agent_hands_history        GET /api/agents/{id}/hands 返回手牌历史
```

#### test_game_routes.py
```
test_create_game                POST /api/games 创建牌局
test_create_game_cash_type      创建现金局
test_create_game_tournament     创建锦标赛
test_start_game                 POST /api/games/{id}/start 启动
test_start_game_insufficient    玩家不足时无法启动
test_add_player_to_game         POST /api/games/{id}/players 添加玩家
test_list_games                 GET /api/games 列表
```

#### test_replay_routes.py
```
test_get_session_hands          获取某 session 的手牌列表
test_get_hand_detail            获取单手牌完整数据
test_get_hand_actions           获取动作序列含思考过程
test_filter_by_player           按玩家筛选手牌
test_replay_nonexistent_hand    不存在的手牌返回 404
```

#### test_hand_lab_routes.py
```
test_create_scenario            POST /api/handlab/scenarios 创建场景
test_create_scenario_validation 缺少必填字段返回 422
test_list_scenarios             GET /api/handlab/scenarios 返回列表
test_get_scenario_detail        GET /api/handlab/scenarios/{id} 返回详情
test_delete_scenario            DELETE /api/handlab/scenarios/{id} 删除
test_run_scenario               POST /api/handlab/run 运行场景返回结果
test_run_multiple               POST /api/handlab/run-multiple 多次运行
test_run_with_preset_cards      指定手牌运行正确
test_run_with_random_cards      随机手牌运行正确
test_run_invalid_scenario       无效场景返回 400
test_get_run_history            GET /api/handlab/runs/{id} 返回运行历史
test_duplicate_preset_cards     预设牌有重复时返回 400
```

#### test_monitoring_routes.py
```
test_get_agent_metrics          GET /api/monitoring/agents/{id} 返回汇总
test_get_agent_llm_calls        GET /api/monitoring/agents/{id}/llm-calls 返回明细
test_get_agent_decisions        GET /api/monitoring/agents/{id}/decisions 返回决策记录
test_get_session_metrics        GET /api/monitoring/sessions/{id} 返回 Session 汇总
test_get_hand_llm_calls         GET /api/monitoring/hands/{id}/llm-calls 返回明细
test_get_providers_overview     GET /api/monitoring/providers 返回所有 Provider
test_get_provider_detail        GET /api/monitoring/providers/{name} 返回单个 Provider
test_get_global_overview        GET /api/monitoring/overview 返回全局概览
test_empty_metrics_not_error    无数据时返回空结果而非报错
test_time_range_query_param     支持 ?from=&to= 时间范围筛选
```

---

## 3. 集成测试

### integration/test_full_hand.py
```
test_full_hand_with_mock_agents
  创建 4 个使用固定策略的 mock agent → 运行一手完整牌局
  → 验证: 牌局正确结束、底池正确分配、筹码变化正确、
         动作日志完整记录、手牌记录写入数据库

test_full_hand_with_side_pot
  3 个 agent 不同筹码 → all-in 场景
  → 验证: 边池正确计算和分配

test_full_hand_recorded_to_db
  运行一手牌 → 查询数据库
  → 验证: hand_records, hand_players, action_logs 完整
```

### integration/test_agent_vs_agent.py
```
test_two_llm_agents_play_hand
  2 个 LLM Agent (mock LLM 返回) → 对战一手牌
  → 验证: 决策管道正常、thinking 被记录

test_human_and_agents_mixed
  1 个 mock Human Agent + 2 个 Agent → 对战
  → 验证: Human Agent 的等待/输入流程正常

test_agent_learning_after_session
  1 个 Agent 打 10 手牌 → 检查历史摘要
  → 验证: 第 11 手牌的 prompt 中包含历史摘要

test_cash_game_10_hands
  4 个 Agent → 现金局运行 10 手牌
  → 验证: 筹码连续正确、庄家轮转、手牌记录完整
```

### integration/test_api_game_flow.py
```
test_api_create_and_start_game
  通过 API 创建 Agent → 创建牌局 → 添加玩家 → 启动
  → 验证: 状态变化正确

test_api_replay_after_game
  运行一局完整游戏 → 通过回放 API 获取数据
  → 验证: 回放数据完整、含 Agent 思考过程
```

### integration/test_hand_lab_flow.py
```
test_hand_lab_preset_all_cards
  4 个 Agent 全部指定手牌 + 指定公共牌 → 运行
  → 验证: 所有预设牌正确、Agent 决策正常、结果记录完整

test_hand_lab_partial_random
  2 个 Agent 指定手牌 + 2 个随机 → flop 指定, turn/river 随机
  → 验证: 指定牌固定、随机牌不重复、可回放

test_hand_lab_run_multiple_same_scenario
  同一场景（部分固定手牌）运行 5 次
  → 验证: 固定部分每次一致、随机部分有变化、结果列表长度 5

test_hand_lab_start_from_flop
  从 flop 街开始（跳过 preflop 下注）→ 运行
  → 验证: 从 flop 正确开始、无 preflop 动作记录

test_hand_lab_save_and_reload_scenario
  创建场景 → 保存到 DB → 重新加载 → 运行
  → 验证: 加载后的配置与原始一致

test_hand_lab_result_reuses_replay
  运行手牌实验室 → 通过回放 API 获取同一 hand_id 的数据
  → 验证: 回放系统可直接查看实验室运行的结果
```

### integration/test_monitoring_flow.py
```
test_metrics_recorded_during_game
  4 个 mock Agent → 现金局运行 5 手牌
  → 验证: llm_call_logs 有对应记录、decision_logs 有对应记录
         action_logs 中 input_tokens/output_tokens 有值

test_timeout_agent_auto_folds
  1 个故意延迟>30s 的 mock Agent + 2 个正常 Agent → 对战
  → 验证: 超时 Agent 自动 fold、action_logs.is_timeout=True
         decision_logs.decision_status="timeout"

test_error_agent_retry_and_fallback
  1 个首次返回 error 的 mock Provider → Agent 对战
  → 验证: 自动重试 1 次、llm_call_logs 有 is_retry=True 记录
         如果重试仍失败 → fold 并记录 error_fallback

test_agent_metrics_aggregate_after_session
  运行 10 手牌 → 查询 Agent 汇总
  → 验证: total_decisions/success_rate/avg_latency 等指标正确

test_provider_availability_tracked
  混合使用 success/error 的 mock Provider → 运行
  → 验证: Provider 可用率正确反映 success/total 比率

test_session_token_cost_estimate
  运行 session → 查询 session 汇总
  → 验证: total_tokens 与各手牌 token 之和一致
         total_cost_estimate > 0
```

---

## 4. 最小原型试跑 (Minimal Prototype Runs)

### 4.1 CLI 试跑脚本: scripts/run_cli_game.py

```python
"""
最小原型: 在命令行中运行一手 Agent 对战
用法: python scripts/run_cli_game.py

预期输出:
  - 发牌信息
  - 每个 Agent 的行动 (含思考过程摘要)
  - 每条街的公共牌
  - 最终摊牌结果和筹码变化
"""
```

验证点:
- [x] 牌局引擎正确运行完整一手牌
- [x] Agent 能通过 LLM (或 mock) 做出合法决策
- [x] 动作日志完整打印
- [x] 底池和筹码计算正确

### 4.2 CLI 多手牌试跑: scripts/run_session.py

```python
"""
运行一个包含 N 手牌的现金局 session
用法: python scripts/run_session.py --hands 20 --players 4
"""
```

验证点:
- [x] 连续多手牌运行不崩溃
- [x] 庄家轮转正确
- [x] 筹码追踪准确
- [x] 数据正确写入数据库

### 4.3 API + 前端试跑

```
1. 启动后端: cd backend && uvicorn main:app --reload
2. 启动前端: cd frontend && npm run dev
3. 浏览器打开牌桌页面
4. 观看 Agent 对战或加入牌局
5. 对局结束后查看回放
```

验证点:
- [x] 前后端通信正常 (REST + WebSocket)
- [x] 牌桌 UI 正确渲染
- [x] 实时更新无延迟
- [x] 回放播放器可用

---

## 5. Mock 策略

| 被 Mock 的组件 | Mock 方式 | 用途 |
|----------------|-----------|------|
| LLM API | 返回固定格式文本 | 单元/集成测试中避免真实 API 调用 |
| 数据库 | SQLite in-memory | 测试中使用内存数据库 |
| WebSocket | asyncio.Queue 模拟 | 测试人类玩家交互 |
| Deck.shuffle | 固定种子 | 测试中使用确定性发牌 |

**Mock LLM 示例**:
```python
class MockLLMProvider(BaseLLMProvider):
    def __init__(self, fixed_response: str = "ACTION: call"):
        self.fixed_response = fixed_response
        self.call_count = 0

    async def chat(self, messages: list[dict]) -> str:
        self.call_count += 1
        return f"让我思考一下...根据当前底池赔率，{self.fixed_response}"
```

**确定性发牌示例**:
```python
class SeededDeck(Deck):
    def __init__(self, seed: int):
        super().__init__()
        random.Random(seed).shuffle(self.cards)
```

---

## 6. 覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|-----------|------|
| engine/ | ≥95% | 核心逻辑，必须高覆盖 |
| agent/ | ≥85% | 含 LLM 调用需 mock |
| llm/ | ≥80% | 接口+工厂模式 |
| learning/ | ≥80% | RAG 部分可后期补充 |
| gto/ | ≥85% | 数学计算需精确 |
| api/ | ≥85% | 路由+错误处理 |
| services/ | ≥85% | 业务逻辑 |
| 总体 | ≥85% | - |

---

## 7. CI 测试执行

```bash
# 运行全部测试
pytest backend/tests/ -v --cov=backend --cov-report=html

# 仅运行引擎测试
pytest backend/tests/engine/ -v

# 仅运行集成测试
pytest backend/tests/integration/ -v

# 运行最小原型
python scripts/run_cli_game.py

# 前端测试
cd frontend && npm test
```

---

## 8. 测试数据

### 预定义测试场景

```python
# test_fixtures.py — 共享测试数据

SCENARIO_ROYAL_FLUSH = {
    "hole_cards": [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.SPADES)],
    "community": [
        Card(Rank.QUEEN, Suit.SPADES), Card(Rank.JACK, Suit.SPADES),
        Card(Rank.TEN, Suit.SPADES), Card(Rank.TWO, Suit.HEARTS),
        Card(Rank.THREE, Suit.DIAMONDS),
    ],
    "expected_rank": HandRank.ROYAL_FLUSH,
}

SCENARIO_SPLIT_POT = {
    "player1_hole": [Card(Rank.ACE, Suit.HEARTS), Card(Rank.KING, Suit.HEARTS)],
    "player2_hole": [Card(Rank.ACE, Suit.DIAMONDS), Card(Rank.KING, Suit.DIAMONDS)],
    "community": [...],  # 公共牌使双方牌型相同
    "expected": "split_pot",
}

SCENARIO_ALL_IN_SIDE_POT = {
    "players": [
        {"id": "p1", "chips": 100},
        {"id": "p2", "chips": 500},
        {"id": "p3", "chips": 300},
    ],
    "expected_pots": [
        {"amount": 300, "eligible": ["p1", "p2", "p3"]},
        {"amount": 400, "eligible": ["p2", "p3"]},
        {"amount": 200, "eligible": ["p2"]},
    ],
}
```

---

## 9. 回归测试检查清单

每次修改后应确认的关键场景:

- [ ] 2人单挑正常运行
- [ ] 6人满桌正常运行
- [ ] All-in + 边池正确
- [ ] 所有 10 种牌型正确识别
- [ ] 牌型比较（含 kicker）正确
- [ ] 盲注收取和庄家轮转正确
- [ ] Agent 决策管道正常（LLM mock）
- [ ] 手牌记录完整写入数据库
- [ ] 回放数据完整可读取
- [ ] API 端点 CRUD 正常
- [ ] WebSocket 连接和消息收发正常
- [ ] 手牌实验室：预设手牌正确分配
- [ ] 手牌实验室：预设牌不会重复出现
- [ ] 手牌实验室：从非 preflop 街开始正常
- [ ] 手牌实验室：多次运行结果正确记录
- [ ] 手牌实验室：结果可通过回放系统查看
- [ ] Agent 30s 超时自动 fold（或 check）
- [ ] LLM 调用失败自动重试 1 次后降级
- [ ] 每次 LLM 调用的 token 数和耗时正确记录
- [ ] Agent 决策状态(success/timeout/error)正确记录
- [ ] 监控 API 端点返回正确汇总数据
