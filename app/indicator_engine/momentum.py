"""Momentum indicator calculations."""

from __future__ import annotations

import pandas as pd


def add_rsi(data: pd.DataFrame, period: int) -> pd.DataFrame:
    """Add a Wilder-smoothed relative strength index."""
    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    average_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    relative_strength = average_gain / average_loss
    data[f"rsi_{period}"] = (100 - (100 / (1 + relative_strength))).where(average_loss.ne(0), 100.0)
    return data


def add_macd(data: pd.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> pd.DataFrame:
    """Add standard MACD, signal, and histogram columns."""
    fast = data["close"].ewm(span=fast_period, adjust=False, min_periods=fast_period).mean()
    slow = data["close"].ewm(span=slow_period, adjust=False, min_periods=slow_period).mean()
    macd = fast - slow
    signal = macd.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    data["macd"] = macd
    data["macd_signal"] = signal
    data["macd_histogram"] = macd - signal
    return data


def add_stochastic(data: pd.DataFrame, k_period: int, k_smoothing: int, d_period: int) -> pd.DataFrame:
    """Add smoothed stochastic %K and %D columns."""
    lowest_low = data["low"].rolling(k_period, min_periods=k_period).min()
    highest_high = data["high"].rolling(k_period, min_periods=k_period).max()
    denominator = highest_high - lowest_low
    raw_k = (100 * (data["close"] - lowest_low) / denominator).where(denominator.ne(0))
    k = raw_k.rolling(k_smoothing, min_periods=k_smoothing).mean()
    data["stoch_k"] = k
    data["stoch_d"] = k.rolling(d_period, min_periods=d_period).mean()
    return data