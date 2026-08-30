"""RSI, MACD, and stochastic confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import SignalSettings


@dataclass(frozen=True)
class MomentumAssessment:
    bullish: float
    bearish: float
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


class MomentumAnalyzer:
    def __init__(self, settings: SignalSettings) -> None:
        self.settings = settings

    def assess(self, row: Mapping[str, object], previous: Mapping[str, object]) -> MomentumAssessment:
        v = lambda name: float(row[name])
        p = lambda name: float(previous[name])
        rsi, macd, signal, hist, stoch_k, stoch_d = (v(name) for name in ("rsi_14", "macd", "macd_signal", "macd_histogram", "stoch_k", "stoch_d"))
        bull = sum((rsi > self.settings.rsi_bullish_min, rsi > p("rsi_14"), macd > signal, hist > 0, hist > p("macd_histogram"), stoch_k > stoch_d))
        bear = sum((rsi < self.settings.rsi_bearish_max, rsi < p("rsi_14"), macd < signal, hist < 0, hist < p("macd_histogram"), stoch_k < stoch_d))
        reasons = []
        if macd > signal and hist > 0: reasons.append("MACD bullish")
        if macd < signal and hist < 0: reasons.append("MACD bearish")
        if self.settings.rsi_bullish_min < rsi <= self.settings.rsi_bullish_max: reasons.append("RSI supports bullish momentum")
        if self.settings.rsi_bearish_min <= rsi < self.settings.rsi_bearish_max: reasons.append("RSI supports bearish momentum")
        warnings = ["RSI_OVERBOUGHT" if rsi >= self.settings.rsi_overbought else "RSI_OVERSOLD" if rsi <= self.settings.rsi_oversold else ""]
        return MomentumAssessment(bull / 6, bear / 6, tuple(reasons), tuple(item for item in warnings if item))
