"""Personality profiles and prompt templates for LLM agents."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SkillLevel(Enum):
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class PlayStyle(Enum):
    TAG = "tag"                     # Tight-Aggressive
    LAG = "lag"                     # Loose-Aggressive
    CALLING_STATION = "calling_station"
    ROCK = "rock"                   # Tight-Passive
    FISH = "fish"                   # Loose-Passive / Random
    MANIAC = "maniac"               # Ultra Loose-Aggressive


_SKILL_PROMPTS = {
    SkillLevel.NOVICE: (
        "你是一个德州扑克新手，经验不足。"
        "你对底池赔率、位置优势等概念理解有限，偶尔会犯明显的错误。"
    ),
    SkillLevel.INTERMEDIATE: (
        "你是一个有一定经验的德州扑克玩家。"
        "你理解基本的底池赔率和位置概念，但在复杂场景中判断力有限。"
    ),
    SkillLevel.EXPERT: (
        "你是一个经验丰富的德州扑克高手。"
        "你精通底池赔率、隐含赔率、位置优势、对手读牌和范围分析。"
    ),
}

_STYLE_PROMPTS = {
    PlayStyle.TAG: (
        "你的打法风格为紧凶(TAG)。"
        "你只在起手牌优质时参与手牌，翻前范围紧；"
        "一旦参与，你倾向于主动加注而非跟注；"
        "你会选择性诈唬，但频率适中。"
    ),
    PlayStyle.LAG: (
        "你的打法风格为松凶(LAG)。"
        "你参与较多手牌，翻前范围宽；"
        "你在有利位置时频繁加注施压；"
        "你善于利用位置优势和对手的弱点进行诈唬。"
    ),
    PlayStyle.CALLING_STATION: (
        "你的打法风格为跟注站(Calling Station)。"
        "你喜欢跟注，很少主动加注；"
        "你很难弃掉任何有一点可能的牌；"
        "你几乎不诈唬。"
    ),
    PlayStyle.ROCK: (
        "你的打法风格为紧弱(Rock)。"
        "你只玩最顶级的起手牌；"
        "即使拿到好牌你也倾向于跟注而非加注；"
        "面对大的下注你容易弃牌。"
    ),
    PlayStyle.FISH: (
        "你是一条鱼(Fish)，打牌不讲道理。"
        "你玩太多手牌，经常跟注过大的下注；"
        "你偶尔会用弱牌过度下注；"
        "你的决策缺乏逻辑性。"
    ),
    PlayStyle.MANIAC: (
        "你的打法风格为疯子(Maniac)。"
        "你几乎每手牌都参与，并且总是加注；"
        "你非常激进，频繁诈唬和过度下注；"
        "你享受给对手制造压力。"
    ),
}


@dataclass
class PersonalityProfile:
    skill_level: SkillLevel
    play_style: PlayStyle
    custom_traits: str = ""

    def build_system_prompt(self) -> str:
        """Generate the system prompt reflecting this personality."""
        parts = [
            _SKILL_PROMPTS[self.skill_level],
            _STYLE_PROMPTS[self.play_style],
        ]
        if self.custom_traits:
            parts.append(f"额外特征: {self.custom_traits}")
        parts.append(
            "\n请根据以上性格特征进行决策。"
            "先给出你的思考过程（2-4句），再给出最终决策。"
            "\n输出格式:\nTHINKING: <你的思考>\nACTION: fold|check|call|raise|all_in"
            "\nAMOUNT: <加注金额，仅 raise 时需要>"
        )
        return "\n".join(parts)

    def build_messages(self, context_text: str) -> list[dict]:
        """Build full LLM message list: system + user context."""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": context_text},
        ]
