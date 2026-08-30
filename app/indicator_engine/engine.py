"""Validation, orchestration, and snapshots for raw indicator calculations."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.config.settings import IndicatorSettings
from app.indicator_engine.candles import add_candle_analysis
from app.indicator_engine.momentum import add_macd, add_rsi, add_stochastic
from app.indicator_engine.structure import add_structure
from app.indicator_engine.trend import add_adx, add_ema
from app.indicator_engine.volatility import add_atr, add_bollinger_bands


LOGGER = logging.getLogger(__name__)
REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "tick_volume")


class IndicatorValidationError(ValueError):
    """Raised when OHLCV input cannot be safely calculated."""


class IndicatorEngine:
    """Calculate raw, timeframe-agnostic technical indicators from OHLCV data."""

    def __init__(self, settings: IndicatorSettings) -> None:
        self._settings = settings

    def calculate_all(self, data: pd.DataFrame, timeframe: str | None = None) -> pd.DataFrame:
        """Return a chronologically normalized copy enriched with all indicators."""
        frame = self._prepare_data(data)
        LOGGER.info("[INDICATOR] Calculating %s indicators...", timeframe or "market")
        frame = add_ema(frame, self._settings.ema_periods)
        frame = add_adx(frame, self._settings.adx_period)
        frame = add_rsi(frame, self._settings.rsi_period)
        frame = add_macd(frame, self._settings.macd_fast_period, self._settings.macd_slow_period, self._settings.macd_signal_period)
        frame = add_stochastic(frame, self._settings.stochastic_k_period, self._settings.stochastic_k_smoothing, self._settings.stochastic_d_period)
        frame = add_atr(frame, self._settings.atr_period)
        frame = add_bollinger_bands(frame, self._settings.bollinger_period, self._settings.bollinger_std)
        frame = add_structure(frame, self._settings.swing_lookback, self._settings.recent_extreme_period)
        frame = add_candle_analysis(frame)
        LOGGER.info("[INDICATOR] %s indicators completed.", timeframe or "Market")
        return frame

    def latest_completed_snapshot(self, data: pd.DataFrame) -> dict[str, Any]:
        """Return indicator values from the final completed, never active, candle."""
        if len(data) < 2:
            raise IndicatorValidationError("At least two candles are required for a completed-candle snapshot.")
        snapshot = data.iloc[-2].to_dict()
        timestamp = snapshot.get("time")
        if isinstance(timestamp, pd.Timestamp):
            snapshot["time"] = timestamp.to_pydatetime().isoformat()
        return snapshot

    @staticmethod
    def is_trend_bullish(snapshot: dict[str, Any]) -> bool:
        """Return whether raw EMA ordering is bullish; this is not a signal."""
        return all(pd.notna(snapshot.get(key)) for key in ("ema_9", "ema_21", "ema_50")) and snapshot["ema_9"] > snapshot["ema_21"] > snapshot["ema_50"]

    @staticmethod
    def is_trend_bearish(snapshot: dict[str, Any]) -> bool:
        """Return whether raw EMA ordering is bearish; this is not a signal."""
        return all(pd.notna(snapshot.get(key)) for key in ("ema_9", "ema_21", "ema_50")) and snapshot["ema_9"] < snapshot["ema_21"] < snapshot["ema_50"]

    @staticmethod
    def is_overbought(snapshot: dict[str, Any]) -> bool:
        """Return whether RSI is at or above 70; this is not a signal."""
        return bool(pd.notna(snapshot.get("rsi_14")) and snapshot["rsi_14"] >= 70)

    @staticmethod
    def is_oversold(snapshot: dict[str, Any]) -> bool:
        """Return whether RSI is at or below 30; this is not a signal."""
        return bool(pd.notna(snapshot.get("rsi_14")) and snapshot["rsi_14"] <= 30)

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(data, pd.DataFrame):
            raise IndicatorValidationError("Indicator input must be a pandas DataFrame.")
        missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
        if missing:
            raise IndicatorValidationError(f"Indicator input is missing required columns: {', '.join(missing)}.")
        frame = data.copy()
        frame["time"] = pd.to_datetime(frame["time"], errors="coerce", utc=True)
        if frame["time"].isna().any():
            raise IndicatorValidationError("Indicator input contains invalid timestamps.")
        numeric_columns = [column for column in REQUIRED_COLUMNS if column != "time"]
        converted = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
        invalid = converted.isna() & frame[numeric_columns].notna()
        if invalid.any().any():
            raise IndicatorValidationError("Indicator input contains non-numeric OHLCV values.")
        frame[numeric_columns] = converted
        if (frame["high"] < frame[["open", "close"]].max(axis=1)).any() or (frame["low"] > frame[["open", "close"]].min(axis=1)).any() or (frame["high"] < frame["low"]).any():
            raise IndicatorValidationError("Indicator input contains impossible OHLC values.")
        if frame["time"].duplicated().any():
            LOGGER.warning("[INDICATOR] Duplicate timestamps found; keeping the final received candle.")
            frame = frame.drop_duplicates(subset="time", keep="last")
        if not frame["time"].is_monotonic_increasing:
            LOGGER.warning("[INDICATOR] Input timestamps were unsorted; sorting chronologically.")
            frame = frame.sort_values("time")
        return frame.reset_index(drop=True)