"""Plain-text report for exported or console backtest summaries."""
from __future__ import annotations
from app.backtest.models import BacktestResult
def render(result: BacktestResult, horizon: int) -> str:
    s = result.metrics["horizons"][horizon]; fmt = lambda value: "N/A" if value is None else f"{value:.2%}"
    return "\n".join(("# WOLF SCANNER BACKTEST", f"Period: {result.start_date} to {result.end_date}", f"Signals: {result.total_signals} | BUY: {result.buy_count} | SELL: {result.sell_count} | WAIT: {result.wait_count}", f"{horizon}-Candle Win Rate: {fmt(s['win_rate'])}", f"Average Return: {fmt(s['average_return'])}", f"Profit Factor: {s['profit_factor'] if s['profit_factor'] is not None else 'N/A'}", f"Maximum Drawdown: {fmt(result.metrics['maximum_drawdown'])}", "Theoretical normalized signal-performance curve; not an account simulation."))
