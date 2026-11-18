import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ChevronRight } from "@/components/icons";

import { useIsWide } from "@/components/app-shell";
import { GoalLimitCard } from "@/components/plan-limit";
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
  const wide = useIsWide();
  const { account, token } = useSession();
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

  const goalLimit = account?.goal_limit ?? null;
  const atGoalLimit = goalLimit !== null && goals.length >= goalLimit;

  return (
    <Screen width="wide">
      <Brand />
      <View style={[styles.header, wide && styles.headerWide]}>
        <View style={styles.headerCopy}>
          <Heading>Your goals</Heading>
          <Body>Choose a path and continue exactly where you left it.</Body>
        </View>
        {goals.length > 0 && !atGoalLimit ? (
          <View style={styles.newGoalButton}>
            <Button onPress={() => router.push("/goals/new" as never)}>New goal</Button>
          </View>
        ) : null}
      </View>
      {goalLimit !== null && goals.length > 0 ? (
        atGoalLimit ? (
          <View style={styles.limitCard}>
            <GoalLimitCard limit={goalLimit} />
          </View>
        ) : (
          <Text style={styles.planUsage}>
            {goals.length} of {goalLimit} free goals used
          </Text>
        )
      ) : null}
      <View style={[styles.list, wide && styles.grid]}>
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
            style={({ hovered, pressed }: { hovered?: boolean; pressed: boolean }) => [
              styles.card,
              wide && styles.cardWide,
              hovered && { borderColor: colors.softBorder },
              pressed && styles.cardPressed,
            ]}
          >
            <View style={styles.cardTop}>
              <Text style={styles.goalTitle}>{goal.title}</Text>
              <ChevronRight color={colors.subtle} size={20} strokeWidth={2} />
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
              {goal.status === "completed" ? "Review your journey" : goal.active_roadmap_id ? "Continue" : "Finish setup"}
            </Text>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  header: { gap: 4, marginBottom: 20 },
  headerWide: { alignItems: "flex-start", flexDirection: "row", gap: 24, justifyContent: "space-between" },
  headerCopy: { flex: 1 },
  newGoalButton: { alignSelf: "flex-start", minWidth: 120 },
  limitCard: { marginBottom: 16 },
  planUsage: { color: colors.subtle, fontSize: 14, marginBottom: 14, marginTop: -8 },
  list: { gap: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap" },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderRadius: 12,
    borderWidth: 1,
    gap: 10,
    padding: 22,
  },
  emptyTitle: { color: colors.ink, fontSize: 18, fontWeight: "700", lineHeight: 26 },
  emptyBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginBottom: 6 },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderRadius: 12,
    borderWidth: 1,
    padding: 18,
  },
  cardWide: { flexBasis: "48%", flexGrow: 1, maxWidth: "49.4%" },
  cardPressed: { opacity: 0.76 },
  cardTop: { alignItems: "center", flexDirection: "row", gap: 12 },
  goalTitle: { color: colors.ink, flex: 1, fontSize: 17, fontWeight: "700", lineHeight: 24 },
  status: { color: colors.muted, fontSize: 14, marginTop: 10 },
  continueLabel: { color: colors.forest, fontSize: 14, fontWeight: "700", marginTop: 14 },
  progressTrack: {
    backgroundColor: colors.line,
    borderRadius: 4,
    height: 6,
    marginTop: 12,
    overflow: "hidden",
  },
  progressFill: { backgroundColor: colors.forest, borderRadius: 4, height: 6 },
});
