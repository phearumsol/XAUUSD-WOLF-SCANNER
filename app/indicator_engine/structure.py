"""Causal price-structure calculations based on confirmed historical pivots."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_structure(data: pd.DataFrame, swing_lookback: int, recent_extreme_period: int) -> pd.DataFrame:
    """Add confirmed swings and market structure without future-candle access.

    At each candle, the potential pivot from ``swing_lookback`` candles ago is
    confirmed against candles seen since then. The pivot's price is recorded on
    the confirmation candle, never retroactively on the earlier pivot candle.
    """
    window = swing_lookback * 2 + 1
    rolling_high = data["high"].rolling(window, min_periods=window).max()
    rolling_low = data["low"].rolling(window, min_periods=window).min()
    pivot_high = data["high"].shift(swing_lookback)
    pivot_low = data["low"].shift(swing_lookback)
    data["swing_high"] = pivot_high.where(pivot_high.eq(rolling_high))
    data["swing_low"] = pivot_low.where(pivot_low.eq(rolling_low))
    data["recent_high"] = data["high"].rolling(recent_extreme_period, min_periods=1).max()
    data["recent_low"] = data["low"].rolling(recent_extreme_period, min_periods=1).min()

    previous_high = data["swing_high"].ffill().shift()
    previous_low = data["swing_low"].ffill().shift()
    data["higher_high"] = (data["swing_high"].notna() & data["swing_high"].gt(previous_high)).fillna(False)
    data["lower_high"] = (data["swing_high"].notna() & data["swing_high"].lt(previous_high)).fillna(False)
    data["higher_low"] = (data["swing_low"].notna() & data["swing_low"].gt(previous_low)).fillna(False)
    data["lower_low"] = (data["swing_low"].notna() & data["swing_low"].lt(previous_low)).fillna(False)

    high_relation = pd.Series(np.nan, index=data.index)
    high_relation.loc[data["higher_high"]] = 1.0
    high_relation.loc[data["lower_high"]] = -1.0
    low_relation = pd.Series(np.nan, index=data.index)
    low_relation.loc[data["higher_low"]] = 1.0
    low_relation.loc[data["lower_low"]] = -1.0
    high_relation = high_relation.ffill()
    low_relation = low_relation.ffill()
    data["market_structure"] = np.select(
        [(high_relation.eq(1) & low_relation.eq(1)), (high_relation.eq(-1) & low_relation.eq(-1)), (high_relation.notna() & low_relation.notna())],
        ["BULLISH", "BEARISH", "RANGE"],
        default="UNKNOWN",
    )
    return data