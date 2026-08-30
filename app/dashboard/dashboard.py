"""Streamlit dashboard for connection and raw market data."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.config.settings import Settings
from app.dashboard.components import show_backtest, show_candles, show_indicator_snapshot, show_quote, show_signal, show_status


def render_dashboard(settings: Settings, snapshot_loader: Callable[[], dict[str, object]]) -> None:
    """Render and periodically refresh the scanner dashboard."""
    st.set_page_config(page_title="XAUUSD Wolf Market Scanner", layout="wide")
    st.title("XAUUSD WOLF MARKET SCANNER")

    @st.fragment(run_every=f"{settings.app.refresh_seconds}s")
    def refreshable_content() -> None:
        snapshot = snapshot_loader()
        error_kind = snapshot.get("error_kind")
        if error_kind == "connection":
            st.error("MT5 CONNECTION FAILED")
            st.info("Please make sure MetaTrader 5 is installed, running, and available to this Python terminal.")
            return
        if error_kind == "symbol":
            st.error("XAUUSD SYMBOL NOT FOUND")
            st.write("Tried:")
            st.code("\n".join(settings.market.symbol_candidates), language=None)
            return

        symbol = str(snapshot["symbol"])
        status = snapshot.get("status")
        candles = snapshot.get("candles", {})
        m5_data = candles.get("M5") if isinstance(candles, dict) else None
        latest_m5 = m5_data["time"].iloc[-1].to_pydatetime() if m5_data is not None and not m5_data.empty else None
        if status is not None:
            show_status(status, symbol, latest_m5)
        tick = snapshot.get("tick")
        if isinstance(tick, dict):
            show_quote(tick)
        else:
            st.error("MARKET DATA UNAVAILABLE")

        st.subheader("Market Data")
        validations = snapshot.get("validations", {})
        timeframe_statuses = snapshot.get("timeframe_statuses", {})
        tabs = st.tabs(settings.market.timeframes)
        for tab, timeframe in zip(tabs, settings.market.timeframes, strict=True):
            with tab:
                data = candles.get(timeframe) if isinstance(candles, dict) else None
                result = validations.get(timeframe) if isinstance(validations, dict) else None
                timeframe_status = timeframe_statuses.get(timeframe) if isinstance(timeframe_statuses, dict) else None
                if result is not None and timeframe_status is not None:
                    show_candles(data, result, timeframe_status)

        st.subheader("Indicators")
        indicator_snapshots = snapshot.get("indicator_snapshots", {})
        indicator_errors = snapshot.get("indicator_errors", {})
        indicator_timeframes = [timeframe for timeframe in ("M5", "M15") if timeframe in settings.market.timeframes]
        if not indicator_timeframes:
            st.info("No configured indicator timeframes.")
        else:
            indicator_tabs = st.tabs(indicator_timeframes)
            for tab, timeframe in zip(indicator_tabs, indicator_timeframes, strict=True):
                with tab:
                    error = indicator_errors.get(timeframe) if isinstance(indicator_errors, dict) else None
                    indicator_snapshot = indicator_snapshots.get(timeframe) if isinstance(indicator_snapshots, dict) else None
                    if error:
                        st.warning(f"Indicator data unavailable: {error}")
                    elif isinstance(indicator_snapshot, dict):
                        show_indicator_snapshot(indicator_snapshot)
                    else:
                        st.warning("Indicator data unavailable.")

        st.subheader("🐺 WOLF SIGNAL")
        signal_error = snapshot.get("signal_error")
        signal = snapshot.get("signal")
        if signal_error:
            st.warning(f"Signal unavailable: {signal_error}")
        elif signal is not None:
            show_signal(signal, settings.signals)
        else:
            st.warning("Signal unavailable: M5 and M15 indicator data are required.")

        st.subheader("🐺 WOLF BACKTEST")
        m15_data = candles.get("M15") if isinstance(candles, dict) else None
        show_backtest(m5_data, m15_data, settings)

    refreshable_content()
