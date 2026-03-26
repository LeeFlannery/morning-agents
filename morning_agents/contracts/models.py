from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    action_needed = "action_needed"


class AgentStatus(str, Enum):
    success = "success"
    partial = "partial"
    error = "error"


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


def _ensure_tz(v: Any) -> datetime:
    if isinstance(v, str):
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


AwareDatetime = Annotated[datetime, BeforeValidator(_ensure_tz)]


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


class ToolCall(BaseModel):
    tool: str
    server: str
    duration_ms: int
    success: bool


class FindingSummary(BaseModel):
    total: int
    by_severity: dict[str, int]


class BriefingSummary(BaseModel):
    agents_run: int
    agents_succeeded: int
    agents_failed: int
    total_findings: int
    by_severity: dict[str, int]
    mcp_servers_used: int


class BriefingConfig(BaseModel):
    agents_enabled: list[str]
    quiet_mode: bool = False


class ExecutionMeta(BaseModel):
    stages: list[list[str]]
    dependency_graph: dict[str, list[str]]
    retries: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    id: str
    source_agent: str
    category: str
    severity: Severity
    title: str
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: AwareDatetime


class AgentResult(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    agent_name: str
    agent_display_name: str
    status: AgentStatus
    started_at: AwareDatetime
    completed_at: AwareDatetime
    duration_ms: int
    findings: list[Finding] = Field(default_factory=list)
    summary: Optional[FindingSummary] = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    error: Optional[str] = None

    def compute_summary(self) -> FindingSummary:
        by_severity: dict[str, int] = {s.value: 0 for s in Severity}
        for finding in self.findings:
            by_severity[finding.severity.value] += 1
        by_severity = {k: v for k, v in by_severity.items() if v > 0}
        summary = FindingSummary(total=len(self.findings), by_severity=by_severity)
        self.summary = summary
        return summary


class CrossReference(BaseModel):
    id: str
    severity: Severity
    title: str
    detail: str
    source_findings: list[str] = Field(default_factory=list)
    source_agents: list[str] = Field(default_factory=list)
    timestamp: AwareDatetime


class BriefingOutput(BaseModel):
    version: str
    briefing_id: str
    generated_at: AwareDatetime
    duration_ms: int
    agent_results: list[AgentResult] = Field(default_factory=list)
    cross_references: list[CrossReference] = Field(default_factory=list)
    summary: BriefingSummary
    execution: Optional[ExecutionMeta] = None
    config: BriefingConfig

    @classmethod
    def generate_id(cls, dt: Optional[datetime] = None) -> str:
        if dt is None:
            dt = datetime.now(tz=timezone.utc)
        return dt.strftime("brief-%Y-%m-%d-%H%M%S")
