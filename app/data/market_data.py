"""Market data retrieval and MT5-rate normalization."""

from __future__ import annotations

import logging

import pandas as pd

from app.data.cache import RefreshCache
from app.data.mt5_client import MT5Client


LOGGER = logging.getLogger(__name__)
CANDLE_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]


class MarketDataService:
    """Retrieve normalized market data through one MT5 client."""

    def __init__(self, client: MT5Client, cache: RefreshCache | None = None) -> None:
        self._client = client
        self._cache = cache or RefreshCache()

    def start_refresh(self) -> None:
        """Clear request results before fetching a new dashboard snapshot."""
        self._cache.clear()

    def get_tick(self, symbol: str) -> dict[str, object] | None:
        """Retrieve the current quote once per refresh."""
        return self._cache.get_or_load(("tick", symbol), lambda: self._client.get_current_tick(symbol))

    def get_candles(self, symbol: str, timeframe: int, count: int) -> pd.DataFrame | None:
        """Retrieve and normalize a timeframe's OHLCV rates once per refresh."""
        return self._cache.get_or_load(("candles", symbol, timeframe, count), lambda: self._normalize_rates(self._client.get_rates(symbol, timeframe, count)))

    @staticmethod
    def _normalize_rates(rates: object) -> pd.DataFrame | None:
        if rates is None:
            return None
        data = pd.DataFrame(rates)
        missing = [column for column in CANDLE_COLUMNS if column not in data.columns]
        if missing:
            LOGGER.error("MT5 rate response is missing columns: %s", ", ".join(missing))
            return None
        data = data.loc[:, CANDLE_COLUMNS].copy()
        data["time"] = pd.to_datetime(data["time"], unit="s", errors="coerce", utc=True)
        numeric_columns = [column for column in CANDLE_COLUMNS if column != "time"]
        data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors="coerce")
        return data.drop_duplicates(subset="time", keep="last").sort_values("time").reset_index(drop=True)