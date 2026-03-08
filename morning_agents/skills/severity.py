from __future__ import annotations

from morning_agents.contracts.models import Severity
from morning_agents.skills.semver import VersionJump

JUMP_TO_SEVERITY: dict[VersionJump, Severity] = {
    "patch": Severity.info,
    "minor": Severity.warning,
    "major": Severity.action_needed,
    "unknown": Severity.warning,
}


def from_version_jump(jump: VersionJump) -> Severity:
    return JUMP_TO_SEVERITY[jump]
