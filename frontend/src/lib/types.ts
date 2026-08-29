export type Goal = {
  id: string;
  title: string;
  status: "discovery" | "ready_to_generate" | "roadmap_review" | "active";
  created_at: string;
  active_roadmap_id: string | null;
  latest_draft_roadmap_id: string | null;
};

export type RoadmapStep = {
  id: string;
  position: number;
  kind: "learn" | "practice" | "prove";
  title: string;
  objective: string;
  action: string;
  completion_condition: string;
  effort_label: string;
};

export type RoadmapMilestone = {
  id: string;
  position: number;
  title: string;
  outcome: string;
  steps: RoadmapStep[];
};

export type Roadmap = {
  id: string;
  goal_id: string;
  version: number;
  status: "draft" | "accepted" | "superseded";
  title: string;
  summary: string;
  generation_source: "fixture" | "ai";
  created_at: string;
  accepted_at: string | null;
  milestones: RoadmapMilestone[];
};

export type DiscoveryAnswers = {
  desired_outcome: string;
  current_level: string;
  existing_experience: string;
  relevant_constraints: string;
  proof_of_completion: string;
};
