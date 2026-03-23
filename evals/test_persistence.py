"""
Unit tests for morning_agents.persistence.
No API calls — uses tmp_path fixture and in-memory models.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    BriefingConfig,
    BriefingOutput,
    BriefingSummary,
    FindingSummary,
)
from morning_agents.persistence import (
    get_latest_run,
    list_runs,
    load_briefing,
    persist_briefing,
)


def _make_briefing(briefing_id: str = "brief-2026-01-01-120000") -> BriefingOutput:
    now = datetime.now(tz=timezone.utc)
    return BriefingOutput(
        version="0.1.0",
        briefing_id=briefing_id,
        generated_at=now,
        duration_ms=1000,
        agent_results=[],
        cross_references=[],
        summary=BriefingSummary(
            agents_run=0,
            agents_succeeded=0,
            agents_failed=0,
            total_findings=0,
            by_severity={},
            mcp_servers_used=0,
        ),
        config=BriefingConfig(
            agents_enabled=[],
            quiet_mode=False,
        ),
    )


def test_briefing_round_trip(tmp_path):
    """Serialize then deserialize a BriefingOutput, check equality."""
    briefing = _make_briefing("brief-2026-01-01-120000")
    filepath = persist_briefing(briefing, runs_dir=tmp_path)
    loaded = load_briefing(filepath)
    assert loaded.briefing_id == briefing.briefing_id
    assert loaded.version == briefing.version
    assert loaded.duration_ms == briefing.duration_ms
    assert loaded.summary.agents_run == briefing.summary.agents_run
    assert loaded.config.quiet_mode == briefing.config.quiet_mode


def test_persist_creates_file(tmp_path):
    """persist_briefing writes file with correct name."""
    briefing = _make_briefing("brief-2026-03-13-093000")
    filepath = persist_briefing(briefing, runs_dir=tmp_path)
    assert filepath.exists()
    assert filepath.name == "brief-2026-03-13-093000.json"
    assert filepath.parent == tmp_path


def test_list_runs_newest_first(tmp_path):
    """Write 3 files with different IDs, verify newest-first order."""
    ids = [
        "brief-2026-01-01-080000",
        "brief-2026-02-15-090000",
        "brief-2026-03-13-100000",
    ]
    for bid in ids:
        persist_briefing(_make_briefing(bid), runs_dir=tmp_path)

    files = list_runs(runs_dir=tmp_path)
    assert len(files) == 3
    # Sorted reverse alphabetically — newest ID string first
    names = [f.name for f in files]
    assert names == sorted([f"{bid}.json" for bid in ids], reverse=True)


def test_get_latest_run(tmp_path):
    """get_latest_run returns the most recent briefing."""
    ids = [
        "brief-2026-01-01-080000",
        "brief-2026-03-13-100000",
        "brief-2026-02-15-090000",
    ]
    for bid in ids:
        persist_briefing(_make_briefing(bid), runs_dir=tmp_path)

    latest = get_latest_run(runs_dir=tmp_path)
    assert latest is not None
    assert latest.briefing_id == "brief-2026-03-13-100000"


def test_get_latest_run_empty(tmp_path):
    """get_latest_run returns None when runs_dir is empty."""
    result = get_latest_run(runs_dir=tmp_path)
    assert result is None
