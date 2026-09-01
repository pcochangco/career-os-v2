import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Body, Brand, Button, ErrorState, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";
import { ThemeColors, useTheme } from "@/lib/theme";

function routeForGoal(goal: Goal): string {
  if (goal.active_roadmap_id) return `/goals/${goal.id}/roadmap?roadmapId=${goal.active_roadmap_id}`;
  if (goal.latest_draft_roadmap_id) return `/goals/${goal.id}/review?roadmapId=${goal.latest_draft_roadmap_id}`;
  return `/goals/${goal.id}/discovery`;
}

export default function GoalsRoute() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const router = useRouter();
  const { token } = useSession();
  const [goals, setGoals] = useState<Goal[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token) return;
    let active = true;
    apiRequest<Goal[]>("/goals", { token })
      .then((value) => active && setGoals(value))
      .catch((caught) => active && setError(caught instanceof Error ? caught.message : "Goals could not load."));
    return () => {
      active = false;
    };
  }, [attempt, token]);

  if (!token || !goals) {
    if (error) return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
    return <LoadingState label="Loading your goals…" />;
  }

  return (
    <Screen>
      <Brand />
      <Pressable accessibilityRole="button" onPress={() => router.push("/settings" as never)} style={styles.appearanceLink}>
        <Text style={styles.appearanceText}>Settings</Text>
      </Pressable>
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Heading>Your goals</Heading>
          <Body>Choose a path and continue exactly where you left it.</Body>
        </View>
        <View style={styles.newGoalButton}>
          <Button onPress={() => router.push("/goals/new" as never)}>New goal</Button>
        </View>
      </View>
      <View style={styles.list}>
        {goals.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={styles.emptyTitle}>Start with one meaningful goal.</Text>
            <Text style={styles.emptyBody}>
              CareerOS will shape a clear path, then keep your next step ready.
            </Text>
            <Button onPress={() => router.push("/goals/new" as never)}>Create your first goal</Button>
          </View>
        ) : goals.map((goal) => (
          <Pressable
            accessibilityHint={`Opens ${goal.title}`}
            accessibilityRole="button"
            key={goal.id}
            onPress={() => router.push(routeForGoal(goal) as never)}
            style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
          >
            <View style={styles.cardTop}>
              <Text style={styles.goalTitle}>{goal.title}</Text>
              <Text style={styles.chevron}>›</Text>
            </View>
            <Text style={styles.status}>
              {goal.status === "completed"
                ? `Goal complete · ${goal.completed_steps} steps`
                : goal.active_roadmap_id
                  ? `${goal.completed_steps} of ${goal.total_steps} steps · ${goal.progress_percent}% complete`
                  : "Finish setting up your roadmap"}
            </Text>
            {goal.active_roadmap_id ? (
              <View style={styles.progressTrack}>
                <View
                  style={[
                    styles.progressFill,
                    { width: `${goal.progress_percent}%` as `${number}%` },
                  ]}
                />
              </View>
            ) : null}
            <Text style={styles.continueLabel}>
              {goal.status === "completed" ? "Review your journey" : "Continue →"}
            </Text>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  appearanceLink: { alignSelf: "flex-start", marginBottom: 14, minHeight: 34, justifyContent: "center" },
  appearanceText: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  header: { gap: 10, marginBottom: 18 },
  headerCopy: { flex: 1 },
  newGoalButton: { alignSelf: "flex-start", minWidth: 130 },
  list: { gap: 14 },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderRadius: 20,
    borderWidth: 1,
    gap: 10,
    padding: 22,
  },
  emptyTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", lineHeight: 27 },
  emptyBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginBottom: 6 },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderRadius: 20,
    borderWidth: 1,
    padding: 20,
  },
  cardPressed: { opacity: 0.76 },
  cardTop: { alignItems: "center", flexDirection: "row", gap: 12 },
  goalTitle: { color: colors.ink, flex: 1, fontSize: 19, fontWeight: "800", lineHeight: 26 },
  chevron: { color: colors.forest, fontSize: 30, lineHeight: 30 },
  status: { color: colors.muted, fontSize: 14, marginTop: 10 },
  continueLabel: { color: colors.forest, fontSize: 14, fontWeight: "800", marginTop: 14 },
  progressTrack: {
    backgroundColor: colors.line,
    borderRadius: 4,
    height: 6,
    marginTop: 12,
    overflow: "hidden",
  },
  progressFill: { backgroundColor: colors.forest, borderRadius: 4, height: 6 },
});
