from __future__ import annotations

from morning_agents.contracts.models import Severity
from morning_agents.skills.semver import VersionJump

JUMP_TO_SEVERITY: dict[str, Severity] = {
    "patch": Severity.info,
    "minor": Severity.warning,
    "major": Severity.action_needed,
    "current": Severity.info,
    "not_installed": Severity.warning,
    "unknown": Severity.warning,
}


def from_version_jump(jump: str) -> Severity:
    return JUMP_TO_SEVERITY.get(jump, Severity.warning)
