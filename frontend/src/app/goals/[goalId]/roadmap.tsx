import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import {
  Brand,
  Button,
  colors,
  ErrorState,
  Field,
  LoadingState,
  Screen,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Roadmap, RoadmapStep } from "@/lib/types";

const stateLabels: Record<RoadmapStep["progress_status"], string> = {
  completed: "Completed",
  current: "Continue here",
  upcoming: "Upcoming",
  blocked: "Prerequisite needed",
};

export default function RoadmapRoute() {
  const { roadmapId } = useLocalSearchParams<{ goalId: string; roadmapId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState<"work" | "completion" | null>(null);
  const [notes, setNotes] = useState("");
  const [evidenceSummary, setEvidenceSummary] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [completionConfirmed, setCompletionConfirmed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token || !roadmapId) return;
    let active = true;
    setError(null);
    apiRequest<Roadmap>(`/roadmaps/${roadmapId}`, { token })
      .then((value) => active && setRoadmap(value))
      .catch(
        (caught) =>
          active &&
          setError(caught instanceof Error ? caught.message : "Roadmap could not load."),
      );
    return () => {
      active = false;
    };
  }, [attempt, roadmapId, token]);

  const stepNumberById = useMemo(() => {
    const positions = new Map<string, number>();
    let position = 0;
    for (const milestone of roadmap?.milestones ?? []) {
      for (const step of milestone.steps) {
        position += 1;
        positions.set(step.id, position);
      }
    }
    return positions;
  }, [roadmap]);

  const currentStep = useMemo(
    () =>
      roadmap?.milestones
        .flatMap((milestone) => milestone.steps)
        .find((step) => step.id === roadmap.current_step_id) ?? null,
    [roadmap],
  );

  useEffect(() => {
    setNotes(currentStep?.notes ?? "");
    setEvidenceSummary(currentStep?.evidence_summary ?? "");
    setEvidenceUrl(currentStep?.evidence_url ?? "");
    setCompletionConfirmed(false);
  }, [currentStep?.id]);

  const workDirty = Boolean(
    currentStep &&
      (notes.trim() !== currentStep.notes ||
        evidenceSummary.trim() !== currentStep.evidence_summary ||
        evidenceUrl.trim() !== currentStep.evidence_url),
  );

  const workPayload = {
    evidence_summary: evidenceSummary,
    evidence_url: evidenceUrl,
    notes,
  };

  async function saveStepWork(step: RoadmapStep) {
    if (!token || step.progress_status !== "current") return;
    setActionError(null);
    setSavingAction("work");
    try {
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Your work could not be saved.");
    } finally {
      setSavingAction(null);
    }
  }

  async function completeStep(step: RoadmapStep) {
    if (!token || step.progress_status !== "current" || !completionConfirmed) return;
    setActionError(null);
    setSavingAction("completion");
    try {
      const saved = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      setRoadmap(saved);
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/progress`, {
        body: { completed: true, completion_confirmed: true },
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Progress could not be saved.");
    } finally {
      setSavingAction(null);
    }
  }

  function openResourceSearch(query: string) {
    void Linking.openURL(`https://www.google.com/search?q=${encodeURIComponent(query)}`);
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
  }
  if (!roadmap) return <LoadingState />;

  return (
    <Screen>
      <View style={styles.topBar}>
        <Brand />
        <Pressable accessibilityRole="button" onPress={() => router.push("/goals" as never)}>
          <Text style={styles.goalsLink}>All goals</Text>
        </Pressable>
      </View>
      <Text style={styles.title}>{roadmap.title}</Text>
      <View style={styles.progressHeader}>
        <Text style={styles.progressText}>
          {roadmap.completed_steps} of {roadmap.total_steps} steps
        </Text>
        <Text style={styles.progressPercent}>{roadmap.progress_percent}%</Text>
      </View>
      <View style={styles.progressTrack}>
        <View
          style={[
            styles.progressFill,
            { width: `${roadmap.progress_percent}%` as `${number}%` },
          ]}
        />
      </View>

      {roadmap.current_step_id === null ? (
        <View style={styles.goalComplete}>
          <Text style={styles.goalCompleteEyebrow}>Goal complete</Text>
          <Text style={styles.goalCompleteTitle}>You finished the full roadmap.</Text>
          <Text style={styles.goalCompleteBody}>
            Every step remains below so you can return to the work and materials you used.
          </Text>
        </View>
      ) : null}

      {actionError ? <Text style={styles.actionError}>{actionError}</Text> : null}

      <View style={styles.path}>
        {roadmap.milestones.map((milestone, milestoneIndex) => (
          <View key={milestone.id}>
            <View style={styles.milestoneHeader}>
              <Text style={styles.milestoneLabel}>Milestone {milestone.position}</Text>
              <Text style={styles.milestoneTitle}>{milestone.title}</Text>
            </View>
            {milestone.steps.map((step, stepIndex) => {
              const isCurrent = step.progress_status === "current";
              const isCompleted = step.progress_status === "completed";
              const isBlocked = step.progress_status === "blocked";
              const isLast =
                milestoneIndex === roadmap.milestones.length - 1 &&
                stepIndex === milestone.steps.length - 1;
              const nodeLabel = isCompleted
                ? "✓"
                : isCurrent
                  ? "▶"
                  : isBlocked
                    ? "·"
                    : String(stepNumberById.get(step.id));

              return (
                <View key={step.id} style={styles.pathRow}>
                  <View style={styles.rail}>
                    <View
                      style={[
                        styles.node,
                        isCurrent && styles.nodeCurrent,
                        isCompleted && styles.nodeCompleted,
                        isBlocked && styles.nodeBlocked,
                      ]}
                    >
                      <Text
                        style={[
                          styles.nodeLabel,
                          (isCurrent || isCompleted) && styles.nodeLabelActive,
                        ]}
                      >
                        {nodeLabel}
                      </Text>
                    </View>
                    {!isLast ? (
                      <View style={[styles.connector, isCompleted && styles.connectorCompleted]} />
                    ) : null}
                  </View>
                  <View
                    style={[
                      styles.stepCard,
                      isCurrent && styles.currentCard,
                      isCompleted && styles.completedCard,
                      isBlocked && styles.blockedCard,
                    ]}
                  >
                    <Text style={[styles.stateLabel, isCurrent && styles.currentState]}>
                      {stateLabels[step.progress_status]}
                    </Text>
                    <Text style={styles.stepTitle}>{step.title}</Text>
                    {isCompleted &&
                    (step.notes || step.evidence_summary || step.evidence_url) ? (
                      <View style={styles.savedWork}>
                        <Text style={styles.savedWorkLabel}>Your saved work</Text>
                        {step.notes ? <Text style={styles.savedWorkText}>{step.notes}</Text> : null}
                        {step.evidence_summary ? (
                          <Text style={styles.savedWorkText}>{step.evidence_summary}</Text>
                        ) : null}
                        {step.evidence_url ? (
                          <Pressable
                            accessibilityRole="link"
                            onPress={() => void Linking.openURL(step.evidence_url)}
                          >
                            <Text style={styles.savedWorkLink}>Open evidence ↗</Text>
                          </Pressable>
                        ) : null}
                      </View>
                    ) : null}
                    {isCurrent ? (
                      <>
                        <Text style={styles.objective}>{step.objective}</Text>
                        <View style={styles.actionBox}>
                          <Text style={styles.actionLabel}>Do this now</Text>
                          <Text style={styles.actionText}>{step.action}</Text>
                        </View>
                        {step.resource_queries.length ? (
                          <View style={styles.resources}>
                            <Text style={styles.resourceLabel}>Find useful material</Text>
                            {step.resource_queries.map((query) => (
                              <Pressable
                                accessibilityRole="link"
                                key={query}
                                onPress={() => openResourceSearch(query)}
                                style={({ pressed }) => [
                                  styles.resourceLink,
                                  pressed && styles.resourceLinkPressed,
                                ]}
                              >
                                <Text style={styles.resourceLinkText}>Search “{query}” ↗</Text>
                              </Pressable>
                            ))}
                          </View>
                        ) : null}
                        <Text style={styles.completeLabel}>Complete when</Text>
                        <Text style={styles.completeText}>{step.completion_condition}</Text>
                        {step.evidence_suggestion ? (
                          <Text style={styles.evidence}>Keep: {step.evidence_suggestion}</Text>
                        ) : null}
                        <Text style={styles.effort}>{step.effort_label} · no deadline</Text>
                        <View style={styles.workSection}>
                          <Text style={styles.workTitle}>Your learning record</Text>
                          <Text style={styles.workIntro}>
                            Keep anything useful for returning to this work or showing it later.
                          </Text>
                          <Field
                            accessibilityLabel="Notes or reflections"
                            maxLength={4000}
                            multiline
                            onChangeText={setNotes}
                            placeholder="Notes or reflections (optional)"
                            style={styles.workField}
                            value={notes}
                          />
                          <Field
                            accessibilityLabel="Output or evidence summary"
                            maxLength={1000}
                            multiline
                            onChangeText={setEvidenceSummary}
                            placeholder="What did you produce? (optional)"
                            style={styles.workField}
                            value={evidenceSummary}
                          />
                          <Field
                            accessibilityLabel="Evidence link"
                            autoCapitalize="none"
                            autoCorrect={false}
                            keyboardType="url"
                            maxLength={2048}
                            onChangeText={setEvidenceUrl}
                            placeholder="https://… evidence link (optional)"
                            style={styles.linkField}
                            value={evidenceUrl}
                          />
                          <View style={styles.saveRow}>
                            <View style={styles.saveButton}>
                              <Button
                                disabled={!workDirty || savingAction !== null}
                                loading={savingAction === "work"}
                                onPress={() => void saveStepWork(step)}
                                secondary
                              >
                                Save record
                              </Button>
                            </View>
                            {!workDirty && step.work_updated_at ? (
                              <Text style={styles.savedLabel}>Saved</Text>
                            ) : null}
                          </View>
                        </View>
                        <Pressable
                          accessibilityRole="checkbox"
                          accessibilityState={{ checked: completionConfirmed }}
                          onPress={() => setCompletionConfirmed((value) => !value)}
                          style={styles.confirmationRow}
                        >
                          <View
                            style={[
                              styles.checkbox,
                              completionConfirmed && styles.checkboxChecked,
                            ]}
                          >
                            {completionConfirmed ? (
                              <Text style={styles.checkboxMark}>✓</Text>
                            ) : null}
                          </View>
                          <Text style={styles.confirmationText}>
                            I met this step’s completion condition.
                          </Text>
                        </Pressable>
                        <View style={styles.completeButton}>
                          <Button
                            disabled={!completionConfirmed || savingAction !== null}
                            loading={savingAction === "completion"}
                            onPress={() => void completeStep(step)}
                          >
                            Complete this step
                          </Button>
                        </View>
                      </>
                    ) : null}
                  </View>
                </View>
              );
            })}
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between" },
  goalsLink: { color: colors.forest, fontSize: 15, fontWeight: "800", paddingVertical: 2 },
  title: {
    color: colors.ink,
    fontSize: 29,
    fontWeight: "800",
    letterSpacing: -0.5,
    lineHeight: 35,
  },
  progressHeader: { flexDirection: "row", justifyContent: "space-between", marginTop: 18 },
  progressText: { color: colors.muted, fontSize: 14 },
  progressPercent: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  progressTrack: {
    backgroundColor: colors.line,
    borderRadius: 4,
    height: 7,
    marginBottom: 32,
    marginTop: 9,
    overflow: "hidden",
  },
  progressFill: { backgroundColor: colors.forest, borderRadius: 4, height: 7 },
  goalComplete: {
    backgroundColor: colors.forestSoft,
    borderRadius: 18,
    marginBottom: 28,
    padding: 20,
  },
  goalCompleteEyebrow: {
    color: colors.forest,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  goalCompleteTitle: { color: colors.ink, fontSize: 21, fontWeight: "800", marginTop: 6 },
  goalCompleteBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 6 },
  actionError: { color: "#A13B32", fontSize: 14, marginBottom: 22 },
  path: { gap: 30 },
  milestoneHeader: { marginBottom: 15, marginLeft: 68 },
  milestoneLabel: {
    color: colors.forest,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  milestoneTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", marginTop: 4 },
  pathRow: { alignItems: "stretch", flexDirection: "row", minHeight: 100 },
  rail: { alignItems: "center", width: 54 },
  node: {
    alignItems: "center",
    backgroundColor: "#E7ECE8",
    borderColor: colors.line,
    borderRadius: 24,
    borderWidth: 2,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  nodeCurrent: {
    backgroundColor: colors.forest,
    borderColor: colors.forestDark,
    shadowColor: colors.forest,
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  nodeCompleted: { backgroundColor: colors.forest, borderColor: colors.forest },
  nodeBlocked: { opacity: 0.62 },
  nodeLabel: { color: colors.muted, fontSize: 13, fontWeight: "800" },
  nodeLabelActive: { color: colors.white, fontSize: 15 },
  connector: { backgroundColor: colors.line, flex: 1, minHeight: 28, width: 3 },
  connectorCompleted: { backgroundColor: colors.forest },
  stepCard: {
    backgroundColor: "#F0F3F0",
    borderColor: colors.line,
    borderRadius: 18,
    borderWidth: 1,
    flex: 1,
    marginBottom: 18,
    marginLeft: 14,
    padding: 18,
  },
  currentCard: { backgroundColor: colors.card, borderColor: colors.forest, borderWidth: 2 },
  completedCard: { backgroundColor: colors.card },
  blockedCard: { opacity: 0.68 },
  stateLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "800",
    marginBottom: 6,
    textTransform: "uppercase",
  },
  currentState: { color: colors.forest },
  stepTitle: { color: colors.ink, fontSize: 18, fontWeight: "800", lineHeight: 24 },
  objective: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 8 },
  actionBox: { backgroundColor: colors.forestSoft, borderRadius: 14, marginTop: 16, padding: 14 },
  actionLabel: {
    color: colors.forestDark,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  actionText: { color: colors.forestDark, fontSize: 14, lineHeight: 21, marginTop: 5 },
  resources: { gap: 8, marginTop: 16 },
  resourceLabel: {
    color: colors.ink,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  resourceLink: {
    backgroundColor: colors.background,
    borderColor: colors.line,
    borderRadius: 12,
    borderWidth: 1,
    minHeight: 44,
    paddingHorizontal: 13,
    paddingVertical: 11,
  },
  resourceLinkPressed: { opacity: 0.72 },
  resourceLinkText: { color: colors.forest, fontSize: 13, fontWeight: "700", lineHeight: 19 },
  completeLabel: {
    color: colors.ink,
    fontSize: 12,
    fontWeight: "800",
    marginTop: 16,
    textTransform: "uppercase",
  },
  completeText: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 4 },
  evidence: { color: colors.muted, fontSize: 13, fontStyle: "italic", marginTop: 12 },
  effort: { color: colors.forest, fontSize: 12, fontWeight: "700", marginTop: 14 },
  savedWork: {
    backgroundColor: colors.forestSoft,
    borderRadius: 12,
    gap: 6,
    marginTop: 13,
    padding: 13,
  },
  savedWorkLabel: {
    color: colors.forestDark,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  savedWorkText: { color: colors.forestDark, fontSize: 13, lineHeight: 19 },
  savedWorkLink: { color: colors.forest, fontSize: 13, fontWeight: "800", marginTop: 2 },
  workSection: {
    borderTopColor: colors.line,
    borderTopWidth: 1,
    marginTop: 20,
    paddingTop: 18,
  },
  workTitle: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  workIntro: { color: colors.muted, fontSize: 13, lineHeight: 19, marginBottom: 13, marginTop: 4 },
  workField: { fontSize: 15, lineHeight: 22, marginBottom: 10, minHeight: 94 },
  linkField: { fontSize: 15, marginBottom: 10, minHeight: 50 },
  saveRow: { alignItems: "center", flexDirection: "row", gap: 12 },
  saveButton: { minWidth: 154 },
  savedLabel: { color: colors.forest, fontSize: 13, fontWeight: "800" },
  confirmationRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    marginTop: 20,
    minHeight: 44,
  },
  checkbox: {
    alignItems: "center",
    backgroundColor: colors.card,
    borderColor: colors.muted,
    borderRadius: 7,
    borderWidth: 2,
    height: 25,
    justifyContent: "center",
    width: 25,
  },
  checkboxChecked: { backgroundColor: colors.forest, borderColor: colors.forest },
  checkboxMark: { color: colors.white, fontSize: 16, fontWeight: "900" },
  confirmationText: { color: colors.ink, flex: 1, fontSize: 14, fontWeight: "700", lineHeight: 20 },
  completeButton: { marginTop: 18 },
});
