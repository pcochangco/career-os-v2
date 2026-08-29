import { useLocalSearchParams, useRouter } from "expo-router";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Body, Brand, Button, colors, Field, Heading, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { DiscoveryAnswers, Roadmap } from "@/lib/types";

const questions: Array<{
  key: keyof DiscoveryAnswers;
  title: string;
  help: string;
  placeholder: string;
}> = [
  {
    key: "desired_outcome",
    title: "What should be different when you finish?",
    help: "Describe what you want to confidently do, understand, or produce.",
    placeholder: "I want to be able to…",
  },
  {
    key: "current_level",
    title: "Where are you starting from?",
    help: "A simple, honest description is enough.",
    placeholder: "I’m a beginner / I already know…",
  },
  {
    key: "existing_experience",
    title: "What relevant experience do you already have?",
    help: "This helps the roadmap avoid repeating work you have already done.",
    placeholder: "Skills, courses, projects, or experience…",
  },
  {
    key: "relevant_constraints",
    title: "What should the roadmap work around?",
    help: "Mention access, budget, tools, or learning preferences—not a required schedule.",
    placeholder: "I prefer practical work, free resources, concise lessons…",
  },
  {
    key: "proof_of_completion",
    title: "What would make you confident you achieved it?",
    help: "Choose a real output or demonstration you would be proud to show.",
    placeholder: "A portfolio project, certification, presentation…",
  },
];

const initialAnswers: DiscoveryAnswers = {
  desired_outcome: "",
  current_level: "",
  existing_experience: "",
  relevant_constraints: "",
  proof_of_completion: "",
};

export default function DiscoveryRoute() {
  const { goalId } = useLocalSearchParams<{ goalId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [answers, setAnswers] = useState(initialAnswers);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const question = questions[index];

  if (!question || !goalId) return null;
  const value = answers[question.key];
  const isLast = index === questions.length - 1;
  const progressWidth = `${((index + 1) / questions.length) * 100}%` as `${number}%`;

  async function continueFlow() {
    if (!value.trim()) return;
    if (!isLast) {
      setIndex((current) => current + 1);
      return;
    }
    if (!token) return;
    try {
      setSaving(true);
      setError(null);
      await apiRequest(`/goals/${goalId}/discovery`, {
        body: answers,
        method: "PUT",
        token,
      });
      const roadmap = await apiRequest<Roadmap>(`/goals/${goalId}/roadmaps`, {
        method: "POST",
        token,
      });
      router.replace(`/goals/${goalId}/review?roadmapId=${roadmap.id}` as never);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your roadmap could not be generated.");
      setSaving(false);
    }
  }

  return (
    <Screen>
      <Brand />
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: progressWidth }]} />
      </View>
      <Text style={styles.progressLabel}>A little context · {index + 1} of {questions.length}</Text>
      <Heading>{question.title}</Heading>
      <Body>{question.help}</Body>
      <Field
        autoFocus
        multiline
        onChangeText={(answer) => setAnswers((current) => ({ ...current, [question.key]: answer }))}
        placeholder={question.placeholder}
        value={value}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.actions}>
        {index > 0 ? <Button onPress={() => setIndex((current) => current - 1)} secondary>Back</Button> : null}
        <View style={styles.primaryAction}>
          <Button disabled={!value.trim()} loading={saving} onPress={() => void continueFlow()}>
            {isLast ? "Create my roadmap" : "Continue"}
          </Button>
        </View>
      </View>
      {saving ? <Text style={styles.generating}>Building a clear first path from your answers…</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  progressTrack: { backgroundColor: colors.line, borderRadius: 4, height: 6, overflow: "hidden" },
  progressFill: { backgroundColor: colors.forest, borderRadius: 4, height: 6 },
  progressLabel: { color: colors.muted, fontSize: 13, fontWeight: "700", marginBottom: 26, marginTop: 10 },
  actions: { flexDirection: "row", gap: 12 },
  primaryAction: { flex: 1 },
  error: { color: "#A43E38", fontSize: 14, marginBottom: 14 },
  generating: { color: colors.muted, fontSize: 14, marginTop: 16, textAlign: "center" },
});
