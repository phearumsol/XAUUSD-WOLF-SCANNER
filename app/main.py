"""Application composition root for the Streamlit scanner."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from app.config.settings import PROJECT_ROOT, Settings, load_settings
from app.dashboard.dashboard import render_dashboard
from app.data.cache import RefreshCache
from app.data.data_validator import DataValidationResult, validate_candles
from app.data.market_data import MarketDataService
from app.data.market_status import MarketDataStatus, evaluate_market_data
from app.data.mt5_client import MT5Client, TIMEFRAME_MAP
from app.indicator_engine import IndicatorEngine, IndicatorValidationError
from app.signal_engine import SignalEngine, SignalValidationError


def configure_logging() -> None:
    """Configure file logging once for the process."""
    log_path = Path(PROJECT_ROOT) / "logs" / "scanner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        force=True,
    )


@st.cache_resource
def get_client(settings: Settings) -> MT5Client:
    """Preserve one MT5 client across Streamlit reruns."""
    return MT5Client(settings.mt5)


@st.cache_resource
def get_signal_engine(settings: Settings) -> SignalEngine:
    """Preserve the in-memory signal history across Streamlit refreshes."""
    return SignalEngine(settings.signals)


def build_snapshot(settings: Settings, client: MT5Client) -> dict[str, object]:
    """Fetch one complete connection and raw-data dashboard snapshot."""
    logger = logging.getLogger(__name__)
    if not client.connect():
        return {"error_kind": "connection", "message": client.last_error}
    symbol = client.find_symbol(settings.market.symbol_candidates)
    if symbol is None:
        return {"error_kind": "symbol", "message": client.last_error}

    service = MarketDataService(client, RefreshCache())
    service.start_refresh()
    candles: dict[str, object] = {}
    validations: dict[str, DataValidationResult] = {}
    timeframe_statuses: dict[str, MarketDataStatus] = {}
    indicator_frames: dict[str, pd.DataFrame] = {}
    indicator_snapshots: dict[str, dict[str, object]] = {}
    indicator_errors: dict[str, str] = {}
    indicator_engine = IndicatorEngine(settings.indicators)
    for timeframe_name in settings.market.timeframes:
        timeframe = TIMEFRAME_MAP.get(timeframe_name)
        if timeframe is None:
            validations[timeframe_name] = DataValidationResult(False, [f"Unsupported timeframe: {timeframe_name}."])
            continue
        data = service.get_candles(symbol, timeframe, settings.market.candle_count)
        candles[timeframe_name] = data
        validations[timeframe_name] = validate_candles(data, settings.market.candle_count)
        latest_candle = data["time"].iloc[-1].to_pydatetime() if data is not None and not data.empty else None
        timeframe_statuses[timeframe_name] = evaluate_market_data(settings.market_status, latest_candle)
        if isinstance(data, pd.DataFrame):
            try:
                indicator_data = indicator_engine.calculate_all(data, timeframe_name)
                indicator_frames[timeframe_name] = indicator_data
                indicator_snapshots[timeframe_name] = indicator_engine.latest_completed_snapshot(indicator_data)
            except IndicatorValidationError as error:
                indicator_errors[timeframe_name] = str(error)
                logger.warning("[INDICATOR] %s calculation skipped: %s", timeframe_name, error)
        logger.info("Retrieved %s candle data for %s.", timeframe_name, symbol)
    signal = None
    signal_error = None
    if "M5" in indicator_frames and "M15" in indicator_frames:
        try:
            signal = get_signal_engine(settings).generate_signal(indicator_frames["M5"], indicator_frames["M15"])
        except SignalValidationError as error:
            signal_error = str(error)
            logger.warning("[SIGNAL] Calculation skipped: %s", error)
    tick = service.get_tick(symbol)
    tick_timestamp = tick.get("time") if isinstance(tick, dict) else None
    return {
        "symbol": symbol,
        "tick": tick,
        "status": evaluate_market_data(settings.market_status, tick_timestamp if hasattr(tick_timestamp, "tzinfo") else None),
        "candles": candles,
        "validations": validations,
        "timeframe_statuses": timeframe_statuses,
        "indicator_frames": indicator_frames,
        "indicator_snapshots": indicator_snapshots,
        "indicator_errors": indicator_errors,
        "signal": signal,
        "signal_error": signal_error,
    }


def main() -> None:
    """Load configuration and launch the dashboard."""
    configure_logging()
    try:
        settings = load_settings()
        client = get_client(settings)
        render_dashboard(settings, lambda: build_snapshot(settings, client))
    except Exception:
        logging.getLogger(__name__).exception("Unexpected application error")
        st.error("The scanner could not start. Check logs/scanner.log for technical details.")


if __name__ == "__main__":
    main()
