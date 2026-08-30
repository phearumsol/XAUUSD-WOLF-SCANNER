"""Strongly typed signal-engine outputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class Strength(StrEnum):
    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"


@dataclass(frozen=True)
class SignalResult:
    direction: Direction
    score: int
    confidence: float  # Internal model confidence, not win probability.
    strength: Strength
    timeframe: str
    timestamp: str
    entry_price: float
    m15_bias: str
    m5_bias: str
    bullish_score: int
    bearish_score: int
    directional_edge: int
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    components: Mapping[str, int]
    signal_changed: bool
