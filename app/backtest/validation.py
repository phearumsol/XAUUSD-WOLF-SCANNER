"""Strict historical OHLCV validation before calculations begin."""
from __future__ import annotations
import pandas as pd

REQUIRED = ("time", "open", "high", "low", "close", "tick_volume")
class BacktestValidationError(ValueError): pass

def validate(data: pd.DataFrame, name: str) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame) or data.empty: raise BacktestValidationError(f"{name} historical data is empty.")
    missing = set(REQUIRED) - set(data.columns)
    if missing: raise BacktestValidationError(f"{name} historical data is missing columns: {', '.join(sorted(missing))}.")
    frame = data.loc[:, REQUIRED].copy(); frame["time"] = pd.to_datetime(frame["time"], utc=True, errors="coerce")
    if frame["time"].isna().any(): raise BacktestValidationError(f"{name} has invalid timestamps.")
    if frame["time"].duplicated().any() or not frame["time"].is_monotonic_increasing: raise BacktestValidationError(f"{name} timestamps must be sorted and unique.")
    numeric = frame.drop(columns="time").apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any(): raise BacktestValidationError(f"{name} contains missing or non-numeric OHLCV values.")
    frame[numeric.columns] = numeric
    if (frame.high < frame[["open", "close"]].max(axis=1)).any() or (frame.low > frame[["open", "close"]].min(axis=1)).any() or (frame.high < frame.low).any(): raise BacktestValidationError(f"{name} contains invalid OHLC values.")
    return frame
