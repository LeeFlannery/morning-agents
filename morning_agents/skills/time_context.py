"""Relative time formatting utility."""
from __future__ import annotations

from datetime import datetime, timezone


def relative_time(dt: datetime) -> str:
    """Return a human-friendly relative time string for the given datetime.

    Examples:
        "just now"
        "3 minutes ago"
        "2 hours ago"
        "yesterday"
        "3 days ago"
        "last week"
        "in 2 hours"
        "tomorrow"
    """
    now = datetime.now(tz=timezone.utc)

    # Ensure dt is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    delta = now - dt
    seconds = delta.total_seconds()

    future = seconds < 0
    abs_seconds = abs(seconds)

    minutes = abs_seconds / 60
    hours = abs_seconds / 3600
    days = abs_seconds / 86400

    if abs_seconds < 60:
        return "just now"
    elif minutes < 60:
        m = round(minutes)
        if future:
            return f"in {m} minute{'s' if m != 1 else ''}"
        return f"{m} minute{'s' if m != 1 else ''} ago"
    elif hours < 24:
        h = round(hours)
        if future:
            return f"in {h} hour{'s' if h != 1 else ''}"
        return f"{h} hour{'s' if h != 1 else ''} ago"
    elif days < 2:
        if future:
            return "tomorrow"
        return "yesterday"
    elif days < 7:
        d = round(days)
        if future:
            return f"in {d} days"
        return f"{d} days ago"
    else:
        w = round(days / 7)
        if future:
            return f"in {w} week{'s' if w != 1 else ''}"
        return "last week" if w == 1 else f"{w} weeks ago"
