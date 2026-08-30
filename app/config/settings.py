"""Typed configuration loading for the scanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

from dotenv import load_dotenv
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class MarketSettings:
    """Market data settings."""

    symbol_candidates: list[str]
    default_symbol: str
    timeframes: list[str]
    candle_count: int


@dataclass(frozen=True)
class ApplicationSettings:
    """Dashboard settings."""

    refresh_seconds: int


@dataclass(frozen=True)
class MarketStatusSettings:
    """Freshness thresholds and initial UTC XAUUSD market-session policy."""

    live_tick_max_age_seconds: int
    recent_data_max_age_seconds: int
    stale_data_max_age_seconds: int
    session_timezone: str
    weekly_open_day: int
    weekly_open_hour: int
    weekly_close_day: int
    weekly_close_hour: int


@dataclass(frozen=True)
class IndicatorSettings:
    """Configurable parameters for raw technical indicator calculations."""

    ema_periods: list[int]
    rsi_period: int
    adx_period: int
    atr_period: int
    bollinger_period: int
    bollinger_std: float
    macd_fast_period: int
    macd_slow_period: int
    macd_signal_period: int
    stochastic_k_period: int
    stochastic_k_smoothing: int
    stochastic_d_period: int
    swing_lookback: int
    recent_extreme_period: int


@dataclass(frozen=True)
class SignalWeights:
    macro_trend: int
    entry_trend: int
    momentum: int
    structure: int
    volatility: int
    candle: int
    support_resistance: int


@dataclass(frozen=True)
class SignalSettings:
    buy_threshold: int
    sell_threshold: int
    minimum_directional_edge: int
    very_strong_score: int
    very_strong_edge: int
    history_size: int
    adx_weak: float
    adx_developing: float
    adx_established: float
    adx_strong: float
    rsi_bullish_min: float
    rsi_bullish_max: float
    rsi_bearish_min: float
    rsi_bearish_max: float
    rsi_overbought: float
    rsi_oversold: float
    atr_low_percent: float
    atr_normal_percent: float
    atr_high_percent: float
    sr_proximity_atr: float
    weights: SignalWeights


@dataclass(frozen=True)
class BacktestSettings:
    horizons: list[int]
    default_horizon: int
    spread_percent: float
    slippage_percent: float
    commission_percent: float
    session_timezone: str


@dataclass(frozen=True)
class MT5Settings:
    """Optional MetaTrader 5 terminal connection settings."""

    terminal_path: str | None
    login: int | None
    password: str | None
    server: str | None


@dataclass(frozen=True)
class Settings:
    """All scanner settings exposed to the application."""

    market: MarketSettings
    app: ApplicationSettings
    market_status: MarketStatusSettings
    indicators: IndicatorSettings
    signals: SignalSettings
    backtest: BacktestSettings
    mt5: MT5Settings


def _required_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section '{name}' must be a mapping.")
    return value


def _optional_string(value: Any, name: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"Configuration value '{name}' must be a string or null.")
    return value


def load_settings(config_path: Path | None = None) -> Settings:
    """Load YAML settings and apply non-empty environment variable overrides."""
    path = config_path or PROJECT_ROOT / "config.yaml"
    if not path.is_file():
        raise ValueError(f"Configuration file was not found: {path}")

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    with path.open("r", encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file) or {}
    if not isinstance(raw_config, dict):
        raise ValueError("Configuration file must contain a top-level mapping.")

    market = _required_mapping(raw_config.get("market"), "market")
    application = _required_mapping(raw_config.get("app"), "app")
    market_status = _required_mapping(raw_config.get("market_status"), "market_status")
    indicators = _required_mapping(raw_config.get("indicators"), "indicators")
    signals = _required_mapping(raw_config.get("signals"), "signals")
    backtest = _required_mapping(raw_config.get("backtest"), "backtest")
    mt5 = _required_mapping(raw_config.get("mt5"), "mt5")
    candidates = market.get("symbol_candidates")
    timeframes = market.get("timeframes")
    if not isinstance(candidates, list) or not all(isinstance(item, str) and item for item in candidates):
        raise ValueError("market.symbol_candidates must be a non-empty list of strings.")
    if not isinstance(timeframes, list) or not all(isinstance(item, str) and item for item in timeframes):
        raise ValueError("market.timeframes must be a non-empty list of strings.")

    symbol_override = os.getenv("MT5_SYMBOL")
    default_symbol = symbol_override or market.get("default_symbol")
    if not isinstance(default_symbol, str) or not default_symbol:
        raise ValueError("market.default_symbol must be a non-empty string.")
    if symbol_override:
        candidates = [symbol_override, *[candidate for candidate in candidates if candidate != symbol_override]]

    candle_count = market.get("candle_count")
    refresh_seconds = application.get("refresh_seconds")
    if not isinstance(candle_count, int) or candle_count <= 0:
        raise ValueError("market.candle_count must be a positive integer.")
    if not isinstance(refresh_seconds, int) or refresh_seconds <= 0:
        raise ValueError("app.refresh_seconds must be a positive integer.")

    status_values = [
        market_status.get("live_tick_max_age_seconds"),
        market_status.get("recent_data_max_age_seconds"),
        market_status.get("stale_data_max_age_seconds"),
    ]
    if not all(isinstance(value, int) and value > 0 for value in status_values):
        raise ValueError("market_status freshness thresholds must be positive integers.")
    if not status_values[0] <= status_values[1] <= status_values[2]:
        raise ValueError("market_status thresholds must increase from live to stale.")
    session_values = [
        market_status.get("weekly_open_day"),
        market_status.get("weekly_open_hour"),
        market_status.get("weekly_close_day"),
        market_status.get("weekly_close_hour"),
    ]
    if not all(isinstance(value, int) for value in session_values):
        raise ValueError("market_status session day and hour values must be integers.")
    if not 0 <= session_values[0] <= 6 or not 0 <= session_values[2] <= 6:
        raise ValueError("market_status session days must use Monday=0 through Sunday=6.")
    if not 0 <= session_values[1] <= 23 or not 0 <= session_values[3] <= 23:
        raise ValueError("market_status session hours must be between 0 and 23.")
    session_timezone = market_status.get("session_timezone")
    if not isinstance(session_timezone, str) or not session_timezone:
        raise ValueError("market_status.session_timezone must be a non-empty IANA timezone name.")

    ema_periods = indicators.get("ema_periods")
    if not isinstance(ema_periods, list) or not all(isinstance(period, int) and period > 0 for period in ema_periods):
        raise ValueError("indicators.ema_periods must be a list of positive integers.")
    indicator_values = [
        indicators.get("rsi_period"), indicators.get("adx_period"), indicators.get("atr_period"),
        indicators.get("bollinger_period"), indicators.get("macd_fast_period"), indicators.get("macd_slow_period"),
        indicators.get("macd_signal_period"), indicators.get("stochastic_k_period"),
        indicators.get("stochastic_k_smoothing"), indicators.get("stochastic_d_period"),
        indicators.get("swing_lookback"), indicators.get("recent_extreme_period"),
    ]
    if not all(isinstance(value, int) and value > 0 for value in indicator_values):
        raise ValueError("All indicator periods must be positive integers.")
    bollinger_std = indicators.get("bollinger_std")
    if not isinstance(bollinger_std, (int, float)) or bollinger_std <= 0:
        raise ValueError("indicators.bollinger_std must be a positive number.")
    if indicators["macd_fast_period"] >= indicators["macd_slow_period"]:
        raise ValueError("indicators.macd_fast_period must be less than macd_slow_period.")

    weights = _required_mapping(signals.get("weights"), "signals.weights")
    weight_names = ("macro_trend", "entry_trend", "momentum", "structure", "volatility", "candle", "support_resistance")
    if not all(isinstance(weights.get(name), int) and weights[name] >= 0 for name in weight_names):
        raise ValueError("signals.weights values must be non-negative integers.")
    if sum(weights[name] for name in weight_names) != 100:
        raise ValueError("signals.weights must total 100.")
    signal_numbers = ("buy_threshold", "sell_threshold", "minimum_directional_edge", "very_strong_score", "very_strong_edge", "history_size")
    if not all(isinstance(signals.get(name), int) and signals[name] > 0 for name in signal_numbers):
        raise ValueError("Signal thresholds and history_size must be positive integers.")
    signal_decimals = ("adx_weak", "adx_developing", "adx_established", "adx_strong", "rsi_bullish_min", "rsi_bullish_max", "rsi_bearish_min", "rsi_bearish_max", "rsi_overbought", "rsi_oversold", "atr_low_percent", "atr_normal_percent", "atr_high_percent", "sr_proximity_atr")
    if not all(isinstance(signals.get(name), (int, float)) and signals[name] >= 0 for name in signal_decimals):
        raise ValueError("Signal numeric settings must be non-negative numbers.")
    horizons = backtest.get("horizons")
    if not isinstance(horizons, list) or not horizons or not all(isinstance(item, int) and item > 0 for item in horizons):
        raise ValueError("backtest.horizons must be a non-empty list of positive integers.")
    if backtest.get("default_horizon") not in horizons:
        raise ValueError("backtest.default_horizon must be listed in backtest.horizons.")
    cost_names = ("spread_percent", "slippage_percent", "commission_percent")
    if not all(isinstance(backtest.get(name), (int, float)) and backtest[name] >= 0 for name in cost_names):
        raise ValueError("backtest costs must be non-negative numbers.")
    if not isinstance(backtest.get("session_timezone"), str) or not backtest["session_timezone"]:
        raise ValueError("backtest.session_timezone must be a non-empty IANA timezone name.")

    login_text = os.getenv("MT5_LOGIN") or mt5.get("login")
    try:
        login = int(login_text) if login_text not in (None, "") else None
    except (TypeError, ValueError) as error:
        raise ValueError("MT5 login must be an integer.") from error

    mt5_settings = MT5Settings(
        terminal_path=os.getenv("MT5_TERMINAL_PATH") or _optional_string(mt5.get("terminal_path"), "mt5.terminal_path"),
        login=login,
        password=os.getenv("MT5_PASSWORD") or _optional_string(mt5.get("password"), "mt5.password"),
        server=os.getenv("MT5_SERVER") or _optional_string(mt5.get("server"), "mt5.server"),
    )
    if mt5_settings.login is None and any((mt5_settings.password, mt5_settings.server)):
        raise ValueError("MT5 password and server require an MT5 login.")
    return Settings(
        market=MarketSettings(candidates, default_symbol, timeframes, candle_count),
        app=ApplicationSettings(refresh_seconds),
        market_status=MarketStatusSettings(*status_values, session_timezone, *session_values),
        indicators=IndicatorSettings(ema_periods, *indicator_values[:4], float(bollinger_std), *indicator_values[4:]),
        signals=SignalSettings(
            *(signals[name] for name in signal_numbers),
            *(float(signals[name]) for name in signal_decimals),
            SignalWeights(**{name: weights[name] for name in weight_names}),
        ),
        backtest=BacktestSettings(horizons, backtest["default_horizon"], *(float(backtest[name]) for name in cost_names), backtest["session_timezone"]),
        mt5=mt5_settings,
    )
