"""Completed-candle, explainable signal orchestration; never sends orders."""

from __future__ import annotations

from collections import deque
import logging
from typing import Iterable

import pandas as pd

from app.config.settings import SignalSettings
from app.signal_engine.models import Direction, SignalResult, Strength
from app.signal_engine.momentum import MomentumAnalyzer
from app.signal_engine.scoring import breakdown
from app.signal_engine.structure import StructureAnalyzer
from app.signal_engine.trend import TrendAnalyzer
from app.signal_engine.volatility import VolatilityAnalyzer

LOGGER = logging.getLogger(__name__)
REQUIRED = {"time", "open", "high", "low", "close", "ema_9", "ema_21", "ema_50", "ema_200", "adx_14", "plus_di_14", "minus_di_14", "rsi_14", "macd", "macd_signal", "macd_histogram", "stoch_k", "stoch_d", "atr_14", "atr_percent", "bb_upper", "bb_lower", "recent_high", "recent_low", "market_structure", "candle_direction", "body_percent", "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"}


class SignalValidationError(ValueError): pass


class SignalEngine:
    def __init__(self, settings: SignalSettings) -> None:
        self.settings = settings
        self.trend = TrendAnalyzer(settings); self.momentum = MomentumAnalyzer(settings); self.structure = StructureAnalyzer(settings); self.volatility = VolatilityAnalyzer(settings)
        self._history: deque[SignalResult] = deque(maxlen=settings.history_size)

    def generate_signal(self, m5_indicators: pd.DataFrame, m15_indicators: pd.DataFrame) -> SignalResult:
        self._validate(m5_indicators, "M5"); self._validate(m15_indicators, "M15")
        current, previous, macro_row = m5_indicators.iloc[-2], m5_indicators.iloc[-3], m15_indicators.iloc[-2]
        m15, m5 = self.trend.m15(macro_row), self.trend.m5(current)
        momentum, structure, volatility = self.momentum.assess(current, previous), self.structure.assess(current), self.volatility.assess(current)
        candle_bull, candle_bear, candle_reason = self._candle(current)
        bull = breakdown(self.settings.weights, m15.bullish, m5.bullish, momentum.bullish, structure.bullish, volatility.score, candle_bull, structure.sr_bullish)
        bear = breakdown(self.settings.weights, m15.bearish, m5.bearish, momentum.bearish, structure.bearish, volatility.score, candle_bear, structure.sr_bearish)
        bullish_score, bearish_score = sum(bull.values()), sum(bear.values())
        edge = bullish_score - bearish_score
        warnings = list(dict.fromkeys((*momentum.warnings, *structure.warnings, *volatility.warnings)))
        if m15.bias != "NEUTRAL" and m5.bias != "NEUTRAL" and m15.bias != m5.bias: warnings.append("MTF_CONFLICT")
        if (m15.bias == "BULLISH" and structure.bearish == 1) or (m15.bias == "BEARISH" and structure.bullish == 1): warnings.append("STRUCTURE_CONFLICT")
        direction = self._direction(bullish_score, bearish_score, edge, m15.bias, volatility.classification, warnings)
        score = bullish_score if direction is Direction.BUY else bearish_score if direction is Direction.SELL else max(bullish_score, bearish_score)
        major = {"EXTREME_VOLATILITY", "MTF_CONFLICT", "STRUCTURE_CONFLICT"}
        strength = self._strength(score, abs(edge), m15.bias == m5.bias and m15.bias != "NEUTRAL", not major.intersection(warnings)) if direction is not Direction.WAIT else Strength.NONE
        confidence = round(max(0, min(100, score - len(warnings) * 5 + min(abs(edge), 30) / 3)) / 100, 2)
        reasons = list(m15.reasons + m5.reasons + momentum.reasons + structure.reasons)
        if candle_reason: reasons.append(candle_reason)
        reasons.append(f"{volatility.classification.title()} volatility")
        result = SignalResult(direction, score, confidence, strength, "M5", pd.Timestamp(current["time"]).isoformat(), float(current["close"]), m15.bias, m5.bias, bullish_score, bearish_score, edge, tuple(dict.fromkeys(reasons)), tuple(warnings), bull if direction is not Direction.SELL else bear, not self._history or self._history[-1].direction != direction)
        self._history.append(result)
        LOGGER.info("[SIGNAL] M15 Bias: %s | M5 Bias: %s | Bullish: %s | Bearish: %s | Edge: %+d | Final: %s | Strength: %s", m15.bias, m5.bias, bullish_score, bearish_score, edge, direction, strength)
        return result

    def get_latest_signal(self) -> SignalResult | None: return self._history[-1] if self._history else None
    def history(self) -> tuple[SignalResult, ...]: return tuple(self._history)

    def _validate(self, frame: pd.DataFrame, name: str) -> None:
        missing = REQUIRED - set(frame.columns)
        if missing: raise SignalValidationError(f"{name} indicator data is missing required columns: {', '.join(sorted(missing))}.")
        if len(frame) < 3: raise SignalValidationError(f"{name} indicator data requires at least three candles to evaluate a completed candle.")
        needed = frame.iloc[[-3, -2]][list(REQUIRED - {"time", "market_structure", "candle_direction", "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"})]
        if needed.isna().any().any(): raise SignalValidationError(f"{name} completed-candle indicator values are not ready (warm-up or missing data).")

    def _direction(self, bull: int, bear: int, edge: int, m15: str, volatility: str, warnings: Iterable[str]) -> Direction:
        if volatility == "EXTREME": return Direction.WAIT
        if bull >= self.settings.buy_threshold and edge >= self.settings.minimum_directional_edge and m15 != "BEARISH" and "MTF_CONFLICT" not in warnings: return Direction.BUY
        if bear >= self.settings.sell_threshold and -edge >= self.settings.minimum_directional_edge and m15 != "BULLISH" and "MTF_CONFLICT" not in warnings: return Direction.SELL
        return Direction.WAIT

    def _strength(self, score: int, edge: int, aligned: bool, no_major_warning: bool) -> Strength:
        if score >= self.settings.very_strong_score and edge >= self.settings.very_strong_edge and aligned and no_major_warning: return Strength.VERY_STRONG
        if score >= 70: return Strength.STRONG
        if score >= 60: return Strength.MODERATE
        return Strength.WEAK

    @staticmethod
    def _candle(row: pd.Series) -> tuple[float, float, str]:
        strong = float(row["body_percent"]) >= 50
        if (str(row["candle_direction"]) == "BULLISH" and strong) or bool(row["bullish_engulfing"]) or bool(row["hammer"]): return 1.0, 0.0, "Bullish candle confirmation"
        if (str(row["candle_direction"]) == "BEARISH" and strong) or bool(row["bearish_engulfing"]) or bool(row["shooting_star"]): return 0.0, 1.0, "Bearish candle confirmation"
        return 0.2, 0.2, "Weak or indecisive candle"
