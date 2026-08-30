"""Market session and received-data freshness evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config.settings import MarketStatusSettings


class MarketStatus(str, Enum):
    """Expected availability of the configured market session."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class DataStatus(str, Enum):
    """Freshness of an observed tick or latest candle timestamp."""

    LIVE = "LIVE"
    RECENT = "RECENT"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class MarketDataStatus:
    """Separate market session and data freshness state."""

    market: MarketStatus
    data: DataStatus
    observed_at: datetime | None


def _require_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamps must be timezone-aware.")
    return value.astimezone(timezone.utc)


def determine_market_status(settings: MarketStatusSettings, now: datetime | None = None) -> MarketStatus:
    """Evaluate the initial configurable weekly session window in its configured timezone."""
    current = _require_aware(now) or datetime.now(timezone.utc)
    try:
        local_time = current.astimezone(ZoneInfo(settings.session_timezone))
    except ZoneInfoNotFoundError:
        return MarketStatus.UNKNOWN
    current_slot = local_time.weekday() * 24 + local_time.hour
    open_slot = settings.weekly_open_day * 24 + settings.weekly_open_hour
    close_slot = settings.weekly_close_day * 24 + settings.weekly_close_hour
    if open_slot < close_slot:
        is_open = open_slot <= current_slot < close_slot
    else:
        is_open = current_slot >= open_slot or current_slot < close_slot
    return MarketStatus.OPEN if is_open else MarketStatus.CLOSED


def determine_data_status(observed_at: datetime | None, settings: MarketStatusSettings, now: datetime | None = None) -> DataStatus:
    """Classify an observed timestamp with timezone-aware age comparisons."""
    timestamp = _require_aware(observed_at)
    if timestamp is None:
        return DataStatus.UNAVAILABLE
    current = _require_aware(now) or datetime.now(timezone.utc)
    age_seconds = (current - timestamp).total_seconds()
    if age_seconds < 0:
        return DataStatus.RECENT
    if age_seconds <= settings.live_tick_max_age_seconds:
        return DataStatus.LIVE
    if age_seconds <= settings.recent_data_max_age_seconds:
        return DataStatus.RECENT
    if age_seconds <= settings.stale_data_max_age_seconds:
        return DataStatus.STALE
    return DataStatus.STALE


def evaluate_market_data(settings: MarketStatusSettings, observed_at: datetime | None, now: datetime | None = None) -> MarketDataStatus:
    """Return the separate market-session and observed-data freshness states."""
    return MarketDataStatus(
        market=determine_market_status(settings, now),
        data=determine_data_status(observed_at, settings, now),
        observed_at=_require_aware(observed_at),
    )