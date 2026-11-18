import { useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";

import { Check, ChevronDown, ChevronUp } from "@/components/icons";
import { RoadmapStyles } from "@/components/roadmap/styles";
import { useTheme } from "@/lib/theme";
import { Roadmap } from "@/lib/types";

/** Overview of every milestone with progress, plus the optional detailed map. */
export function MilestoneMap({ roadmap, styles }: { roadmap: Roadmap; styles: RoadmapStyles }) {
  const { colors } = useTheme();
  const [detailedMapExpanded, setDetailedMapExpanded] = useState(false);
  const milestoneProgress = useMemo(
    () =>
      roadmap.milestones.map((milestone) => {
        const completed = milestone.steps.filter(
          (step) => step.progress_status === "completed",
        ).length;
        const isCurrent = milestone.steps.some((step) => step.progress_status === "current");
        return { ...milestone, completed, isCurrent };
      }),
    [roadmap],
  );

  return (
    <View style={styles.mapCard}>
      <Text style={styles.mapEyebrow}>Your roadmap map</Text>
      <Text style={styles.mapTitle}>Build toward: {roadmap.goal_outcome}</Text>
      <Text style={styles.mapBody}>
        Each milestone unlocks the next piece of proof for your goal.
      </Text>
      <View style={styles.mapMilestones}>
        {milestoneProgress.map((milestone, index) => (
          <View key={milestone.id} style={styles.mapMilestoneRow}>
            <View style={styles.mapRail}>
              <View
                style={[
                  styles.mapNode,
                  milestone.completed === milestone.steps.length && styles.mapNodeCompleted,
                  milestone.isCurrent && styles.mapNodeCurrent,
                ]}
              >
                {milestone.completed === milestone.steps.length ? (
                  <Check color={colors.onForest} size={16} strokeWidth={3} />
                ) : (
                  <Text
                    style={[styles.mapNodeText, milestone.isCurrent && styles.mapNodeTextActive]}
                  >
                    {milestone.position}
                  </Text>
                )}
              </View>
              {index < milestoneProgress.length - 1 ? <View style={styles.mapConnector} /> : null}
            </View>
            <View style={styles.mapMilestoneContent}>
              <Text style={styles.mapMilestoneTitle}>{milestone.title}</Text>
              <Text numberOfLines={2} style={styles.mapMilestoneOutcome}>
                {milestone.outcome}
              </Text>
              <Text style={styles.mapMilestoneProgress}>
                {milestone.completed}/{milestone.steps.length} steps complete
                {milestone.isCurrent ? " · You are here" : ""}
              </Text>
            </View>
          </View>
        ))}
      </View>
      {roadmap.milestones.length > 0 ? (
        <Pressable
          accessibilityHint="Shows or hides the details for every milestone"
          accessibilityRole="button"
          accessibilityState={{ expanded: detailedMapExpanded }}
          onPress={() => setDetailedMapExpanded((current) => !current)}
          style={({ pressed }) => [styles.detailToggle, pressed && styles.detailTogglePressed]}
        >
          <View style={styles.inlineRow}>
            <Text style={styles.detailToggleText}>
              {detailedMapExpanded ? "Hide detailed map" : "View detailed map"}
            </Text>
            {detailedMapExpanded ? (
              <ChevronUp color={colors.forest} size={16} strokeWidth={2.6} />
            ) : (
              <ChevronDown color={colors.forest} size={16} strokeWidth={2.6} />
            )}
          </View>
        </Pressable>
      ) : null}
      {detailedMapExpanded ? (
        <View style={styles.detailMap}>
          {roadmap.strategy_summary || roadmap.summary ? (
            <View style={styles.strategyCard}>
              <Text style={styles.detailEyebrow}>How this roadmap works</Text>
              <Text style={styles.strategyText}>{roadmap.strategy_summary || roadmap.summary}</Text>
            </View>
          ) : null}
          {roadmap.suggested_rhythm.length > 0 ? (
            <View style={styles.rhythmCard}>
              <Text style={styles.detailEyebrow}>Suggested rhythm</Text>
              {roadmap.suggested_rhythm.map((item, index) => (
                <View key={`${item}-${index}`} style={styles.rhythmRow}>
                  <Text style={styles.rhythmBullet}>•</Text>
                  <Text style={styles.rhythmText}>{item}</Text>
                </View>
              ))}
            </View>
          ) : null}
          {roadmap.milestones.map((milestone) => {
            const focusAreas = milestone.focus_areas.length > 0
              ? milestone.focus_areas
              : milestone.steps.slice(0, 3).map((step) => step.title);
            const finalStep = milestone.steps[milestone.steps.length - 1];
            const proofTarget = milestone.proof_target || finalStep?.evidence_suggestion;
            const successSignal = milestone.success_signal || finalStep?.completion_condition;
            return (
              <View key={milestone.id} style={styles.detailPhaseCard}>
                <Text style={styles.detailPhaseLabel}>Milestone {milestone.position}</Text>
                <Text style={styles.detailPhaseTitle}>{milestone.title}</Text>
                {focusAreas.length > 0 ? (
                  <View style={styles.focusList}>
                    {focusAreas.map((focus, index) => (
                      <View key={`${focus}-${index}`} style={styles.focusPill}>
                        <Text style={styles.focusPillText}>{focus}</Text>
                      </View>
                    ))}
                  </View>
                ) : null}
                {proofTarget ? (
                <View style={styles.detailItem}>
                  <Text style={styles.detailItemLabel}>Build / prove</Text>
                  <Text style={styles.detailItemText}>{proofTarget}</Text>
                </View>
                ) : null}
                {successSignal ? (
                <View style={styles.detailItem}>
                  <Text style={styles.detailItemLabel}>Checkpoint</Text>
                  <Text style={styles.detailItemText}>{successSignal}</Text>
                </View>
                ) : null}
              </View>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}
