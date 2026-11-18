import { RoadmapStep } from "@/lib/types";

export const stateLabels: Record<RoadmapStep["progress_status"], string> = {
  completed: "Completed",
  current: "Continue here",
  upcoming: "Upcoming",
  blocked: "Prerequisite needed",
  locked: "Premium unlock",
};
export const resourceRefreshCooldownMs = 12_000;
export const resourceUndoWindowMs = 6_000;

export function learningRecordFor(step: RoadmapStep | null): string {
  if (!step) return "";
  // Older records kept a separate summary; fold it into the notes the user edits.
  return [step.notes, step.evidence_summary]
    .map((value) => value.trim())
    .filter(Boolean)
    .join("\n\n");
}

export const AUTOSAVE_DELAY_MS = 1200;

export function isValidEvidenceLink(value: string): boolean {
  const link = value.trim();
  return !link || /^https?:\/\/[^\s/]+\.[^\s]+/i.test(link);
}
