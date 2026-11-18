import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ChevronRight } from "@/components/icons";

import { useIsWide } from "@/components/app-shell";
import { GoalLimitCard } from "@/components/plan-limit";
import { GoalsSkeleton } from "@/components/skeleton";
import { Body, Brand, Button, ErrorState, Heading, Screen } from "@/components/ui";
import { loadGoals } from "@/lib/prefetch";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";
import { ThemeColors, useTheme } from "@/lib/theme";

function routeForGoal(goal: Goal): string {
  if (goal.active_roadmap_id) return `/goals/${goal.id}/roadmap?roadmapId=${goal.active_roadmap_id}`;
  if (goal.latest_draft_roadmap_id) return `/goals/${goal.id}/review?roadmapId=${goal.latest_draft_roadmap_id}`;
  return `/goals/${goal.id}/discovery`;
}

/** "today", "yesterday", "3 days ago", or a short date for anything older than a week. */
function lastWorkedLabel(iso: string, now = new Date()): string {
  const then = new Date(iso);
  const startOfDay = (date: Date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const days = Math.round((startOfDay(now) - startOfDay(then)) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return `on ${then.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`;
}

/** The unfinished goal worked on most recently, if any work has happened yet. */
function lastWorkedGoal(goals: Goal[]): Goal | null {
  return goals
    .filter((goal) => goal.status !== "completed" && goal.active_roadmap_id && goal.last_activity_at)
    .reduce<Goal | null>(
      (latest, goal) =>
        !latest || (goal.last_activity_at ?? "") > (latest.last_activity_at ?? "") ? goal : latest,
      null,
    );
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
    loadGoals(token)
      .then((value) => active && setGoals(value))
      .catch((caught) => active && setError(caught instanceof Error ? caught.message : "Goals could not load."));
    return () => {
      active = false;
    };
  }, [attempt, token]);

  if (!token || !goals) {
    if (error) return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
    return <GoalsSkeleton />;
  }

  const goalLimit = account?.goal_limit ?? null;
  // With one goal, opening CareerOS already lands on its roadmap; the card helps choose among several.
  const resume = goals.length > 1 ? lastWorkedGoal(goals) : null;
  const atGoalLimit = goalLimit !== null && goals.length >= goalLimit;

  return (
    <Screen width="wide">
      <Brand />
      <View style={[styles.header, wide && styles.headerWide]}>
        <View style={styles.headerCopy}>
          <Heading>Your goals</Heading>
          <Body>Pick a goal and continue exactly where you left off.</Body>
        </View>
        {goals.length > 0 && !atGoalLimit ? (
          <View style={styles.newGoalButton}>
            <Button onPress={() => router.push("/goals/new" as never)}>New goal</Button>
          </View>
        ) : null}
      </View>
      {resume ? (
        <Pressable
          accessibilityHint={`Opens your roadmap for ${resume.title}`}
          accessibilityRole="button"
          onPress={() => router.push(routeForGoal(resume) as never)}
          style={({ pressed }) => [styles.resume, pressed && styles.cardPressed]}
        >
          <View style={styles.resumeCopy}>
            <Text style={styles.resumeEyebrow}>Pick up where you left off</Text>
            <Text style={styles.resumeTitle}>{resume.title}</Text>
            {resume.current_step_title ? (
              <Text numberOfLines={2} style={styles.resumeNext}>Next: {resume.current_step_title}</Text>
            ) : null}
            <Text style={styles.resumeMeta}>
              Last worked on {lastWorkedLabel(resume.last_activity_at ?? "")} · {resume.progress_percent}% complete
            </Text>
          </View>
          <ChevronRight color={colors.onForest} size={22} strokeWidth={2.2} />
        </Pressable>
      ) : null}
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
              CareerOS will build your roadmap, then keep your next step ready.
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
              {goal.status === "completed" ? "Review roadmap" : goal.active_roadmap_id ? "Continue" : "Finish setup"}
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
  resume: {
    alignItems: "center",
    backgroundColor: colors.forest,
    borderRadius: 12,
    flexDirection: "row",
    gap: 12,
    marginBottom: 18,
    padding: 18,
  },
  resumeCopy: { flex: 1, gap: 4 },
  resumeEyebrow: { color: colors.onForestMuted, fontSize: 12, fontWeight: "800", textTransform: "uppercase" },
  resumeTitle: { color: colors.onForest, fontSize: 18, fontWeight: "800", lineHeight: 24 },
  resumeNext: { color: colors.onForest, fontSize: 15, lineHeight: 21 },
  resumeMeta: { color: colors.onForestMuted, fontSize: 13, fontWeight: "600", marginTop: 2 },
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
