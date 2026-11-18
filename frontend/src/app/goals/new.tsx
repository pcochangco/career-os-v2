import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { GoalLimitCard } from "@/components/plan-limit";
import { Body, Brand, Button, Field, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { loadGoals } from "@/lib/prefetch";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";
import { ThemeColors, useTheme } from "@/lib/theme";

export default function NewGoalRoute() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const router = useRouter();
  const { account, token } = useSession();
  const goalLimit = account?.goal_limit ?? null;
  // null while unknown; only fetched for plans with a goal limit.
  const [goalCount, setGoalCount] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submittingRef = useRef(false);

  useEffect(() => {
    if (!token || goalLimit === null) return;
    let active = true;
    loadGoals(token)
      .then((goals) => active && setGoalCount(goals.length))
      .catch(() => active && setGoalCount(0)); // Fall back to the form; the server still enforces.
    return () => {
      active = false;
    };
  }, [goalLimit, token]);

  async function createGoal() {
    if (!token || title.trim().length < 3 || submittingRef.current) return;
    try {
      submittingRef.current = true;
      setSaving(true);
      setError(null);
      const goal = await apiRequest<Goal>("/goals", {
        body: { title: title.trim() },
        method: "POST",
        token,
      });
      router.replace(`/goals/${goal.id}/discovery` as never);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your goal could not be created.");
      setSaving(false);
      submittingRef.current = false;
    }
  }

  if (goalLimit !== null && goalCount === null) return <LoadingState label="Checking your plan…" />;
  if (goalLimit !== null && goalCount !== null && goalCount >= goalLimit) {
    return (
      <Screen width="narrow">
        <Brand />
        <Text style={styles.step}>New goal</Text>
        <Heading>Your goals are ready to continue.</Heading>
        <Body>You can keep working on every goal and roadmap you’ve already created.</Body>
        <GoalLimitCard limit={goalLimit} />
        <View style={styles.backAction}>
          <Button onPress={() => router.replace("/goals" as never)} secondary>
            Back to your goals
          </Button>
        </View>
      </Screen>
    );
  }

  return (
    <Screen width="narrow">
      <Brand />
      <Text style={styles.step}>New goal</Text>
      <Heading>What do you want to achieve?</Heading>
      <Body>Describe the destination. CareerOS will build your roadmap from it.</Body>
      <Field
        autoFocus
        maxLength={140}
        onChangeText={(value) => {
          setTitle(value);
          if (error) setError(null);
        }}
        onSubmitEditing={() => void createGoal()}
        placeholder="e.g. Become confident building AI agents"
        returnKeyType="next"
        value={title}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <Button disabled={title.trim().length < 3} loading={saving} onPress={() => void createGoal()}>
        Shape my roadmap
      </Button>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  step: { color: colors.forest, fontSize: 14, fontWeight: "700", marginBottom: 12 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 14 },
  backAction: { marginTop: 16 },
});
