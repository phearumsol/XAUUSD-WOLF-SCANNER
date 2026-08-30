"""Explicit validation for received candle data."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume")


@dataclass(frozen=True)
class DataValidationResult:
    """Structured outcome of candle-data validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_candles(data: pd.DataFrame | None, required_count: int) -> DataValidationResult:
    """Validate availability, shape, ordering, completeness, and OHLC rules."""
    errors: list[str] = []
    warnings: list[str] = []
    if data is None or data.empty:
        return DataValidationResult(False, ["No candle data was returned."], warnings)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}.")
        return DataValidationResult(False, errors, warnings)
    if len(data) < required_count:
        errors.append(f"Received {len(data)} candles; expected at least {required_count}.")
    if data.loc[:, REQUIRED_COLUMNS].isna().any().any():
        errors.append("Candle data contains missing values.")
    timestamps = pd.to_datetime(data["time"], errors="coerce", utc=True)
    if timestamps.isna().any():
        errors.append("Candle data contains invalid timestamps.")
    elif timestamps.duplicated().any():
        errors.append("Candle data contains duplicate timestamps.")
    elif not timestamps.is_monotonic_increasing:
        errors.append("Candle timestamps are not in chronological order.")
    numeric_data = data.loc[:, ["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    if numeric_data.isna().any().any():
        errors.append("OHLC data contains non-numeric values.")
    else:
        impossible = ((numeric_data["high"] < numeric_data[["open", "close"]].max(axis=1)) | (numeric_data["low"] > numeric_data[["open", "close"]].min(axis=1)) | (numeric_data["high"] < numeric_data["low"]))
        if impossible.any():
            errors.append(f"OHLC rules fail for {int(impossible.sum())} candle(s).")
    return DataValidationResult(not errors, errors, warnings)