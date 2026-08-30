from __future__ import annotations
import numpy as np
import pandas as pd
import pytest
from app.backtest import BacktestEngine, BacktestValidationError
from app.config.settings import load_settings

def data(rows=320, freq="5min", slope=.35):
    close = 3000 + np.arange(rows) * slope + np.sin(np.arange(rows) / 3)
    return pd.DataFrame({"time": pd.date_range("2026-01-01", periods=rows, freq=freq, tz="UTC"), "open": close-.1, "high": close+1, "low": close-1, "close": close, "tick_volume": 100})

@pytest.fixture
def engine():
    s = load_settings(); return BacktestEngine(s.indicators, s.signals, s.backtest)

def test_run_is_deterministic(engine):
    one = engine.run(data(660), data(220, "15min")); two = engine.run(data(660), data(220, "15min"))
    assert one.trade_records == two.trade_records and one.metrics == two.metrics

def test_records_waits_and_uses_horizons(engine):
    result = engine.run(data(660), data(220, "15min"))
    assert result.total_signals == result.buy_count + result.sell_count + result.wait_count
    assert set(result.metrics["horizons"]) == {1, 3, 5, 10}

@pytest.mark.parametrize("column", ["time", "open", "high", "low", "close", "tick_volume"])
def test_missing_columns_fail(engine, column):
    with pytest.raises(BacktestValidationError): engine.run(data().drop(columns=column), data(freq="15min"))

def test_duplicate_timestamp_fails(engine):
    frame = data(); frame.loc[1, "time"] = frame.loc[0, "time"]
    with pytest.raises(BacktestValidationError, match="sorted and unique"): engine.run(frame, data(freq="15min"))

def test_empty_data_fails(engine):
    with pytest.raises(BacktestValidationError): engine.run(pd.DataFrame(), pd.DataFrame())

def test_invalid_date_and_horizon_fail(engine):
    with pytest.raises(BacktestValidationError): engine.run(data(), data(freq="15min"), "2027-01-01", "2026-01-01")
    with pytest.raises(BacktestValidationError): engine.run(data(), data(freq="15min"), horizon=2)

def test_future_modification_does_not_change_earlier_signal(engine):
    base5, base15 = data(), data(freq="15min")
    baseline = engine.run(base5, base15, end_date=base5.time.iloc[260])
    changed = base5.copy(); changed.loc[changed.index > 280, ["open", "high", "low", "close"]] *= 2
    rerun = engine.run(changed, base15, end_date=base5.time.iloc[260])
    assert [(r.timestamp, r.direction, r.score) for r in baseline.trade_records] == [(r.timestamp, r.direction, r.score) for r in rerun.trade_records]

def test_csv_export_does_not_overwrite(engine, tmp_path):
    result = engine.run(data(660), data(220, "15min")); first = engine.export_csv(result, tmp_path); second = engine.export_csv(result, tmp_path)
    assert first.exists() and second.exists() and first != second

def test_equity_and_summary_are_present(engine):
    result = engine.run(data(660), data(220, "15min"))
    assert "maximum_drawdown" in result.metrics and isinstance(result.equity_curve, tuple)
