import { Pressable, Text, View } from "react-native";

import { ArrowRight, Check } from "@/components/icons";
import { RoadmapStyles } from "@/components/roadmap/styles";
import { useTheme } from "@/lib/theme";
import { RoadmapPracticeTask } from "@/lib/types";

/** Today's optional practice: log it, or swap for another one from this roadmap. */
export function PracticeCard({
  error,
  hasAlternatives,
  onComplete,
  onShowAnother,
  practicedToday,
  saving,
  styles,
  task,
}: {
  error: string | null;
  hasAlternatives: boolean;
  onComplete: () => void;
  onShowAnother: () => void;
  practicedToday: boolean;
  saving: boolean;
  styles: RoadmapStyles;
  task: RoadmapPracticeTask;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.practiceCard}>
      <View style={styles.practiceHeader}>
        <Text style={styles.practiceEyebrow}>Daily practice</Text>
        {practicedToday ? (
          <View style={styles.inlineRow}>
            <Check color={colors.forest} size={14} strokeWidth={3} />
            <Text style={styles.practiceCompleteMark}>Done</Text>
          </View>
        ) : null}
      </View>
      <Text style={styles.practiceTitle}>{task.title}</Text>
      <Text style={styles.practiceBody}>{task.instruction}</Text>
      <View style={styles.practiceProof}>
        <Text style={styles.practiceProofLabel}>Done when</Text>
        <Text style={styles.practiceProofText}>{task.completion_signal}</Text>
      </View>
      {practicedToday ? (
        <View style={styles.practiceCelebration}>
          <Text style={styles.practiceCelebrationTitle}>Practice logged.</Text>
          <Text style={styles.practiceCelebrationText}>That is a real piece of work toward this goal.</Text>
        </View>
      ) : (
        <Pressable
          accessibilityHint="Records this optional practice as completed for today"
          accessibilityRole="button"
          accessibilityState={{ busy: saving }}
          onPress={onComplete}
          style={({ pressed }) => [styles.practiceCompleteButton, pressed && styles.practiceCompleteButtonPressed]}
        >
          <Text style={styles.practiceCompleteButtonText}>
            {saving ? "Logging…" : "I did this today"}
          </Text>
        </Pressable>
      )}
      {error ? (
        <Text accessibilityLiveRegion="polite" style={styles.inlineError}>{error}</Text>
      ) : null}
      {!practicedToday && hasAlternatives ? (
        <Pressable
          accessibilityHint="Shows another optional practice from this roadmap"
          accessibilityRole="button"
          onPress={onShowAnother}
          style={({ pressed }) => [styles.practiceNext, pressed && styles.practiceNextPressed]}
        >
          <View style={styles.inlineRow}>
            <Text style={styles.practiceNextText}>Show another practice</Text>
            <ArrowRight color={colors.forest} size={15} strokeWidth={2.6} />
          </View>
        </Pressable>
      ) : null}
    </View>
  );
}
