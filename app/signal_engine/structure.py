"""Market-structure and nearby-level assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import SignalSettings


@dataclass(frozen=True)
class StructureAssessment:
    bullish: float
    bearish: float
    sr_bullish: float
    sr_bearish: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


class StructureAnalyzer:
    def __init__(self, settings: SignalSettings) -> None:
        self.settings = settings

    def assess(self, row: Mapping[str, object]) -> StructureAssessment:
        structure = str(row["market_structure"])
        close, recent_high, recent_low, atr, candle_high, candle_low = (float(row[name]) for name in ("close", "recent_high", "recent_low", "atr_14", "high", "low"))
        # A rolling extreme equal to this candle's high/low is not a prior structural level.
        near_resistance = recent_high > candle_high and (recent_high - close) / atr <= self.settings.sr_proximity_atr
        near_support = recent_low < candle_low and (close - recent_low) / atr <= self.settings.sr_proximity_atr
        bull, bear = (1.0, 0.0) if structure == "BULLISH" else (0.0, 1.0) if structure == "BEARISH" else (0.4, 0.4)
        reasons = ["Bullish market structure" if structure == "BULLISH" else "Bearish market structure" if structure == "BEARISH" else "Market structure unavailable"]
        warnings = ["RESISTANCE_RISK" if near_resistance else "", "SUPPORT_RISK" if near_support else ""]
        return StructureAssessment(bull, bear, 0.0 if near_resistance else 1.0, 0.0 if near_support else 1.0, tuple(reasons), tuple(item for item in warnings if item))
