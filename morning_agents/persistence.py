from __future__ import annotations

import json
from pathlib import Path

from morning_agents.contracts.models import BriefingOutput

RUNS_DIR = Path("runs")


def persist_briefing(output: BriefingOutput, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(exist_ok=True)
    filename = f"{output.briefing_id}.json"
    filepath = runs_dir / filename
    filepath.write_text(output.model_dump_json(indent=2))
    return filepath


def load_briefing(filepath: Path) -> BriefingOutput:
    return BriefingOutput.model_validate_json(filepath.read_text())


def list_runs(runs_dir: Path = RUNS_DIR, limit: int = 20) -> list[Path]:
    if not runs_dir.exists():
        return []
    files = sorted(runs_dir.glob("brief-*.json"), reverse=True)
    return files[:limit]


def get_latest_run(runs_dir: Path = RUNS_DIR) -> BriefingOutput | None:
    files = list_runs(runs_dir, limit=1)
    if not files:
        return None
    return load_briefing(files[0])
