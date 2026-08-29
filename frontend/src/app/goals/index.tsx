import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Body, Brand, Button, colors, ErrorState, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";

function routeForGoal(goal: Goal): string {
  if (goal.active_roadmap_id) return `/goals/${goal.id}/roadmap?roadmapId=${goal.active_roadmap_id}`;
  if (goal.latest_draft_roadmap_id) return `/goals/${goal.id}/review?roadmapId=${goal.latest_draft_roadmap_id}`;
  return `/goals/${goal.id}/discovery`;
}

export default function GoalsRoute() {
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
        {goals.map((goal) => (
          <Pressable
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
              {goal.active_roadmap_id ? "Roadmap ready · 0% complete" : "Finish setting up your roadmap"}
            </Text>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 10, marginBottom: 18 },
  headerCopy: { flex: 1 },
  newGoalButton: { alignSelf: "flex-start", minWidth: 130 },
  list: { gap: 14 },
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
});
