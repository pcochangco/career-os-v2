import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Body, Brand, Button, colors, ErrorState, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Roadmap } from "@/lib/types";

export default function ReviewRoute() {
  const { goalId, roadmapId } = useLocalSearchParams<{ goalId: string; roadmapId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);
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

  async function acceptRoadmap() {
    if (!token || !roadmapId || !goalId) return;
    try {
      setAccepting(true);
      setError(null);
      await apiRequest<Roadmap>(`/roadmaps/${roadmapId}/accept`, { method: "POST", token });
      router.replace(`/goals/${goalId}/roadmap?roadmapId=${roadmapId}` as never);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Roadmap could not be accepted.");
      setAccepting(false);
    }
  }

  if (error && !roadmap) {
    return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
  }
  if (!roadmap) return <LoadingState label="Preparing your roadmap…" />;

  return (
    <Screen>
      <Brand />
      <Text style={styles.eyebrow}>Your first roadmap</Text>
      <Heading>{roadmap.title}</Heading>
      <Body>{roadmap.summary}</Body>
      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>Built as a clear starting path</Text>
        <Text style={styles.noticeBody}>You can review every stage now. Accepting it makes this your active roadmap.</Text>
      </View>
      <View style={styles.milestones}>
        {roadmap.milestones.map((milestone) => (
          <View key={milestone.id} style={styles.milestone}>
            <Text style={styles.milestoneNumber}>Milestone {milestone.position}</Text>
            <Text style={styles.milestoneTitle}>{milestone.title}</Text>
            <Text style={styles.outcome}>{milestone.outcome}</Text>
            <View style={styles.steps}>
              {milestone.steps.map((step) => (
                <View key={step.id} style={styles.stepRow}>
                  <View style={styles.stepDot} />
                  <View style={styles.stepCopy}>
                    <Text style={styles.stepTitle}>{step.title}</Text>
                    <Text style={styles.stepMeta}>{step.kind} · {step.effort_label}</Text>
                  </View>
                </View>
              ))}
            </View>
          </View>
        ))}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button loading={accepting} onPress={() => void acceptRoadmap()}>Use this roadmap</Button>
    </Screen>
  );
}

const styles = StyleSheet.create({
  eyebrow: { color: colors.forest, fontSize: 14, fontWeight: "800", marginBottom: 12 },
  notice: { backgroundColor: colors.forestSoft, borderRadius: 18, marginBottom: 24, padding: 18 },
  noticeTitle: { color: colors.forestDark, fontSize: 16, fontWeight: "800", marginBottom: 5 },
  noticeBody: { color: colors.forestDark, fontSize: 14, lineHeight: 21 },
  milestones: { gap: 16, marginBottom: 24 },
  milestone: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 20, borderWidth: 1, padding: 20 },
  milestoneNumber: { color: colors.forest, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  milestoneTitle: { color: colors.ink, fontSize: 21, fontWeight: "800", marginTop: 6 },
  outcome: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 7 },
  steps: { gap: 14, marginTop: 18 },
  stepRow: { alignItems: "flex-start", flexDirection: "row", gap: 12 },
  stepDot: { backgroundColor: colors.forest, borderRadius: 7, height: 14, marginTop: 4, width: 14 },
  stepCopy: { flex: 1 },
  stepTitle: { color: colors.ink, fontSize: 15, fontWeight: "700", lineHeight: 21 },
  stepMeta: { color: colors.muted, fontSize: 12, marginTop: 3, textTransform: "capitalize" },
  error: { color: "#A43E38", fontSize: 14, marginBottom: 14 },
});
