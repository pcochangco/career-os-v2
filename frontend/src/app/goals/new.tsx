import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { StyleSheet, Text } from "react-native";

import { Body, Brand, Button, colors, Field, Heading, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Goal } from "@/lib/types";

export default function NewGoalRoute() {
  const router = useRouter();
  const { token } = useSession();
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submittingRef = useRef(false);

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

  return (
    <Screen>
      <Brand />
      <Text style={styles.step}>New goal</Text>
      <Heading>What do you want to achieve?</Heading>
      <Body>Describe the destination. CareerOS will help shape the path.</Body>
      <Field
        autoFocus
        maxLength={140}
        onChangeText={setTitle}
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

const styles = StyleSheet.create({
  step: { color: colors.forest, fontSize: 14, fontWeight: "800", marginBottom: 12 },
  error: { color: "#A43E38", fontSize: 14, marginBottom: 14 },
});
