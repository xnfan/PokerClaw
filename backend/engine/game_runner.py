"""Execute a single hand of Texas Hold'em."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from backend.engine.betting_round import (
    BettingAction,
    BettingRound,
    PlayerAction,
    PlayerSeat,
)
from backend.engine.card import Card
from backend.engine.deck import Deck
from backend.engine.game_state import GameState, PlayerState, Street
from backend.engine.hand_evaluator import HandEvaluator, HandScore
from backend.engine.pot_manager import PotManager

# Callback type for real-time action events
ActionCallback = Callable[[dict[str, Any]], Awaitable[None]]

if TYPE_CHECKING:
    from backend.agent.base_agent import BaseAgent


@dataclass
class ActionRecord:
    """Record of a single action taken during the hand."""
    player_id: str
    street: str
    action: str
    amount: int  # total amount put in this action
    round_bet: int  # total amount player invested this round
    pot_after: int
    thinking: str = ""
    is_timeout: bool = False
    is_fallback: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    llm_latency_ms: float = 0.0
    decision_ms: float = 0.0


@dataclass
class HandResult:
    hand_id: str
    winners: dict[str, int]  # player_id -> winnings
    player_hands: dict[str, HandScore]  # player_id -> hand score
    player_cards: dict[str, list[Card]]  # player_id -> hole cards
    community_cards: list[Card]
    action_history: list[ActionRecord]
    final_chips: dict[str, int]  # player_id -> chips after hand


class GameRunner:
    """Execute a full hand: blinds -> deal -> streets -> showdown."""

    def __init__(
        self,
        players: list[PlayerState],
        agents: dict[str, "BaseAgent"],
        small_blind: int = 50,
        big_blind: int = 100,
        dealer_index: int = 0,
        deck_seed: int | None = None,
    ) -> None:
        self.hand_id = str(uuid.uuid4())[:8]
        self.agents = agents
        self.deck = Deck(seed=deck_seed)
        self.deck.shuffle()
        self.state = GameState(
            hand_id=self.hand_id,
            players=players,
            pot_manager=PotManager(),
            small_blind=small_blind,
            big_blind=big_blind,
            dealer_index=dealer_index,
        )
        # Map player_id to display_name for readable action history
        self._player_names: dict[str, str] = {p.player_id: p.display_name for p in players}
        self.on_action: ActionCallback | None = None
        self.action_history: list[ActionRecord] = []

    async def run_hand(self) -> HandResult:
        """Run a complete hand and return result."""
        self._post_blinds()
        self._deal_hole_cards()

        streets = [Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER]
        for street in streets:
            if len(self.state.active_players) <= 1:
                break
            self.state.street = street
            if street != Street.PREFLOP:
                await self._deal_community(street)
                for p in self.state.players:
                    p.reset_street_bet()
            if len(self.state.active_non_allin) > 0:
                await self._run_betting_round(street)

        return self._resolve()

    def _post_blinds(self) -> None:
        """Post small and big blinds."""
        n = len(self.state.players)
        sb_idx = (self.state.dealer_index + 1) % n
        bb_idx = (self.state.dealer_index + 2) % n
        # Heads-up: dealer posts SB
        if n == 2:
            sb_idx = self.state.dealer_index
            bb_idx = (self.state.dealer_index + 1) % n

        sb_player = self.state.players[sb_idx]
        bb_player = self.state.players[bb_idx]
        sb_amount = min(self.state.small_blind, sb_player.chips)
        bb_amount = min(self.state.big_blind, bb_player.chips)

        self._deduct_bet(sb_player, sb_amount)
        self._deduct_bet(bb_player, bb_amount)

    def _deduct_bet(self, player: PlayerState, amount: int) -> None:
        player.chips -= amount
        player.current_bet += amount
        player.total_bet += amount
        self.state.pot_manager.add_bet(player.player_id, amount)
        if player.chips == 0:
            player.is_all_in = True
            self.state.pot_manager.mark_all_in(player.player_id)

    def _deal_hole_cards(self) -> None:
        for player in self.state.players:
            player.hole_cards = self.deck.deal(2)

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

    async def _run_betting_round(self, street: Street) -> None:
        """Run a full betting round for one street."""
        seats = self._build_seats()
        n = len(self.state.players)
        # Determine first to act
        if street == Street.PREFLOP:
            first = (self.state.dealer_index + 3) % n
            if n == 2:
                first = self.state.dealer_index  # heads-up: SB acts first preflop
        else:
            first = (self.state.dealer_index + 1) % n

        # Reorder seats starting from first to act
        ordered_seats = seats[first:] + seats[:first]
        betting = BettingRound(
            seats=ordered_seats,
            pot_manager=self.state.pot_manager,
            current_bet=max(s.current_bet for s in seats),
            min_raise=self.state.big_blind,
        )

        while not betting.is_complete():
            next_pid = betting.get_next_player_id()
            if next_pid is None:
                break
            valid_actions = betting.get_valid_actions(next_pid)
            if not valid_actions:
                break
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
            player_view = self.state.to_player_view(next_pid)
            agent = self.agents[next_pid]
            action, metadata = await agent.decide(player_view, valid_actions)
            # Ensure action is valid
            if action.action not in valid_actions:
                action = PlayerAction(next_pid, BettingAction.FOLD)
            # Get round_bet before applying action
            seat_before = next((s for s in ordered_seats if s.player_id == next_pid), None)
            round_bet_before = seat_before.current_bet if seat_before else 0
            betting.apply_action(action)
            self._sync_seats_back(ordered_seats)
            # Get round_bet after action
            round_bet_after = next((s.current_bet for s in ordered_seats if s.player_id == next_pid), 0)
            round_invested = round_bet_after  # total invested this round for this player
            # Record action (use display_name for readability)
            display_name = self._player_names.get(next_pid, next_pid)
            record = ActionRecord(
                player_id=display_name,
                street=street.value,
                action=action.action.value,
                amount=action.amount,
                round_bet=round_invested,
                pot_after=self.state.pot_manager.total_pot,
                thinking=metadata.get("thinking", ""),
                is_timeout=metadata.get("is_timeout", False),
                is_fallback=metadata.get("is_fallback", False),
                input_tokens=metadata.get("input_tokens", 0),
                output_tokens=metadata.get("output_tokens", 0),
                llm_latency_ms=metadata.get("llm_latency_ms", 0.0),
                decision_ms=metadata.get("decision_ms", 0.0),
            )
            self.action_history.append(record)
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

    def _build_seats(self) -> list[PlayerSeat]:
        return [
            PlayerSeat(
                player_id=p.player_id,
                chips=p.chips,
                is_active=p.is_active,
                is_all_in=p.is_all_in,
                current_bet=p.current_bet,
            )
            for p in self.state.players
        ]

    def _sync_seats_back(self, seats: list[PlayerSeat]) -> None:
        """Sync betting round seat state back to game state players."""
        seat_map = {s.player_id: s for s in seats}
        for p in self.state.players:
            if p.player_id in seat_map:
                s = seat_map[p.player_id]
                p.chips = s.chips
                p.is_active = s.is_active
                p.is_all_in = s.is_all_in
                p.current_bet = s.current_bet

    def _resolve(self) -> HandResult:
        """Resolve the hand: determine winners and distribute pot."""
        active = self.state.active_players
        active_ids = {p.player_id for p in active}
        hand_scores: dict[str, HandScore] = {}
        player_cards: dict[str, list[Card]] = {}

        for p in active:
            if p.hole_cards and len(self.state.community_cards) >= 3:
                score = HandEvaluator.evaluate(
                    p.hole_cards, self.state.community_cards
                )
                hand_scores[p.player_id] = score
            player_cards[p.player_id] = list(p.hole_cards)

        # Single winner (everyone else folded)
        if len(active) == 1:
            winner = active[0]
            total = self.state.pot_manager.total_pot
            winner.chips += total
            winners = {winner.player_id: total}
        else:
            winners = self.state.pot_manager.distribute_winnings(
                hand_scores, active_ids
            )
            for pid, amount in winners.items():
                self.state.get_player(pid).chips += amount

        return HandResult(
            hand_id=self.hand_id,
            winners=winners,
            player_hands=hand_scores,
            player_cards=player_cards,
            community_cards=list(self.state.community_cards),
            action_history=self.action_history,
            final_chips={p.player_id: p.chips for p in self.state.players},
        )
