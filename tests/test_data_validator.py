from __future__ import annotations

import pandas as pd

from app.data.data_validator import validate_candles


def make_candles(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({"time": pd.date_range("2026-01-01", periods=rows, freq="h", tz="UTC"), "open": [100.0] * rows, "high": [102.0] * rows, "low": [99.0] * rows, "close": [101.0] * rows, "tick_volume": [10] * rows, "spread": [2] * rows, "real_volume": [0] * rows})


def test_valid_ohlc_data_is_accepted() -> None:
    assert validate_candles(make_candles(), 3).valid


def test_impossible_ohlc_data_is_rejected() -> None:
    data = make_candles()
    data.loc[0, "high"] = 99.0
    result = validate_candles(data, 3)
    assert not result.valid
    assert any("OHLC rules" in error for error in result.errors)


def test_missing_values_are_rejected() -> None:
    data = make_candles()
    data.loc[1, "close"] = None
    assert not validate_candles(data, 3).valid


def test_duplicate_timestamps_are_rejected() -> None:
    data = make_candles()
    data.loc[1, "time"] = data.loc[0, "time"]
    result = validate_candles(data, 3)
    assert not result.valid
    assert any("duplicate" in error for error in result.errors)


def test_insufficient_candles_are_rejected() -> None:
    result = validate_candles(make_candles(2), 3)
    assert not result.valid
    assert any("expected at least" in error for error in result.errors)