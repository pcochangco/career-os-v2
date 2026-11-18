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

import { Check } from "@/components/icons";
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
import { ApiError, apiRequest } from "@/lib/api";
import { clearDraft, readDraft, writeDraft } from "@/lib/drafts";
import { useSession } from "@/lib/session";
import { DiscoveryState, Goal, Roadmap } from "@/lib/types";
import { ThemeColors, useTheme } from "@/lib/theme";

const GENERATION_POLL_MS = 4000;
const GENERATION_WAIT_LIMIT_MS = 9 * 60 * 1000;

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

  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const routeToRoadmap = useCallback((goal: Goal): boolean => {
    if (goal.active_roadmap_id) {
      router.replace(`/goals/${goalId}/roadmap?roadmapId=${goal.active_roadmap_id}` as never);
      return true;
    }
    if (goal.latest_draft_roadmap_id) {
      router.replace(`/goals/${goalId}/review?roadmapId=${goal.latest_draft_roadmap_id}` as never);
      return true;
    }
    return false;
  }, [goalId, router]);

  // A roadmap is being built by an earlier request (another tab, a refresh, or a lost
  // response). Watch the goal instead of starting a second, paid generation.
  const waitForGeneration = useCallback(() => {
    if (!token || !goalId) return;
    setGenerating(true);
    setError(null);
    const startedAt = Date.now();
    const check = async () => {
      try {
        const goal = await apiRequest<Goal>(`/goals/${goalId}`, { token });
        if (routeToRoadmap(goal)) return;
        if (!goal.roadmap_generation_in_progress) {
          setGenerating(false);
          setError("Your roadmap couldn’t be finished. Please try again.");
          return;
        }
      } catch {
        // A brief network drop while waiting is fine; keep checking.
      }
      if (Date.now() - startedAt > GENERATION_WAIT_LIMIT_MS) {
        setGenerating(false);
        setError("This is taking longer than usual. Please try again in a moment.");
        return;
      }
      pollRef.current = setTimeout(() => void check(), GENERATION_POLL_MS);
    };
    pollRef.current = setTimeout(() => void check(), GENERATION_POLL_MS);
  }, [goalId, routeToRoadmap, token]);

  useEffect(() => () => {
    if (pollRef.current) clearTimeout(pollRef.current);
  }, []);

  const loadDiscovery = useCallback(async () => {
    if (!token || !goalId) return;
    try {
      setError(null);
      const goal = await apiRequest<Goal>(`/goals/${goalId}`, { token });
      if (routeToRoadmap(goal)) return;
      const current = await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery`, { token });
      const next = current.status === "unstarted"
        ? await apiRequest<DiscoveryState>(`/goals/${goalId}/discovery/questions/next`, { method: "POST", token })
        : current;
      setState(next);
      if (goal.roadmap_generation_in_progress) waitForGeneration();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not tailor your questions.");
    }
  }, [goalId, routeToRoadmap, token, waitForGeneration]);

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
  const draftKey = question ? `discovery.${question.id}` : null;

  // Restore what the user typed or picked for this question before a refresh or back button.
  useEffect(() => {
    if (!draftKey) return;
    const saved = readDraft(draftKey);
    if (!saved) return;
    try {
      const draft = JSON.parse(saved) as { custom: string; selected: string[] };
      setCustomAnswer(draft.custom ?? "");
      setSelected(Array.isArray(draft.selected) ? draft.selected : []);
    } catch {
      clearDraft(draftKey);
    }
  }, [draftKey]);

  useEffect(() => {
    if (!draftKey) return;
    if (!customAnswer && selected.length === 0) clearDraft(draftKey);
    else writeDraft(draftKey, JSON.stringify({ custom: customAnswer, selected }));
  }, [customAnswer, draftKey, selected]);

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
      clearDraft(`discovery.${question.id}`);
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
    generationRequestRef.current = true;
    setGenerationStage(0);
    setGenerating(true);
    setError(null);
    try {
      const roadmap = await apiRequest<Roadmap>(`/goals/${goalId}/roadmaps`, {
        method: "POST",
        token,
      });
      router.replace(`/goals/${goalId}/review?roadmapId=${roadmap.id}` as never);
      setGenerating(false);
    } catch (caught) {
      // 409: a generation for this goal is already running. A lost response or timeout:
      // the server may still be working, or may already have saved the draft. In both
      // cases check the goal rather than starting a second, paid generation.
      if (
        caught instanceof ApiError &&
        caught.status !== 0 &&
        caught.status !== 409 &&
        caught.status < 500
      ) {
        setGenerating(false);
        setError(caught.message);
        return;
      }
      try {
        const goal = await apiRequest<Goal>(`/goals/${goalId}`, { token });
        if (routeToRoadmap(goal)) return;
        if (goal.roadmap_generation_in_progress) {
          waitForGeneration();
          return;
        }
      } catch {
        // Fall through to the original error if the API cannot be reached either.
      }
      setGenerating(false);
      setError(
        caught instanceof ApiError
          ? caught.message
          : "We couldn’t reach CareerOS. Check your connection and try again.",
      );
    } finally {
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
      <Screen width="narrow">
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
            This usually takes under a minute. If you leave, your roadmap keeps building and
            will be waiting when you come back.
          </Text>
        </View>
      </Screen>
    );
  }

  const answeredContext = (state.context ?? []).filter((item) => !item.skipped);
  const skippedCount = (state.context ?? []).length - answeredContext.length;

  if (state?.status === "ready") {
    return (
      <Screen width="narrow">
        <Brand />
        <Text style={styles.eyebrow}>Your starting context</Text>
        <Heading>Ready to build your roadmap.</Heading>
        <Body>{state.completion_reason}</Body>
        {answeredContext.length > 0 ? (
          <View style={styles.summaryCard}>
            {answeredContext.map((item) => (
              <View key={item.question} style={styles.summaryRow}>
                <Text style={styles.summaryQuestion}>{item.question}</Text>
                <Text style={styles.summaryItem}>{item.answer}</Text>
              </View>
            ))}
            {skippedCount > 0 ? (
              <Text style={styles.summarySkipped}>
                {skippedCount === 1 ? "1 question skipped" : `${skippedCount} questions skipped`}
              </Text>
            ) : null}
          </View>
        ) : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <Button onPress={() => void createRoadmap()}>Generate roadmap</Button>
      </Screen>
    );
  }

  const questionPosition = question?.position ?? state.answered_questions + 1;
  const maxQuestions = Math.max(state.maximum_questions, questionPosition);
  const progressWidth = `${Math.round((questionPosition / maxQuestions) * 100)}%` as `${number}%`;
  const mayFinishAfterThisQuestion = questionPosition >= state.minimum_questions;
  const useCompactChoices = Boolean(
    question &&
      questionPosition % 2 === 1 &&
      question.options.length <= 5 &&
      question.options.every((option) => option.label.length <= 32),
  );

  return (
    <Screen width="narrow">
      <Brand />
      <View
        accessibilityLabel={`Discovery progress. Question ${questionPosition}.`}
        accessibilityRole="progressbar"
        accessibilityValue={{
          text: `Question ${questionPosition} of up to ${maxQuestions}. CareerOS will stop when it has enough context.`,
        }}
        style={styles.progress}
      >
        <View style={styles.progressCopy}>
          <Text style={styles.progressLabel}>Shaping your roadmap</Text>
          <Text style={styles.progressCount}>
            Question {questionPosition} of up to {maxQuestions}
          </Text>
        </View>
        <View style={styles.progressTrack}>
          <View style={[styles.progressFill, { width: progressWidth }]} />
        </View>
        <Text style={styles.progressHint}>
          {mayFinishAfterThisQuestion
            ? "CareerOS will stop when it has enough useful context."
            : "CareerOS is learning what matters for this goal."}
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
                  {active ? <Check color={colors.forest} size={15} strokeWidth={3.2} /> : null}
                </View>
              ) : null}
              {useCompactChoices && active ? (
                <Check color={colors.onForest} size={15} strokeWidth={3} style={styles.chipCheck} />
              ) : null}
              <Text
                style={[
                  useCompactChoices ? styles.choiceChipText : styles.choiceText,
                  active && styles.choiceTextActive,
                ]}
              >
                {option.label}
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
  questionTitle: { color: colors.ink, fontSize: 24, fontWeight: "700", letterSpacing: -0.4, lineHeight: 31, marginBottom: 14 },
  choices: { gap: 10, marginBottom: 22, width: "100%" },
  choiceChips: { flexDirection: "row", flexWrap: "wrap" },
  choice: { alignItems: "center", alignSelf: "stretch", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, flexDirection: "row", gap: 12, minHeight: 52, paddingHorizontal: 15, paddingVertical: 13, width: "100%" },
  choiceChip: { alignItems: "center", alignSelf: "flex-start", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 999, borderWidth: 1, flexDirection: "row", flexShrink: 1, maxWidth: "100%", minHeight: 44, paddingHorizontal: 15, paddingVertical: 10 },
  choiceActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  choicePressed: { opacity: 0.78 },
  choiceMark: { alignItems: "center", borderColor: colors.muted, borderRadius: 7, borderWidth: 1.5, flexShrink: 0, height: 22, justifyContent: "center", width: 22 },
  choiceMarkActive: { backgroundColor: colors.onForest, borderColor: colors.onForest },
  chipCheck: { marginRight: 6 },
  choiceText: { color: colors.ink, flex: 1, flexShrink: 1, fontSize: 15, fontWeight: "700", lineHeight: 21, minWidth: 0 },
  choiceChipText: { color: colors.ink, flexShrink: 1, fontSize: 15, fontWeight: "700", lineHeight: 21, maxWidth: "100%" },
  choiceTextActive: { color: colors.onForest },
  or: { color: colors.muted, fontSize: 13, fontWeight: "700", marginBottom: 9 },
  actions: { flexDirection: "row", gap: 12 },
  secondaryAction: { flex: 0.88 },
  primaryAction: { flex: 1 },
  error: { color: colors.danger, fontSize: 14, marginBottom: 14 },
  note: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 15, textAlign: "center" },
  summaryCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, gap: 12, marginBottom: 22, padding: 18 },
  summaryItem: { color: colors.ink, fontSize: 15, lineHeight: 22 },
  summaryRow: { gap: 2 },
  summaryQuestion: { color: colors.subtle, fontSize: 13, lineHeight: 18 },
  summarySkipped: { color: colors.subtle, fontSize: 13 },
  generating: { flex: 1, justifyContent: "center", minHeight: 480 },
  generatingIndicator: { alignItems: "center", backgroundColor: colors.forestSoft, borderRadius: 40, height: 80, justifyContent: "center", marginBottom: 24, width: 80 },
  generationStage: { color: colors.forestDark, fontSize: 17, fontWeight: "800", lineHeight: 25, marginBottom: 10 },
  generationNote: { color: colors.muted, fontSize: 14, lineHeight: 21 },
});
