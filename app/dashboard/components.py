"""Reusable Streamlit display components."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from app.config.settings import SignalSettings
from app.config.settings import Settings
from app.backtest import BacktestEngine, BacktestValidationError
from app.data.data_validator import DataValidationResult
from app.data.market_status import DataStatus, MarketDataStatus, MarketStatus
from app.signal_engine.models import SignalResult


def _status_text(status: MarketDataStatus) -> tuple[str, str]:
    if status.market is MarketStatus.CLOSED:
        return "Market", "CLOSED"
    if status.market is MarketStatus.UNKNOWN:
        return "Market", "UNKNOWN"
    return "Data", status.data.value


def show_status(status: MarketDataStatus, symbol: str, latest_m5: datetime | None) -> None:
    """Render the separate connection, market, and data availability states."""
    st.subheader("Connection")
    st.success("MT5 Connected")
    market_level = st.success if status.market is MarketStatus.OPEN else st.error if status.market is MarketStatus.CLOSED else st.warning
    market_level(f"Market: {status.market.value}")
    data_label = "LAST AVAILABLE" if status.market is MarketStatus.CLOSED else status.data.value
    data_level = st.success if status.data is DataStatus.LIVE and status.market is MarketStatus.OPEN else st.warning
    data_level(f"Data: {data_label}")
    st.subheader("Symbol")
    st.write(symbol)
    if status.observed_at:
        st.caption(f"Last Tick: {status.observed_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")
    if latest_m5:
        st.caption(f"Latest M5 Candle: {latest_m5.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")
    if status.market is MarketStatus.CLOSED:
        st.warning("MARKET CLOSED - Displaying the last available market data.")
    elif status.data is DataStatus.STALE:
        st.warning("DATA STALE - The displayed market data may no longer represent current market conditions.")
    elif status.data is DataStatus.UNAVAILABLE:
        st.warning("MARKET DATA UNAVAILABLE")


def show_quote(tick: dict[str, object]) -> None:
    """Render the current quote summary."""
    bid = float(tick["bid"])
    ask = float(tick["ask"])
    last = float(tick["last"])
    spread = float(tick["spread"])
    updated = tick["time"]
    current_price = last if last > 0 else (bid + ask) / 2
    columns = st.columns(4)
    columns[0].metric("Current Price", f"{current_price:,.2f}")
    columns[1].metric("Bid", f"{bid:,.2f}")
    columns[2].metric("Ask", f"{ask:,.2f}")
    columns[3].metric("Spread", f"{spread:.2f}")
    if isinstance(updated, datetime):
        st.caption(f"Last Update: {updated.astimezone().strftime('%Y-%m-%d %H:%M:%S')}")


def show_candles(data: pd.DataFrame | None, result: DataValidationResult, status: MarketDataStatus) -> None:
    """Render the latest candles and data-quality messages."""
    if data is None or data.empty:
        st.error("MARKET DATA UNAVAILABLE")
        return
    table = data.tail(10).loc[:, ["time", "open", "high", "low", "close", "tick_volume", "spread"]].copy()
    table.columns = ["Time", "Open", "High", "Low", "Close", "Volume", "Spread"]
    table["Time"] = table["Time"].dt.strftime("%Y-%m-%d %H:%M")
    status_name, status_value = _status_text(status)
    latest = status.observed_at.astimezone().strftime("%Y-%m-%d %H:%M:%S") if status.observed_at else "Unavailable"
    st.caption(f"{status_name}: {status_value} | Latest: {latest}")
    st.dataframe(table, hide_index=True, width="stretch")
    if result.valid:
        st.success("Data Quality: Valid")
    else:
        for message in result.errors:
            st.error(message)
    for message in result.warnings:
        st.warning(message)


def show_indicator_snapshot(snapshot: dict[str, object]) -> None:
    """Render raw values from the latest completed candle without interpretation."""
    groups = {
        "Trend": ["ema_9", "ema_21", "ema_50", "ema_200", "adx_14", "plus_di_14", "minus_di_14"],
        "Momentum": ["rsi_14", "macd", "macd_signal", "macd_histogram", "stoch_k", "stoch_d"],
        "Volatility": ["atr_14", "atr_percent", "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_percent"],
        "Structure": ["market_structure", "recent_high", "recent_low"],
        "Candle": ["candle_direction", "candle_body", "upper_wick", "lower_wick", "bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"],
    }
    timestamp = snapshot.get("time", "Unavailable")
    st.caption(f"Latest completed candle: {timestamp}")
    for title, fields in groups.items():
        st.markdown(f"#### {title}")
        rows = [{"Metric": field, "Value": _format_indicator_value(snapshot.get(field))} for field in fields]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def _format_indicator_value(value: object) -> object:
    if isinstance(value, float):
        return "Unavailable" if pd.isna(value) else f"{value:,.4f}"
    return value if value is not None else "Unavailable"


def show_signal(signal: SignalResult, settings: SignalSettings) -> None:
    """Render the current setup analysis; this view has no execution controls."""
    columns = st.columns(6)
    columns[0].metric("Direction", signal.direction.value)
    columns[1].metric("Score", f"{signal.score} / 100")
    columns[2].metric("Confidence", f"{signal.confidence:.0%}")
    columns[3].metric("Strength", signal.strength.value)
    columns[4].metric("M15 Bias", signal.m15_bias)
    columns[5].metric("M5 Bias", signal.m5_bias)
    st.caption("Confidence is internal model confidence, not a probability of a winning trade.")
    maxima = {"trend_score": settings.weights.macro_trend, "entry_trend_score": settings.weights.entry_trend, "momentum_score": settings.weights.momentum, "structure_score": settings.weights.structure, "volatility_score": settings.weights.volatility, "candle_score": settings.weights.candle, "sr_score": settings.weights.support_resistance}
    labels = {"trend_score": "Trend", "entry_trend_score": "M5 Entry", "momentum_score": "Momentum", "structure_score": "Structure", "volatility_score": "Volatility", "candle_score": "Candle", "sr_score": "Support/Resistance"}
    st.markdown("### Score Breakdown")
    st.dataframe(pd.DataFrame([{"Component": labels[key], "Score": f"{value} / {maxima[key]}"} for key, value in signal.components.items()]), hide_index=True, width="stretch")
    st.markdown("### Reasons")
    for reason in signal.reasons:
        st.write(f"✓ {reason}")
    if signal.warnings:
        st.markdown("### Warnings")
        for warning in signal.warnings:
            st.warning(f"⚠ {warning}")


def show_backtest(m5_data: pd.DataFrame | None, m15_data: pd.DataFrame | None, settings: Settings) -> None:
    """Render opt-in historical validation from the currently loaded data only."""
    if not isinstance(m5_data, pd.DataFrame) or not isinstance(m15_data, pd.DataFrame) or m5_data.empty or m15_data.empty:
        st.info("Backtest requires M5 and M15 historical data.")
        return
    start, end = st.columns(2)
    start_date = start.date_input("Start Date", value=m5_data["time"].iloc[0].date(), key="backtest_start")
    end_date = end.date_input("End Date", value=m5_data["time"].iloc[-1].date(), key="backtest_end")
    horizon = st.selectbox("Signal horizon", settings.backtest.horizons, index=settings.backtest.horizons.index(settings.backtest.default_horizon), key="backtest_horizon")
    if not st.button("Run validation backtest", key="run_backtest"):
        st.caption("Uses theoretical completed-candle entries and normalized directional returns; it does not place orders.")
        return
    try:
        result = BacktestEngine(settings.indicators, settings.signals, settings.backtest).run(m5_data, m15_data, start_date, end_date, horizon)
    except BacktestValidationError as error:
        st.warning(f"Backtest unavailable: {error}")
        return
    summary = result.metrics["horizons"][horizon]
    columns = st.columns(7)
    for column, label, value in zip(columns, ("Signals", "BUY", "SELL", "WAIT", "Win Rate", "Average Return", "Max Drawdown"), (result.total_signals, result.buy_count, result.sell_count, result.wait_count, _percentage(summary["win_rate"]), _percentage(summary["average_return"]), _percentage(result.metrics["maximum_drawdown"])), strict=True): column.metric(label, value)
    st.caption("Theoretical normalized signal-performance curve — not an account or execution simulation.")
    if result.equity_curve:
        curve = pd.DataFrame(result.equity_curve, columns=["time", "equity"]).set_index("time")
        st.line_chart(curve, y="equity")
    if result.warnings:
        for warning in result.warnings: st.warning(warning)


def _percentage(value: object) -> str:
    return "N/A" if value is None else f"{float(value):.2%}"
