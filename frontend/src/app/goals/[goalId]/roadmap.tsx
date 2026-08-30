import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { Brand, Button, colors, ErrorState, LoadingState, Screen } from "@/components/ui";
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
  const [savingStepId, setSavingStepId] = useState<string | null>(null);
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

  async function completeStep(step: RoadmapStep) {
    if (!token || step.progress_status !== "current") return;
    setActionError(null);
    setSavingStepId(step.id);
    try {
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/progress`, {
        body: { completed: true },
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Progress could not be saved.");
    } finally {
      setSavingStepId(null);
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
                        <View style={styles.completeButton}>
                          <Button
                            loading={savingStepId === step.id}
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
  completeButton: { marginTop: 18 },
});
