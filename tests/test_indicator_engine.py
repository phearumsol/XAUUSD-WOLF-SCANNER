from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.config.settings import load_settings
from app.indicator_engine import IndicatorEngine, IndicatorValidationError


def make_ohlcv(rows: int = 260, frequency: str = "5min") -> pd.DataFrame:
    close = pd.Series(3000 + np.linspace(0, 80, rows) + np.sin(np.arange(rows) / 4))
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=rows, freq=frequency, tz="UTC"),
        "open": close - 0.25,
        "high": close + 1.0,
        "low": close - 1.0,
        "close": close,
        "tick_volume": 100,
    })


@pytest.fixture
def engine() -> IndicatorEngine:
    return IndicatorEngine(load_settings().indicators)


def test_calculate_all_adds_requested_indicator_columns(engine: IndicatorEngine) -> None:
    result = engine.calculate_all(make_ohlcv(), "M5")
    expected = {"ema_9", "ema_21", "ema_50", "ema_200", "adx_14", "plus_di_14", "minus_di_14", "rsi_14", "macd", "macd_signal", "macd_histogram", "stoch_k", "stoch_d", "atr_14", "atr_percent", "bb_middle", "bb_upper", "bb_lower", "bb_width", "bb_percent", "swing_high", "swing_low", "recent_high", "recent_low", "market_structure", "higher_high", "higher_low", "lower_high", "lower_low", "candle_body", "candle_range", "upper_wick", "lower_wick", "body_percent", "upper_wick_percent", "lower_wick_percent", "candle_direction", "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"}
    assert expected.issubset(result.columns)
    assert pd.api.types.is_numeric_dtype(result["rsi_14"])
    assert result["ema_200"].notna().any()


def test_missing_required_column_is_rejected(engine: IndicatorEngine) -> None:
    with pytest.raises(IndicatorValidationError, match="missing required columns"):
        engine.calculate_all(make_ohlcv().drop(columns="close"))


def test_invalid_numeric_value_is_rejected(engine: IndicatorEngine) -> None:
    data = make_ohlcv()
    data["open"] = data["open"].astype(object)
    data.loc[0, "open"] = "invalid"
    with pytest.raises(IndicatorValidationError, match="non-numeric"):
        engine.calculate_all(data)


def test_unsorted_and_duplicate_timestamps_are_normalized(engine: IndicatorEngine) -> None:
    data = make_ohlcv(40)
    duplicate = data.iloc[[5]].copy()
    result = engine.calculate_all(pd.concat([data.iloc[::-1], duplicate], ignore_index=True))
    assert result["time"].is_monotonic_increasing
    assert not result["time"].duplicated().any()


def test_insufficient_history_returns_warmup_nans_without_failing(engine: IndicatorEngine) -> None:
    result = engine.calculate_all(make_ohlcv(10))
    assert result["ema_200"].isna().all()
    assert result["macd_signal"].isna().all()


def test_missing_numeric_values_do_not_crash_calculation(engine: IndicatorEngine) -> None:
    data = make_ohlcv()
    data.loc[10, "close"] = np.nan
    result = engine.calculate_all(data)
    assert pd.isna(result.loc[10, "close"])
    assert "atr_14" in result


def test_calculations_do_not_change_when_future_rows_are_appended(engine: IndicatorEngine) -> None:
    data = make_ohlcv(160)
    base = engine.calculate_all(data.iloc[:80])
    extended = engine.calculate_all(data)
    columns = ["ema_9", "rsi_14", "atr_14", "recent_high", "recent_low", "swing_high", "swing_low", "market_structure"]
    pd.testing.assert_frame_equal(base[columns], extended.iloc[:80][columns], check_dtype=False)


def test_m5_and_m15_frames_are_processed_independently(engine: IndicatorEngine) -> None:
    m5 = engine.calculate_all(make_ohlcv(120, "5min"), "M5")
    m15 = engine.calculate_all(make_ohlcv(120, "15min"), "M15")
    assert len(m5) == len(m15) == 120
    assert not m5["time"].equals(m15["time"])


def test_latest_snapshot_uses_the_completed_candle(engine: IndicatorEngine) -> None:
    result = engine.calculate_all(make_ohlcv())
    snapshot = engine.latest_completed_snapshot(result)
    assert snapshot["time"] == result.iloc[-2]["time"].to_pydatetime().isoformat()