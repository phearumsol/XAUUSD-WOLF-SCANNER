"""Typed, compact backtest outputs."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

@dataclass(frozen=True)
class SignalRecord:
    timestamp: str; direction: str; entry_price: float; score: int; confidence: float; strength: str
    m15_bias: str; m5_bias: str; bullish_score: int; bearish_score: int; directional_edge: int
    returns: Mapping[int, float | None]; mfe: Mapping[int, float | None]; mae: Mapping[int, float | None]
    warnings: tuple[str, ...]; reasons: tuple[str, ...]; components: Mapping[str, int]; regime: str; session: str

@dataclass(frozen=True)
class BacktestResult:
    start_date: str; end_date: str; total_candles: int; total_signals: int; buy_count: int; sell_count: int; wait_count: int
    metrics: Mapping[str, object]; trade_records: tuple[SignalRecord, ...]; equity_curve: tuple[tuple[str, float], ...]
    warnings: tuple[str, ...]; data_quality_report: Mapping[str, object]
