import { useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import {
  Body,
  Brand,
  Button,
  ErrorState,
  Field,
  Heading,
  LoadingState,
  Screen,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { DiscoveryState, Goal, Roadmap } from "@/lib/types";
import { ThemeColors, useTheme } from "@/lib/theme";

export default function DiscoveryRoute() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const { goalId } = useLocalSearchParams<{ goalId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [state, setState] = useState<DiscoveryState | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [customAnswer, setCustomAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationStage, setGenerationStage] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);
  const answerRequestRef = useRef(false);
  const generationRequestRef = useRef(false);

  const generationStages = [
    "Understanding your goal and starting point…",
    "Building a practical milestone sequence…",
    "Checking each action and its completion evidence…",
    "Preparing your roadmap for review…",
  ];

  const loadDiscovery = useCallback(async () => {
    if (!token || !goalId) return;
    try {
      setError(null);
      const goal = await apiRequest<Goal>(`/goals/${goalId}`, { token });
      if (goal.active_roadmap_id) {
        router.replace(
          `/goals/${goalId}/roadmap?roadmapId=${goal.active_roadmap_id}` as never,
        );
        return;
      }
      if (goal.latest_draft_roadmap_id) {
        router.replace(
          `/goals/${goalId}/review?roadmapId=${goal.latest_draft_roadmap_id}` as never,
        );
        return;
      }
      const current = await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery`, { token });
      const next = current.status === "unstarted"
        ? await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery/questions/next`, { method: "POST", token })
        : current;
      setState(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not tailor your questions.");
    }
  }, [goalId, router, token]);

  useEffect(() => {
    void loadDiscovery();
  }, [loadDiscovery]);

  useEffect(() => {
    void AccessibilityInfo.isReduceMotionEnabled().then(setReduceMotion);
    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReduceMotion,
    );
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (!generating || reduceMotion) return;
    const interval = setInterval(() => {
      setGenerationStage((current) => (current + 1) % generationStages.length);
    }, 2400);
    return () => clearInterval(interval);
  }, [generating, generationStages.length, reduceMotion]);

  const question = state?.question;

  function toggleOption(key: string) {
    if (!question) return;
    setSelected((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  async function submitAnswer(skipped: boolean) {
    if (!token || !goalId || !question || answerRequestRef.current) return;
    try {
      answerRequestRef.current = true;
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
      answerRequestRef.current = false;
      setSaving(false);
    }
  }

  async function createRoadmap() {
    if (!token || !goalId || generationRequestRef.current) return;
    try {
      generationRequestRef.current = true;
      setGenerationStage(0);
      setGenerating(true);
      setError(null);
      const roadmap = await apiRequest<Roadmap>(`/goals/${goalId}/roadmaps`, { method: "POST", token });
      router.replace(`/goals/${goalId}/review?roadmapId=${roadmap.id}` as never);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your roadmap could not be generated.");
      setGenerating(false);
      generationRequestRef.current = false;
    }
  }

  if (!state) {
    return error
      ? <ErrorState message={error} onRetry={() => void loadDiscovery()} />
      : <LoadingState label="Finding the right first question…" />;
  }

  if (generating) {
    return (
      <Screen>
        <Brand />
        <View
          accessibilityLabel="Building your roadmap"
          accessibilityLiveRegion="polite"
          accessibilityRole="progressbar"
          style={styles.generating}
        >
          <View style={styles.generatingIndicator}>
            <ActivityIndicator color={colors.forest} size="large" />
          </View>
          <Text style={styles.eyebrow}>Creating {state.goal_title || "your roadmap"}</Text>
          <Heading>Building your roadmap…</Heading>
          <Text style={styles.generationStage}>
            {reduceMotion ? generationStages[0] : generationStages[generationStage]}
          </Text>
          <Text style={styles.generationNote}>
            Keep this page open. CareerOS will take you to the draft as soon as it is ready.
          </Text>
        </View>
      </Screen>
    );
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
        <Button onPress={() => void createRoadmap()}>Generate roadmap</Button>
      </Screen>
    );
  }

  const questionPosition = question?.position ?? state.answered_questions + 1;
  const progressWidth = `${Math.min(
    100,
    (questionPosition / state.maximum_questions) * 100,
  )}%` as `${number}%`;
  const mayFinishAfterThisQuestion = questionPosition >= state.minimum_questions;
  const useCompactChoices = Boolean(
    question &&
      questionPosition % 2 === 1 &&
      question.options.length <= 5 &&
      question.options.every((option) => option.label.length <= 32),
  );

  return (
    <Screen>
      <Brand />
      <View
        accessibilityLabel={`Discovery progress. Question ${questionPosition} of up to ${state.maximum_questions}.`}
        accessibilityRole="progressbar"
        accessibilityValue={{
          max: state.maximum_questions,
          min: 0,
          now: questionPosition,
          text: `Question ${questionPosition} of up to ${state.maximum_questions}`,
        }}
        style={styles.progress}
      >
        <View style={styles.progressCopy}>
          <Text style={styles.progressLabel}>Shaping your roadmap</Text>
          <Text style={styles.progressCount}>
            Question {questionPosition} of up to {state.maximum_questions}
          </Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: progressWidth }]} />
        </View>
        <Text style={styles.progressHint}>
          {mayFinishAfterThisQuestion
            ? "This may be the final question if CareerOS has enough context."
            : "CareerOS will stop as soon as it has enough useful context."}
        </Text>
      </View>
      <Text style={styles.eyebrow}>{state.goal_title || "Your goal"}</Text>
      <Text style={styles.questionTitle}>
        {question?.question ?? "Let's understand your goal."}
      </Text>
      <Body>{question?.help_text}</Body>
      <View
        accessibilityRole="list"
        style={[styles.choices, useCompactChoices && styles.choiceChips]}
      >
        {question?.options.map((option) => {
          const active = selected.includes(option.key);
          return (
            <Pressable
              accessibilityRole="checkbox"
              accessibilityState={{ checked: active }}
              key={option.key}
              onPress={() => toggleOption(option.key)}
              style={({ pressed }) => [
                useCompactChoices ? styles.choiceChip : styles.choice,
                active && styles.choiceActive,
                pressed && styles.choicePressed,
              ]}
            >
              {!useCompactChoices ? (
                <View style={[styles.choiceMark, active && styles.choiceMarkActive]}>
                  {active ? <Text style={styles.choiceCheck}>✓</Text> : null}
                </View>
              ) : null}
              <Text
                style={[
                  useCompactChoices ? styles.choiceChipText : styles.choiceText,
                  active && styles.choiceTextActive,
                ]}
              >
                {useCompactChoices && active ? `✓ ${option.label}` : option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
      <Text style={styles.or}>Select all that apply, or answer in your own words</Text>
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

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  eyebrow: { color: colors.forest, fontSize: 13, fontWeight: "800", letterSpacing: 0.3, marginBottom: 12, textTransform: "uppercase" },
  progress: { marginBottom: 24 },
  progressCopy: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 9 },
  progressLabel: { color: colors.forestDark, fontSize: 13, fontWeight: "800" },
  progressCount: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  progressTrack: { backgroundColor: colors.line, borderRadius: 5, height: 8, overflow: "hidden" },
  progressFill: { backgroundColor: colors.forest, borderRadius: 5, height: "100%" },
  progressHint: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 8 },
  questionTitle: { color: colors.ink, fontSize: 30, fontWeight: "800", letterSpacing: -0.6, lineHeight: 37, marginBottom: 14 },
  choices: { gap: 10, marginBottom: 22, width: "100%" },
  choiceChips: { flexDirection: "row", flexWrap: "wrap" },
  choice: { alignItems: "center", alignSelf: "stretch", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 16, borderWidth: 1, flexDirection: "row", gap: 12, minHeight: 52, paddingHorizontal: 15, paddingVertical: 13, width: "100%" },
  choiceChip: { alignItems: "center", alignSelf: "flex-start", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 999, borderWidth: 1, flexDirection: "row", flexShrink: 1, maxWidth: "100%", minHeight: 44, paddingHorizontal: 15, paddingVertical: 10 },
  choiceActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  choicePressed: { opacity: 0.78 },
  choiceMark: { alignItems: "center", borderColor: colors.muted, borderRadius: 7, borderWidth: 1.5, flexShrink: 0, height: 22, justifyContent: "center", width: 22 },
  choiceMarkActive: { backgroundColor: colors.onForest, borderColor: colors.onForest },
  choiceCheck: { color: colors.forest, fontSize: 14, fontWeight: "900", lineHeight: 17 },
  choiceText: { color: colors.ink, flex: 1, flexShrink: 1, fontSize: 15, fontWeight: "700", lineHeight: 21, minWidth: 0 },
  choiceChipText: { color: colors.ink, flexShrink: 1, fontSize: 15, fontWeight: "700", lineHeight: 21, maxWidth: "100%" },
  choiceTextActive: { color: colors.onForest },
  or: { color: colors.muted, fontSize: 13, fontWeight: "700", marginBottom: 9 },
  actions: { flexDirection: "row", gap: 12 },
  secondaryAction: { flex: 0.88 },
  primaryAction: { flex: 1 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 14 },
  note: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 15, textAlign: "center" },
  summaryCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, gap: 12, marginBottom: 22, padding: 18 },
  summaryItem: { color: colors.ink, fontSize: 15, lineHeight: 22 },
  generating: { flex: 1, justifyContent: "center", minHeight: 480 },
  generatingIndicator: { alignItems: "center", backgroundColor: colors.forestSoft, borderRadius: 40, height: 80, justifyContent: "center", marginBottom: 24, width: 80 },
  generationStage: { color: colors.forestDark, fontSize: 17, fontWeight: "800", lineHeight: 25, marginBottom: 10 },
  generationNote: { color: colors.muted, fontSize: 14, lineHeight: 21 },
});
