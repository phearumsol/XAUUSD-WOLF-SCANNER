"""Chronological, anti-look-ahead validation using existing engines only."""
from __future__ import annotations
from pathlib import Path
from datetime import timedelta
import pandas as pd
from app.backtest.metrics import calculate
from app.backtest.models import BacktestResult, SignalRecord
from app.backtest.trade_simulator import outcomes
from app.backtest.validation import BacktestValidationError, validate
from app.config.settings import BacktestSettings, IndicatorSettings, SignalSettings
from app.indicator_engine import IndicatorEngine
from app.signal_engine import Direction, SignalEngine, SignalValidationError

class BacktestEngine:
    """Validate signals as-of each candle; later prices are outcome-only data."""
    def __init__(self, indicators: IndicatorSettings, signals: SignalSettings, settings: BacktestSettings) -> None:
        self.indicators, self.signals, self.settings = indicators, signals, settings

    def run(self, m5_df: pd.DataFrame, m15_df: pd.DataFrame, start_date: object | None = None, end_date: object | None = None, horizon: int | None = None) -> BacktestResult:
        raw_m5, raw_m15 = validate(m5_df, "M5"), validate(m15_df, "M15")
        start = self._utc(start_date) if start_date is not None else raw_m5.time.iloc[0]
        end = self._utc(end_date) if end_date is not None else raw_m5.time.iloc[-1]
        if start > end: raise BacktestValidationError("start_date must not be after end_date.")
        selected = horizon or self.settings.default_horizon
        if selected not in self.settings.horizons: raise BacktestValidationError("Selected horizon is not configured.")
        m5 = IndicatorEngine(self.indicators).calculate_all(raw_m5, "M5")
        m15 = IndicatorEngine(self.indicators).calculate_all(raw_m15, "M15")
        records: list[SignalRecord] = []; warnings: list[str] = []; warmup = 201
        if len(m5) <= warmup or len(m15) <= warmup: warnings.append("INSUFFICIENT_INDICATOR_WARMUP")
        for index in range(warmup, len(m5)):
            timestamp = m5.at[index, "time"]
            if timestamp < start or timestamp > end: continue
            eligible = m15.index[m15.time + timedelta(minutes=15) <= timestamp]
            if len(eligible) == 0: continue
            try: signal = SignalEngine(self.signals).generate_signal(self._as_of(m5, index), self._as_of(m15, int(eligible[-1])))
            except SignalValidationError: continue
            regime = self._regime(m5.iloc[index]); session = self._session(timestamp)
            if signal.direction is Direction.WAIT: returns, mfe, mae = ({h: None for h in self.settings.horizons},) * 3
            else: returns, mfe, mae = outcomes(raw_m5, index, signal.direction.value, signal.entry_price, self.settings.horizons, self._costs())
            records.append(SignalRecord(signal.timestamp, signal.direction.value, signal.entry_price, signal.score, signal.confidence, signal.strength.value, signal.m15_bias, signal.m5_bias, signal.bullish_score, signal.bearish_score, signal.directional_edge, returns, mfe, mae, signal.warnings, signal.reasons, signal.components, regime, session))
        record_tuple = tuple(records); metrics, curve = calculate(record_tuple, self.settings.horizons, selected)
        if not record_tuple: warnings.append("NO_EVALUABLE_SIGNALS: provide overlapping M5/M15 history beyond the indicator warm-up period.")
        buys, sells, waits = (sum(r.direction == name for r in record_tuple) for name in ("BUY", "SELL", "WAIT"))
        report = {"m5_rows": len(raw_m5), "m15_rows": len(raw_m15), "timezone": "UTC", "warmup_candles": warmup, "selected_horizon": selected}
        return BacktestResult(str(start), str(end), len(raw_m5), len(record_tuple), buys, sells, waits, metrics, record_tuple, curve, tuple(warnings), report)

    @staticmethod
    def _as_of(frame: pd.DataFrame, completed_index: int) -> pd.DataFrame:
        history = frame.iloc[:completed_index + 1].copy()
        return pd.concat([history, history.iloc[[-1]].copy()], ignore_index=True)
    @staticmethod
    def _utc(value: object) -> pd.Timestamp:
        timestamp = pd.Timestamp(value)
        return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
    def _costs(self) -> float: return self.settings.spread_percent / 100 + self.settings.slippage_percent / 100 + self.settings.commission_percent / 100
    def _regime(self, row: pd.Series) -> str:
        if float(row.atr_percent) > self.signals.atr_high_percent: return "HIGH_VOLATILITY"
        if float(row.atr_percent) < self.signals.atr_low_percent: return "LOW_VOLATILITY"
        return "TRENDING" if float(row.adx_14) >= self.signals.adx_established else "RANGING"
    def _session(self, timestamp: pd.Timestamp) -> str:
        hour = timestamp.hour
        if 13 <= hour < 16: return "OVERLAP"
        if 7 <= hour < 13: return "LONDON"
        if 13 <= hour < 22: return "NEW_YORK"
        return "ASIAN"
    @staticmethod
    def export_csv(result: BacktestResult, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True); rows = []
        for r in result.trade_records:
            row = {"timestamp": r.timestamp, "direction": r.direction, "entry_price": r.entry_price, "score": r.score, "confidence": r.confidence, "strength": r.strength, "m15_bias": r.m15_bias, "m5_bias": r.m5_bias, "warnings": "|".join(r.warnings), "reasons": "|".join(r.reasons), "regime": r.regime, "session": r.session}
            for prefix, values in (("return", r.returns), ("mfe", r.mfe), ("mae", r.mae)): row.update({f"{prefix}_{h}": v for h, v in values.items()})
            rows.append(row)
        path = directory / f"wolf_backtest_signals_{pd.Timestamp.now(tz='UTC').strftime('%Y%m%d_%H%M%S_%f')}.csv"; pd.DataFrame(rows).to_csv(path, index=False); return path
