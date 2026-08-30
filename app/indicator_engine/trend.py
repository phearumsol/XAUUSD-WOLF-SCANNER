"""Trend indicator calculations."""

from __future__ import annotations

import pandas as pd


def add_ema(data: pd.DataFrame, periods: list[int]) -> pd.DataFrame:
    """Add causal exponential moving averages with normal warm-up NaNs."""
    for period in periods:
        data[f"ema_{period}"] = data["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    return data


def add_adx(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """Add Wilder-smoothed ADX and directional index columns."""
    high, low, close = data["high"], data["low"], data["close"]
    upward_move = high.diff()
    downward_move = -low.diff()
    plus_dm = upward_move.where((upward_move > downward_move) & (upward_move > 0), 0.0)
    minus_dm = downward_move.where((downward_move > upward_move) & (downward_move > 0), 0.0)
    true_range = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / atr
    directional_sum = plus_di + minus_di
    dx = (100 * (plus_di - minus_di).abs() / directional_sum).where(directional_sum.ne(0))
    data[f"plus_di_{period}"] = plus_di
    data[f"minus_di_{period}"] = minus_di
    data[f"adx_{period}"] = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return data