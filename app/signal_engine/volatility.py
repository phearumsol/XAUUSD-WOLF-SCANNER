"""ATR and Bollinger context assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import SignalSettings


@dataclass(frozen=True)
class VolatilityAssessment:
    score: float
    classification: str
    warnings: tuple[str, ...]


class VolatilityAnalyzer:
    def __init__(self, settings: SignalSettings) -> None:
        self.settings = settings

    def assess(self, row: Mapping[str, object]) -> VolatilityAssessment:
        atr = float(row["atr_percent"])
        if atr < self.settings.atr_low_percent: return VolatilityAssessment(0.5, "LOW", ())
        if atr <= self.settings.atr_normal_percent: return VolatilityAssessment(1.0, "NORMAL", ())
        if atr <= self.settings.atr_high_percent: return VolatilityAssessment(0.7, "HIGH", ("VOLATILITY_RISK",))
        return VolatilityAssessment(0.0, "EXTREME", ("EXTREME_VOLATILITY",))
