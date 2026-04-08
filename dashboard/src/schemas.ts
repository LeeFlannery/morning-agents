import { z } from "zod";

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export const Severity = z.enum(["info", "warning", "action_needed"]);
export type Severity = z.infer<typeof Severity>;

export const AgentStatus = z.enum(["success", "partial", "error"]);
export type AgentStatus = z.infer<typeof AgentStatus>;

// ---------------------------------------------------------------------------
// Supporting models
// ---------------------------------------------------------------------------

export const ToolCall = z.object({
  tool: z.string(),
  server: z.string(),
  duration_ms: z.number(),
  success: z.boolean(),
});
export type ToolCall = z.infer<typeof ToolCall>;

export const FindingSummary = z.object({
  total: z.number(),
  by_severity: z.record(z.string(), z.number()).default({}),
});
export type FindingSummary = z.infer<typeof FindingSummary>;

export const BriefingSummary = z.object({
  agents_run: z.number(),
  agents_succeeded: z.number(),
  agents_failed: z.number(),
  total_findings: z.number(),
  by_severity: z.record(z.string(), z.number()).default({}),
  mcp_servers_used: z.number(),
});
export type BriefingSummary = z.infer<typeof BriefingSummary>;

export const BriefingConfig = z.object({
  agents_enabled: z.array(z.string()),
  quiet_mode: z.boolean().default(false),
});
export type BriefingConfig = z.infer<typeof BriefingConfig>;

export const ExecutionMeta = z.object({
  stages: z.array(z.array(z.string())),
  dependency_graph: z.record(z.string(), z.array(z.string())),
  retries: z.record(z.string(), z.number()).default({}),
});
export type ExecutionMeta = z.infer<typeof ExecutionMeta>;

// ---------------------------------------------------------------------------
// Core models
// ---------------------------------------------------------------------------

export const Finding = z.object({
  id: z.string(),
  source_agent: z.string(),
  category: z.string(),
  severity: Severity,
  title: z.string(),
  detail: z.string(),
  metadata: z.record(z.string(), z.unknown()).default({}),
  timestamp: z.string(),
});
export type Finding = z.infer<typeof Finding>;

export const AgentResult = z.object({
  agent_name: z.string(),
  agent_display_name: z.string(),
  status: AgentStatus,
  started_at: z.string(),
  completed_at: z.string(),
  duration_ms: z.number(),
  findings: z.array(Finding).default([]),
  summary: FindingSummary.nullable().optional(),
  tool_calls: z.array(ToolCall).default([]),
  error: z.string().nullable().optional(),
});
export type AgentResult = z.infer<typeof AgentResult>;

export const CrossReference = z.object({
  id: z.string(),
  severity: Severity,
  title: z.string(),
  detail: z.string(),
  source_findings: z.array(z.string()).default([]),
  source_agents: z.array(z.string()).default([]),
  timestamp: z.string(),
});
export type CrossReference = z.infer<typeof CrossReference>;

export const BriefingOutput = z.object({
  version: z.string(),
  briefing_id: z.string(),
  generated_at: z.string(),
  duration_ms: z.number(),
  agent_results: z.array(AgentResult).default([]),
  cross_references: z.array(CrossReference).default([]),
  summary: BriefingSummary,
  execution: ExecutionMeta.nullable().optional(),
  config: BriefingConfig,
});
export type BriefingOutput = z.infer<typeof BriefingOutput>;

// ---------------------------------------------------------------------------
// Manifest (Vite plugin response)
// ---------------------------------------------------------------------------

export const RunManifestEntry = z.object({
  id: z.string(),
  file: z.string(),
  generated_at: z.string(),
  duration_ms: z.number(),
  agents_run: z.number(),
  agents_succeeded: z.number(),
  agents_failed: z.number(),
  total_findings: z.number(),
  by_severity: z.record(z.string(), z.number()).default({}),
  cross_reference_count: z.number(),
});
export type RunManifestEntry = z.infer<typeof RunManifestEntry>;
