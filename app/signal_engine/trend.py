"""Multi-timeframe trend assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.config.settings import SignalSettings


@dataclass(frozen=True)
class TrendAssessment:
    bias: str
    bullish: float
    bearish: float
    reasons: tuple[str, ...]


def _value(row: Mapping[str, object], name: str) -> float:
    return float(row[name])


class TrendAnalyzer:
    def __init__(self, settings: SignalSettings) -> None:
        self.settings = settings

    def m15(self, row: Mapping[str, object]) -> TrendAssessment:
        bullish_checks = ("ema_9", "ema_21", "ema_50", "ema_200")
        e9, e21, e50, e200 = (_value(row, name) for name in bullish_checks)
        close, plus, minus, adx = (_value(row, name) for name in ("close", "plus_di_14", "minus_di_14", "adx_14"))
        bull = sum((e9 > e21, e21 > e50, e50 > e200, close > e50, plus > minus, adx >= self.settings.adx_established))
        bear = sum((e9 < e21, e21 < e50, e50 < e200, close < e50, minus > plus, adx >= self.settings.adx_established))
        bias = "BULLISH" if bull >= 4 and bull > bear else "BEARISH" if bear >= 4 and bear > bull else "NEUTRAL"
        reasons = (("M15 bullish trend",) if bias == "BULLISH" else ("M15 bearish trend",) if bias == "BEARISH" else ())
        return TrendAssessment(bias, bull / 6, bear / 6, reasons)

    def m5(self, row: Mapping[str, object]) -> TrendAssessment:
        e9, e21, e50, close = (_value(row, name) for name in ("ema_9", "ema_21", "ema_50", "close"))
        bull = sum((e9 > e21, e21 > e50, close > e21))
        bear = sum((e9 < e21, e21 < e50, close < e21))
        bias = "BULLISH" if bull >= 2 and bull > bear else "BEARISH" if bear >= 2 and bear > bull else "NEUTRAL"
        reasons = (("M5 EMA alignment bullish",) if bias == "BULLISH" else ("M5 EMA alignment bearish",) if bias == "BEARISH" else ())
        return TrendAssessment(bias, bull / 3, bear / 3, reasons)
