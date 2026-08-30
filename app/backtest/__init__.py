"""Historical validation of the existing completed-candle signal engine."""

from app.backtest.engine import BacktestEngine, BacktestValidationError
from app.backtest.models import BacktestResult, SignalRecord

__all__ = ["BacktestEngine", "BacktestResult", "BacktestValidationError", "SignalRecord"]
