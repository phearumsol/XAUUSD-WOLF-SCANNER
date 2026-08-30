"""Small, isolated adapter around the official MetaTrader5 API."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None  # type: ignore[assignment]

from app.config.settings import MT5Settings


LOGGER = logging.getLogger(__name__)
TIMEFRAME_MAP: dict[str, int] = {
    "H4": getattr(mt5, "TIMEFRAME_H4", 16388),
    "H1": getattr(mt5, "TIMEFRAME_H1", 16385),
    "M30": getattr(mt5, "TIMEFRAME_M30", 30),
    "M15": getattr(mt5, "TIMEFRAME_M15", 15),
    "M5": getattr(mt5, "TIMEFRAME_M5", 5),
}


class MT5Client:
    """Manage one MetaTrader 5 terminal connection and its requests."""

    def __init__(self, settings: MT5Settings) -> None:
        self._settings = settings
        self._connected = False
        self.last_error: str | None = None

    def _set_error(self, message: str) -> None:
        self.last_error = message
        LOGGER.error(message)

    def connect(self) -> bool:
        """Initialize MT5, using optional terminal and account settings."""
        if self._connected and self.is_connected():
            return True
        if mt5 is None:
            self._set_error("The MetaTrader5 Python package is not installed.")
            return False
        options: dict[str, Any] = {}
        if self._settings.terminal_path:
            options["path"] = self._settings.terminal_path
        if self._settings.login is not None:
            options["login"] = self._settings.login
        if self._settings.password:
            options["password"] = self._settings.password
        if self._settings.server:
            options["server"] = self._settings.server
        try:
            initialized = mt5.initialize(**options)
        except Exception as error:
            self._set_error(f"MT5 initialization raised an exception: {error}")
            return False
        if not initialized:
            self._set_error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        self._connected = True
        self.last_error = None
        LOGGER.info("Connected to MetaTrader 5 terminal.")
        return True

    def disconnect(self) -> None:
        """Close the active MT5 connection."""
        if mt5 is not None and self._connected:
            mt5.shutdown()
            LOGGER.info("Disconnected from MetaTrader 5 terminal.")
        self._connected = False

    def is_connected(self) -> bool:
        """Return whether this client has an active MT5 terminal connection."""
        if not self._connected or mt5 is None:
            return False
        try:
            return mt5.terminal_info() is not None
        except Exception:
            return False

    def find_symbol(self, symbol_candidates: list[str]) -> str | None:
        """Find and select the first broker-supported symbol candidate."""
        if not self.is_connected():
            self._set_error("Cannot find a symbol without an MT5 connection.")
            return None
        for symbol in symbol_candidates:
            info = mt5.symbol_info(symbol)
            if info is None:
                continue
            if not info.visible and not mt5.symbol_select(symbol, True):
                LOGGER.warning("Symbol %s exists but could not be selected.", symbol)
                continue
            LOGGER.info("Detected market symbol: %s", symbol)
            return symbol
        self._set_error("No configured XAUUSD symbol candidate is available.")
        return None

    def get_symbol_info(self, symbol: str) -> Any | None:
        """Get broker metadata for a selected symbol."""
        return mt5.symbol_info(symbol) if self.is_connected() else None

    def get_current_tick(self, symbol: str) -> dict[str, float | datetime] | None:
        """Return the latest quote with a calculated absolute spread."""
        if not self.is_connected():
            return None
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self._set_error(f"No current tick was returned for {symbol}.")
            return None
        bid = float(tick.bid)
        ask = float(tick.ask)
        return {"bid": bid, "ask": ask, "last": float(tick.last), "time": datetime.fromtimestamp(tick.time, tz=timezone.utc), "spread": ask - bid}

    def get_rates(self, symbol: str, timeframe: int, count: int) -> Any | None:
        """Retrieve the most recent OHLCV rates from MT5."""
        if not self.is_connected():
            return None
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            self._set_error(f"No rates returned for {symbol}; MT5 error: {mt5.last_error()}")
        return rates