from __future__ import annotations

from typing import Literal

import semver

VersionJump = Literal["patch", "minor", "major", "unknown"]


def classify(current: str, latest: str) -> VersionJump:
    """Return the version jump type between two semver strings."""
    try:
        cur = semver.Version.parse(current.lstrip("v"))
        lat = semver.Version.parse(latest.lstrip("v"))
    except ValueError:
        return "unknown"

    if lat.major > cur.major:
        return "major"
    if lat.minor > cur.minor:
        return "minor"
    if lat.patch > cur.patch:
        return "patch"
    return "unknown"
