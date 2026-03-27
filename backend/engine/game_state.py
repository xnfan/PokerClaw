"""Game state for a single hand of Texas Hold'em."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.engine.card import Card
from backend.engine.pot_manager import PotManager


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
    hole_cards: list[Card] = field(default_factory=list)
    is_active: bool = True
    is_all_in: bool = False
    current_bet: int = 0  # bet in current street
    total_bet: int = 0    # total bet this hand
    seat_index: int = 0

    def reset_street_bet(self) -> None:
        self.current_bet = 0


@dataclass
class GameState:
    """Complete state of a single hand."""
    hand_id: str
    players: list[PlayerState]
    community_cards: list[Card] = field(default_factory=list)
    street: Street = Street.PREFLOP
    pot_manager: PotManager = field(default_factory=PotManager)
    dealer_index: int = 0
    small_blind: int = 50
    big_blind: int = 100
    current_player_index: int = 0

    @property
    def active_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.is_active]

    @property
    def active_non_allin(self) -> list[PlayerState]:
        return [p for p in self.players if p.is_active and not p.is_all_in]

    def get_player(self, player_id: str) -> PlayerState:
        for p in self.players:
            if p.player_id == player_id:
                return p
        raise ValueError(f"Player {player_id} not found")

    def to_player_view(self, player_id: str) -> dict[str, Any]:
        """Return game state visible to a specific player (others' cards hidden)."""
        return {
            "hand_id": self.hand_id,
            "street": self.street.value,
            "community_cards": [str(c) for c in self.community_cards],
            "pot": self.pot_manager.total_pot,
            "players": [
                {
                    "player_id": p.player_id,
                    "display_name": p.display_name,
                    "chips": p.chips,
                    "is_active": p.is_active,
                    "is_all_in": p.is_all_in,
                    "current_bet": p.current_bet,
                    "total_bet": p.total_bet,
                    "seat_index": p.seat_index,
                    "hole_cards": (
                        [str(c) for c in p.hole_cards]
                        if p.player_id == player_id else []
                    ),
                }
                for p in self.players
            ],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
            "dealer_index": self.dealer_index,
        }

    def to_full_view(self) -> dict[str, Any]:
        """Return complete game state (god mode, for replay)."""
        view = self.to_player_view("")
        for i, p in enumerate(self.players):
            view["players"][i]["hole_cards"] = [str(c) for c in p.hole_cards]
        return view
