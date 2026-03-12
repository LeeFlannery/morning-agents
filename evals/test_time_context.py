"""Unit tests for morning_agents.skills.time_context.relative_time."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from morning_agents.skills.time_context import relative_time


def _ago(seconds: float) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(seconds=seconds)


def _from_now(seconds: float) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)


def test_just_now():
    assert relative_time(_ago(5)) == "just now"
    assert relative_time(_ago(0)) == "just now"


def test_3_minutes_ago():
    result = relative_time(_ago(3 * 60))
    assert result == "3 minutes ago"


def test_2_hours_ago():
    result = relative_time(_ago(2 * 3600))
    assert result == "2 hours ago"


def test_yesterday():
    result = relative_time(_ago(25 * 3600))
    assert result == "yesterday"


def test_3_days_ago():
    result = relative_time(_ago(3 * 86400))
    assert result == "3 days ago"


def test_last_week():
    result = relative_time(_ago(7 * 86400))
    assert result == "last week"


def test_in_2_hours():
    result = relative_time(_from_now(2 * 3600))
    assert result == "in 2 hours"


def test_tomorrow():
    result = relative_time(_from_now(25 * 3600))
    assert result == "tomorrow"
