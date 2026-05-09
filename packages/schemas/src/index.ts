// Auto-mirrored from debugra_schemas/models.py
// Keep in sync manually until codegen is added.

export type RunStatus =
  | "pending"
  | "planning"
  | "running"
  | "detecting"
  | "reporting"
  | "complete"
  | "failed";

export type AgentRole =
  | "teacher"
  | "student"
  | "admin"
  | "buyer"
  | "seller"
  | "anonymous";

export type AgentStatus =
  | "pending"
  | "running"
  | "complete"
  | "failed"
  | "aborted";

export type ActionTool =
  | "goto"
  | "click"
  | "fill"
  | "select"
  | "wait_for"
  | "assert_visible"
  | "assert_text"
  | "upload"
  | "screenshot"
  | "scroll"
  | "hover"
  | "press";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type SUT = "lms" | "shop";

export type RunEventType =
  | "run_started"
  | "planning_started"
  | "planning_complete"
  | "agent_spawned"
  | "agent_step"
  | "agent_screenshot"
  | "agent_complete"
  | "agent_failed"
  | "finding_detected"
  | "report_ready"
  | "run_complete"
  | "run_failed"
  | "log_line";

export interface AgentObjective {
  role: AgentRole;
  description: string;
  steps: string[];
  dependencies: string[];
}

export interface PlannerOutput {
  sut: SUT;
  roles: AgentRole[];
  objectives: AgentObjective[];
  success_criteria: string[];
  estimated_steps: number;
}

export interface Run {
  id: string;
  sut: SUT;
  status: RunStatus;
  config: Record<string, unknown>;
  plan: PlannerOutput | null;
  started_at: string | null;
  ended_at: string | null;
  artifact_dir: string | null;
  created_at: string;
}

export interface Agent {
  id: string;
  run_id: string;
  role: AgentRole;
  status: AgentStatus;
  model: string;
  step_count: number;
  trace_path: string | null;
  video_path: string | null;
  started_at: string | null;
  ended_at: string | null;
}

export interface Action {
  id: string;
  agent_id: string;
  step: number;
  observation_summary: string;
  thought: string;
  tool: ActionTool;
  args: Record<string, unknown>;
  result: string | null;
  error: string | null;
  screenshot_path: string | null;
  ts: string;
}

export interface Finding {
  id: string;
  run_id: string;
  agent_id: string | null;
  severity: Severity;
  title: string;
  description: string;
  repro_steps: string[];
  evidence_paths: string[];
  oracle_type: string;
  ground_truth_bug_id: string | null;
  llm_summary: string | null;
  detected_at: string;
}

export interface BugCatalogEntry {
  id: string;
  sut: SUT;
  title: string;
  severity: Severity;
  location: string;
  repro: string;
  detection_oracle: string;
  seeded_in_commit: string | null;
}

export interface RunEvent {
  run_id: string;
  type: RunEventType;
  payload: Record<string, unknown>;
  ts: string;
}
