"""Single-candle measurements and causal two-candle pattern detection."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_candle_analysis(data: pd.DataFrame) -> pd.DataFrame:
    """Add body, wick, direction, and common candlestick pattern columns."""
    body = (data["close"] - data["open"]).abs()
    candle_range = data["high"] - data["low"]
    upper_wick = data["high"] - data[["open", "close"]].max(axis=1)
    lower_wick = data[["open", "close"]].min(axis=1) - data["low"]
    non_zero_range = candle_range.where(candle_range.ne(0))
    data["candle_body"] = body
    data["candle_range"] = candle_range
    data["upper_wick"] = upper_wick
    data["lower_wick"] = lower_wick
    data["body_percent"] = 100 * body / non_zero_range
    data["upper_wick_percent"] = 100 * upper_wick / non_zero_range
    data["lower_wick_percent"] = 100 * lower_wick / non_zero_range
    data["candle_direction"] = np.select([data["close"] > data["open"], data["close"] < data["open"]], ["BULLISH", "BEARISH"], default="DOJI")

    previous_open = data["open"].shift()
    previous_close = data["close"].shift()
    previous_bearish = previous_close < previous_open
    previous_bullish = previous_close > previous_open
    data["bullish_engulfing"] = (previous_bearish & (data["close"] > data["open"]) & (data["open"] <= previous_close) & (data["close"] >= previous_open)).fillna(False)
    data["bearish_engulfing"] = (previous_bullish & (data["close"] < data["open"]) & (data["open"] >= previous_close) & (data["close"] <= previous_open)).fillna(False)
    small_body = body <= candle_range * 0.3
    data["hammer"] = (small_body & (lower_wick >= body * 2) & (upper_wick <= body)).fillna(False)
    data["shooting_star"] = (small_body & (upper_wick >= body * 2) & (lower_wick <= body)).fillna(False)
    data["doji"] = (body <= candle_range * 0.1).fillna(False)
    return data