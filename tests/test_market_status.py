from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.config.settings import MarketStatusSettings
from app.data.market_status import DataStatus, MarketStatus, determine_data_status, determine_market_status, evaluate_market_data


SETTINGS = MarketStatusSettings(
    live_tick_max_age_seconds=15,
    recent_data_max_age_seconds=300,
    stale_data_max_age_seconds=1800,
    session_timezone="UTC",
    weekly_open_day=6,
    weekly_open_hour=22,
    weekly_close_day=4,
    weekly_close_hour=22,
)
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def test_live_data_is_detected() -> None:
    assert determine_data_status(NOW - timedelta(seconds=15), SETTINGS, NOW) is DataStatus.LIVE


def test_recent_data_is_detected() -> None:
    assert determine_data_status(NOW - timedelta(seconds=16), SETTINGS, NOW) is DataStatus.RECENT


def test_stale_data_is_detected() -> None:
    assert determine_data_status(NOW - timedelta(seconds=301), SETTINGS, NOW) is DataStatus.STALE


def test_unavailable_data_is_detected() -> None:
    assert determine_data_status(None, SETTINGS, NOW) is DataStatus.UNAVAILABLE


def test_open_and_closed_session_states_are_detected() -> None:
    assert determine_market_status(SETTINGS, NOW) is MarketStatus.OPEN
    saturday = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    assert determine_market_status(SETTINGS, saturday) is MarketStatus.CLOSED


def test_closed_market_does_not_promote_live_tick_to_live_market() -> None:
    saturday = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    result = evaluate_market_data(SETTINGS, saturday - timedelta(seconds=2), saturday)
    assert result.market is MarketStatus.CLOSED
    assert result.data is DataStatus.LIVE


def test_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        determine_data_status(datetime(2026, 8, 31, 12, 0), SETTINGS, NOW)


def test_aware_timezones_compare_by_the_same_instant() -> None:
    offset_time = datetime(2026, 8, 31, 14, 0, tzinfo=timezone(timedelta(hours=2)))
    assert determine_data_status(offset_time, SETTINGS, NOW) is DataStatus.LIVE