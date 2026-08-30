from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config.settings import load_settings
from app.indicator_engine import IndicatorEngine
from app.signal_engine import Direction, SignalEngine, SignalValidationError


def market(rows: int = 260, bearish: bool = False, volatility: float = 1.0) -> pd.DataFrame:
    slope = -0.7 if bearish else 0.7
    close = 3000 + np.arange(rows) * slope + np.sin(np.arange(rows) / 3) * volatility
    return pd.DataFrame({"time": pd.date_range("2026-01-01", periods=rows, freq="5min", tz="UTC"), "open": close - slope * .3, "high": close + volatility, "low": close - volatility, "close": close, "tick_volume": 100})


def indicators(bearish: bool = False, volatility: float = 1.0, frequency: str = "5min") -> pd.DataFrame:
    data = market(bearish=bearish, volatility=volatility)
    data["time"] = pd.date_range("2026-01-01", periods=len(data), freq=frequency, tz="UTC")
    return IndicatorEngine(load_settings().indicators).calculate_all(data)


def strongify(frame: pd.DataFrame, bearish: bool = False) -> pd.DataFrame:
    """Set the last completed row to an unambiguously confirmed setup."""
    result = frame.copy(); index = result.index[-2]; close = result.at[index, "close"]
    if bearish:
        values = {"ema_9": close - 1, "ema_21": close, "ema_50": close + 1, "ema_200": close + 2, "plus_di_14": 10, "minus_di_14": 35, "rsi_14": 45, "macd": -2, "macd_signal": -1, "macd_histogram": -1, "stoch_k": 20, "stoch_d": 50, "market_structure": "BEARISH", "candle_direction": "BEARISH"}
    else:
        values = {"ema_9": close + 1, "ema_21": close, "ema_50": close - 1, "ema_200": close - 2, "plus_di_14": 35, "minus_di_14": 10, "rsi_14": 60, "macd": 2, "macd_signal": 1, "macd_histogram": 1, "stoch_k": 80, "stoch_d": 50, "market_structure": "BULLISH", "candle_direction": "BULLISH"}
    for key, value in values.items(): result.at[index, key] = value
    result.at[index, "adx_14"] = 30; result.at[index, "atr_percent"] = .25; result.at[index, "body_percent"] = 70
    result.at[index, "recent_high"] = result.at[index, "high"]; result.at[index, "recent_low"] = result.at[index, "low"]
    return result


@pytest.fixture
def engine() -> SignalEngine:
    return SignalEngine(load_settings().signals)


def test_strong_bullish_market_generates_buy(engine: SignalEngine) -> None:
    result = engine.generate_signal(strongify(indicators()), strongify(indicators(frequency="15min")))
    assert result.direction is Direction.BUY
    assert result.bullish_score > result.bearish_score


def test_strong_bearish_market_generates_sell(engine: SignalEngine) -> None:
    result = engine.generate_signal(strongify(indicators(True), True), strongify(indicators(True, frequency="15min"), True))
    assert result.direction is Direction.SELL


def test_mtf_conflict_returns_wait(engine: SignalEngine) -> None:
    result = engine.generate_signal(indicators(True), indicators(frequency="15min"))
    assert result.direction is Direction.WAIT
    assert "MTF_CONFLICT" in result.warnings


def test_extreme_volatility_returns_wait(engine: SignalEngine) -> None:
    m5, m15 = indicators(volatility=40), indicators(volatility=40, frequency="15min")
    m5.loc[m5.index[-2], "atr_percent"] = 1.0
    result = engine.generate_signal(m5, m15)
    assert result.direction is Direction.WAIT
    assert "EXTREME_VOLATILITY" in result.warnings


def test_rsi_extreme_is_a_warning_not_an_opposite_signal(engine: SignalEngine) -> None:
    m5, m15 = indicators(), indicators(frequency="15min")
    m5.loc[m5.index[-2], "rsi_14"] = 75
    result = engine.generate_signal(m5, m15)
    assert "RSI_OVERBOUGHT" in result.warnings
    assert result.direction is not Direction.SELL


def test_nearby_resistance_reduces_bullish_sr_score(engine: SignalEngine) -> None:
    m5, m15 = indicators(), indicators(frequency="15min")
    m5.loc[m5.index[-2], "recent_high"] = m5.loc[m5.index[-2], "close"] + m5.loc[m5.index[-2], "atr_14"] * .2
    m5.loc[m5.index[-2], "high"] = m5.loc[m5.index[-2], "close"] + m5.loc[m5.index[-2], "atr_14"] * .1
    result = engine.generate_signal(m5, m15)
    assert "RESISTANCE_RISK" in result.warnings
    assert result.components["sr_score"] == 0


def test_completed_candle_is_used_not_live_candle(engine: SignalEngine) -> None:
    m5, m15 = indicators(), indicators(frequency="15min")
    expected_time = m5.iloc[-2]["time"].isoformat()
    m5.loc[m5.index[-1], "close"] = 1
    result = engine.generate_signal(m5, m15)
    assert result.timestamp == expected_time


def test_missing_columns_are_clear_validation_errors(engine: SignalEngine) -> None:
    with pytest.raises(SignalValidationError, match="missing required columns"):
        engine.generate_signal(pd.DataFrame(), pd.DataFrame())


def test_appending_future_rows_does_not_change_prior_signal(engine: SignalEngine) -> None:
    m5, m15 = indicators(), indicators(frequency="15min")
    first = engine.generate_signal(m5, m15)
    m5.loc[m5.index[-1], ["close", "ema_9", "rsi_14"]] = [1, 1, 1]
    m15.loc[m15.index[-1], ["close", "ema_9", "rsi_14"]] = [1, 1, 1]
    second = SignalEngine(load_settings().signals).generate_signal(m5, m15)
    assert first.timestamp == second.timestamp
    assert first.direction == second.direction
