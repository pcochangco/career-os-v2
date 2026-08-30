export type Goal = {
  id: string;
  title: string;
  status: "discovery" | "ready_to_generate" | "roadmap_review" | "active" | "completed";
  created_at: string;
  active_roadmap_id: string | null;
  latest_draft_roadmap_id: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
};

export type RoadmapStep = {
  id: string;
  position: number;
  stable_key: string;
  kind: "learn" | "practice" | "prove";
  title: string;
  objective: string;
  rationale: string;
  action: string;
  completion_condition: string;
  effort_label: string;
  evidence_suggestion: string;
  prerequisite_step_keys: string[];
  resource_queries: string[];
  progress_status: "completed" | "current" | "upcoming" | "blocked";
  completed_at: string | null;
};

export type RoadmapMilestone = {
  id: string;
  position: number;
  title: string;
  outcome: string;
  rationale: string;
  steps: RoadmapStep[];
};

export type QualityIssue = {
  severity: "warning" | "error";
  code: string;
  message: string;
  path: string;
  repair_instruction: string;
};

export type QualityReport = {
  passed: boolean;
  final_score: number;
  structural_score: number;
  critic_score: number;
  repair_attempts: number;
  issues: QualityIssue[];
};

export type Roadmap = {
  id: string;
  goal_id: string;
  version: number;
  status: "draft" | "accepted" | "superseded";
  title: string;
  summary: string;
  goal_outcome: string;
  starting_state_summary: string;
  assumptions: string[];
  schema_version: string;
  generation_source: "fixture" | "openai";
  provider_model: string;
  prompt_version: string;
  quality_report: QualityReport;
  quality_score: number;
  input_tokens: number;
  output_tokens: number;
  generation_duration_ms: number;
  created_at: string;
  accepted_at: string | null;
  completed_steps: number;
  total_steps: number;
  progress_percent: number;
  current_step_id: string | null;
  milestones: RoadmapMilestone[];
};

export type DiscoveryAnswers = {
  desired_outcome: string;
  current_level: string;
  existing_experience: string;
  relevant_constraints: string;
  proof_of_completion: string;
};
