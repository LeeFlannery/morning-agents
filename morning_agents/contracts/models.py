from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime:
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class AgentResult(BaseModel):
    agent_name: str
    agent_display_name: str
    status: AgentStatus
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    findings: list[Finding] = Field(default_factory=list)
    summary: Optional[FindingSummary] = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    error: Optional[str] = None

    @field_validator("started_at", "completed_at", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    def compute_summary(self) -> FindingSummary:
        """Build a FindingSummary from the current findings list."""
        by_severity: dict[str, int] = {s.value: 0 for s in Severity}
        for finding in self.findings:
            by_severity[finding.severity.value] += 1
        # Drop zero-count severities to keep output clean (matches spec style)
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
    timestamp: datetime

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class BriefingOutput(BaseModel):
    version: str
    briefing_id: str
    generated_at: datetime
    duration_ms: int
    agent_results: list[AgentResult] = Field(default_factory=list)
    cross_references: list[CrossReference] = Field(default_factory=list)
    summary: BriefingSummary
    config: BriefingConfig

    @field_validator("generated_at", mode="before")
    @classmethod
    def ensure_timezone(cls, v: Any) -> datetime:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    @classmethod
    def generate_id(cls, dt: Optional[datetime] = None) -> str:
        """Return a briefing ID string in the form 'brief-YYYY-MM-DD-HHMMSS'.

        If *dt* is not supplied, the current UTC time is used.
        """
        if dt is None:
            dt = datetime.now(tz=timezone.utc)
        return dt.strftime("brief-%Y-%m-%d-%H%M%S")
