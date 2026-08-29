import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Brand, colors, ErrorState, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Roadmap, RoadmapStep } from "@/lib/types";

export default function RoadmapRoute() {
  const { roadmapId } = useLocalSearchParams<{ goalId: string; roadmapId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token || !roadmapId) return;
    let active = true;
    apiRequest<Roadmap>(`/roadmaps/${roadmapId}`, { token })
      .then((value) => active && setRoadmap(value))
      .catch((caught) => active && setError(caught instanceof Error ? caught.message : "Roadmap could not load."));
    return () => {
      active = false;
    };
  }, [attempt, roadmapId, token]);

  const currentStep = useMemo<RoadmapStep | null>(() => roadmap?.milestones[0]?.steps[0] ?? null, [roadmap]);

  if (error) return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
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
        <Text style={styles.progressText}>0 of {roadmap.milestones.reduce((total, item) => total + item.steps.length, 0)} steps</Text>
        <Text style={styles.progressPercent}>0%</Text>
      </View>
      <View style={styles.progressTrack}><View style={styles.progressFill} /></View>

      <View style={styles.path}>
        {roadmap.milestones.map((milestone, milestoneIndex) => (
          <View key={milestone.id}>
            <View style={styles.milestoneHeader}>
              <Text style={styles.milestoneLabel}>Milestone {milestone.position}</Text>
              <Text style={styles.milestoneTitle}>{milestone.title}</Text>
            </View>
            {milestone.steps.map((step, stepIndex) => {
              const isCurrent = step.id === currentStep?.id;
              const isLast = milestoneIndex === roadmap.milestones.length - 1 && stepIndex === milestone.steps.length - 1;
              return (
                <View key={step.id} style={styles.pathRow}>
                  <View style={styles.rail}>
                    <View style={[styles.node, isCurrent && styles.nodeCurrent]}>
                      <Text style={[styles.nodeLabel, isCurrent && styles.nodeLabelCurrent]}>
                        {isCurrent ? "▶" : milestoneIndex + stepIndex + 2}
                      </Text>
                    </View>
                    {!isLast ? <View style={styles.connector} /> : null}
                  </View>
                  <View style={[styles.stepCard, isCurrent && styles.currentCard]}>
                    <Text style={[styles.stateLabel, isCurrent && styles.currentState]}>
                      {isCurrent ? "Start here" : "Upcoming"}
                    </Text>
                    <Text style={styles.stepTitle}>{step.title}</Text>
                    {isCurrent ? (
                      <>
                        <Text style={styles.objective}>{step.objective}</Text>
                        <View style={styles.actionBox}>
                          <Text style={styles.actionLabel}>What to do</Text>
                          <Text style={styles.actionText}>{step.action}</Text>
                        </View>
                        <Text style={styles.completeLabel}>Complete when</Text>
                        <Text style={styles.completeText}>{step.completion_condition}</Text>
                        <Text style={styles.effort}>{step.effort_label} · no deadline</Text>
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
  title: { color: colors.ink, fontSize: 29, fontWeight: "800", letterSpacing: -0.5, lineHeight: 35 },
  progressHeader: { flexDirection: "row", justifyContent: "space-between", marginTop: 18 },
  progressText: { color: colors.muted, fontSize: 14 },
  progressPercent: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  progressTrack: { backgroundColor: colors.line, borderRadius: 4, height: 7, marginBottom: 32, marginTop: 9, overflow: "hidden" },
  progressFill: { backgroundColor: colors.forest, height: 7, width: "0%" },
  path: { gap: 30 },
  milestoneHeader: { marginBottom: 15, marginLeft: 68 },
  milestoneLabel: { color: colors.forest, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  milestoneTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", marginTop: 4 },
  pathRow: { alignItems: "stretch", flexDirection: "row", minHeight: 100 },
  rail: { alignItems: "center", width: 54 },
  node: { alignItems: "center", backgroundColor: "#E7ECE8", borderColor: colors.line, borderRadius: 24, borderWidth: 2, height: 48, justifyContent: "center", width: 48 },
  nodeCurrent: { backgroundColor: colors.forest, borderColor: colors.forestDark, shadowColor: colors.forest, shadowOpacity: 0.2, shadowRadius: 8 },
  nodeLabel: { color: colors.muted, fontSize: 13, fontWeight: "800" },
  nodeLabelCurrent: { color: colors.white, fontSize: 15 },
  connector: { backgroundColor: colors.line, flex: 1, minHeight: 28, width: 3 },
  stepCard: { backgroundColor: "#F0F3F0", borderColor: colors.line, borderRadius: 18, borderWidth: 1, flex: 1, marginBottom: 18, marginLeft: 14, padding: 18 },
  currentCard: { backgroundColor: colors.card, borderColor: colors.forest, borderWidth: 2 },
  stateLabel: { color: colors.muted, fontSize: 11, fontWeight: "800", marginBottom: 6, textTransform: "uppercase" },
  currentState: { color: colors.forest },
  stepTitle: { color: colors.ink, fontSize: 18, fontWeight: "800", lineHeight: 24 },
  objective: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 8 },
  actionBox: { backgroundColor: colors.forestSoft, borderRadius: 14, marginTop: 16, padding: 14 },
  actionLabel: { color: colors.forestDark, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  actionText: { color: colors.forestDark, fontSize: 14, lineHeight: 21, marginTop: 5 },
  completeLabel: { color: colors.ink, fontSize: 12, fontWeight: "800", marginTop: 16, textTransform: "uppercase" },
  completeText: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 4 },
  effort: { color: colors.forest, fontSize: 12, fontWeight: "700", marginTop: 14 },
});
