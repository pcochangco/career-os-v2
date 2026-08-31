import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import {
  Body,
  Brand,
  Button,
  colors,
  ErrorState,
  Field,
  Heading,
  LoadingState,
  Screen,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { DiscoveryState, Roadmap } from "@/lib/types";

export default function DiscoveryRoute() {
  const { goalId } = useLocalSearchParams<{ goalId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [state, setState] = useState<DiscoveryState | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [customAnswer, setCustomAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadDiscovery = useCallback(async () => {
    if (!token || !goalId) return;
    try {
      setError(null);
      const current = await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery`, { token });
      const next = current.status === "unstarted"
        ? await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery/questions/next`, { method: "POST", token })
        : current;
      setState(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not tailor your questions.");
    }
  }, [goalId, token]);

  useEffect(() => {
    void loadDiscovery();
  }, [loadDiscovery]);

  const question = state?.question;

  function toggleOption(key: string) {
    if (!question) return;
    setSelected((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  async function submitAnswer(skipped: boolean) {
    if (!token || !goalId || !question) return;
    try {
      setSaving(true);
      setError(null);
      const next = await apiRequest<DiscoveryState>(
        `/goals/${goalId}/discovery/questions/${question.id}/answer`,
        {
          body: {
            selected_option_keys: skipped ? [] : selected,
            custom_answer: skipped ? "" : customAnswer,
            skipped,
          },
          method: "POST",
          token,
        },
      );
      setState(next);
      setSelected([]);
      setCustomAnswer("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not save that answer.");
    } finally {
      setSaving(false);
    }
  }

  async function createRoadmap() {
    if (!token || !goalId) return;
    try {
      setSaving(true);
      setError(null);
      const roadmap = await apiRequest<Roadmap>(`/goals/${goalId}/roadmaps`, { method: "POST", token });
      router.replace(`/goals/${goalId}/review?roadmapId=${roadmap.id}` as never);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your roadmap could not be generated.");
      setSaving(false);
    }
  }

  if (!state) {
    return error
      ? <ErrorState message={error} onRetry={() => void loadDiscovery()} />
      : <LoadingState label="Finding the right first question…" />;
  }

  if (state?.status === "ready") {
    return (
      <Screen>
        <Brand />
        <Text style={styles.eyebrow}>Your starting context</Text>
        <Heading>Ready to shape your path.</Heading>
        <Body>{state.completion_reason}</Body>
        <View style={styles.summaryCard}>
          {state.context_summary.map((item) => <Text key={item} style={styles.summaryItem}>{item}</Text>)}
        </View>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Button loading={saving} onPress={() => void createRoadmap()}>Create my roadmap</Button>
      </Screen>
    );
  }

  return (
    <Screen>
      <Brand />
      <Text style={styles.eyebrow}>{state.goal_title || "Your goal"} · Question {question?.position ?? 1}</Text>
      <Heading>{question?.question ?? "Let's understand your goal."}</Heading>
      <Body>{question?.help_text}</Body>
      <View style={styles.chips}>
        {question?.options.map((option) => {
          const active = selected.includes(option.key);
          return (
            <Pressable
              accessibilityRole="button"
              key={option.key}
              onPress={() => toggleOption(option.key)}
              style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && styles.chipPressed]}
            >
              <Text style={[styles.chipText, active && styles.chipTextActive]}>{option.label}</Text>
            </Pressable>
          );
        })}
      </View>
      <Text style={styles.or}>Choose every suggestion that applies, or answer in your own words</Text>
      <Field
        multiline
        onChangeText={setCustomAnswer}
        placeholder={question?.placeholder || "Tell us what matters to you…"}
        value={customAnswer}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={styles.actions}>
        <View style={styles.secondaryAction}>
          <Button loading={saving} onPress={() => void submitAnswer(true)} secondary>Skip for now</Button>
        </View>
        <View style={styles.primaryAction}>
          <Button disabled={!selected.length && !customAnswer.trim()} loading={saving} onPress={() => void submitAnswer(false)}>
            Continue
          </Button>
        </View>
      </View>
      <Text style={styles.note}>Choose a suggestion, add your own answer, or do both. You can skip any question.</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  eyebrow: { color: colors.forest, fontSize: 13, fontWeight: "800", letterSpacing: 0.3, marginBottom: 12, textTransform: "uppercase" },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 22 },
  chip: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 999, borderWidth: 1, paddingHorizontal: 15, paddingVertical: 11 },
  chipActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  chipPressed: { opacity: 0.78 },
  chipText: { color: colors.ink, fontSize: 14, fontWeight: "700" },
  chipTextActive: { color: colors.white },
  or: { color: colors.muted, fontSize: 13, fontWeight: "700", marginBottom: 9 },
  actions: { flexDirection: "row", gap: 12 },
  secondaryAction: { flex: 0.88 },
  primaryAction: { flex: 1 },
  error: { color: "#A43E38", fontSize: 14, marginBottom: 14 },
  note: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 15, textAlign: "center" },
  summaryCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, gap: 12, marginBottom: 22, padding: 18 },
  summaryItem: { color: colors.ink, fontSize: 15, lineHeight: 22 },
});
