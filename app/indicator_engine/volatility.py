"""Volatility indicator calculations."""

from __future__ import annotations

import pandas as pd


def add_atr(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """Add Wilder-smoothed average true range and percentage ATR."""
    true_range = pd.concat([
        data["high"] - data["low"],
        (data["high"] - data["close"].shift()).abs(),
        (data["low"] - data["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    data[f"atr_{period}"] = atr
    data["atr_percent"] = 100 * atr / data["close"]
    return data


def add_bollinger_bands(data: pd.DataFrame, period: int, standard_deviations: float) -> pd.DataFrame:
    """Add standard rolling Bollinger Bands and normalized band measures."""
    middle = data["close"].rolling(period, min_periods=period).mean()
    deviation = data["close"].rolling(period, min_periods=period).std(ddof=0)
    upper = middle + standard_deviations * deviation
    lower = middle - standard_deviations * deviation
    width = upper - lower
    data["bb_middle"] = middle
    data["bb_upper"] = upper
    data["bb_lower"] = lower
    data["bb_width"] = width
    data["bb_percent"] = ((data["close"] - lower) / width).where(width.ne(0))
    return data