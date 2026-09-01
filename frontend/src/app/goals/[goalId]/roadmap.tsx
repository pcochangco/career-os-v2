import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Image, Linking, Pressable, StyleSheet, Text, View } from "react-native";

import {
  Brand,
  Button,
  colors,
  ErrorState,
  Field,
  LoadingState,
  Screen,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Roadmap, RoadmapStep, StepResources } from "@/lib/types";

const stateLabels: Record<RoadmapStep["progress_status"], string> = {
  completed: "Completed",
  current: "Continue here",
  upcoming: "Upcoming",
  blocked: "Prerequisite needed",
};
const resourceRefreshCooldownMs = 12_000;

export default function RoadmapRoute() {
  const { roadmapId } = useLocalSearchParams<{ goalId: string; roadmapId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState<"work" | "completion" | null>(null);
  const [notes, setNotes] = useState("");
  const [evidenceSummary, setEvidenceSummary] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [completionConfirmed, setCompletionConfirmed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [stepResources, setStepResources] = useState<StepResources | null>(null);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState<string | null>(null);
  const [resourceAttempt, setResourceAttempt] = useState(0);
  const [refreshingResources, setRefreshingResources] = useState(false);
  const [resourceRefreshCoolingDown, setResourceRefreshCoolingDown] = useState(false);
  const [dismissingResourceId, setDismissingResourceId] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !roadmapId) return;
    let active = true;
    setError(null);
    apiRequest<Roadmap>(`/roadmaps/${roadmapId}`, { token })
      .then((value) => active && setRoadmap(value))
      .catch(
        (caught) =>
          active &&
          setError(caught instanceof Error ? caught.message : "Roadmap could not load."),
      );
    return () => {
      active = false;
    };
  }, [attempt, roadmapId, token]);

  const stepNumberById = useMemo(() => {
    const positions = new Map<string, number>();
    let position = 0;
    for (const milestone of roadmap?.milestones ?? []) {
      for (const step of milestone.steps) {
        position += 1;
        positions.set(step.id, position);
      }
    }
    return positions;
  }, [roadmap]);

  const currentStep = useMemo(
    () =>
      roadmap?.milestones
        .flatMap((milestone) => milestone.steps)
        .find((step) => step.id === roadmap.current_step_id) ?? null,
    [roadmap],
  );

  const milestoneProgress = useMemo(
    () =>
      (roadmap?.milestones ?? []).map((milestone) => {
        const completed = milestone.steps.filter(
          (step) => step.progress_status === "completed",
        ).length;
        const isCurrent = milestone.steps.some((step) => step.progress_status === "current");
        return { ...milestone, completed, isCurrent };
      }),
    [roadmap],
  );

  useEffect(() => {
    setNotes(currentStep?.notes ?? "");
    setEvidenceSummary(currentStep?.evidence_summary ?? "");
    setEvidenceUrl(currentStep?.evidence_url ?? "");
    setCompletionConfirmed(false);
    setResourceRefreshCoolingDown(false);
  }, [currentStep?.id]);

  useEffect(() => {
    if (!token || !currentStep || currentStep.resource_queries.length === 0) {
      setStepResources(null);
      setResourcesError(null);
      setResourcesLoading(false);
      return;
    }
    let active = true;
    setStepResources(null);
    setResourcesError(null);
    setResourcesLoading(true);
    apiRequest<StepResources>(`/roadmap-steps/${currentStep.id}/resources/resolve`, {
      method: "POST",
      token,
    })
      .then((value) => active && setStepResources(value))
      .catch(
        (caught) =>
          active &&
          setResourcesError(
            caught instanceof Error ? caught.message : "Resources could not be verified.",
          ),
      )
      .finally(() => active && setResourcesLoading(false));
    return () => {
      active = false;
    };
  }, [currentStep?.id, resourceAttempt, token]);

  async function findAnotherResourceSet() {
    if (!token || !currentStep || refreshingResources) return;
    setRefreshingResources(true);
    setResourcesError(null);
    try {
      const value = await apiRequest<StepResources>(
        `/roadmap-steps/${currentStep.id}/resources/resolve?refresh=true`,
        { method: "POST", token },
      );
      setStepResources(value);
      setResourceRefreshCoolingDown(true);
      setTimeout(() => setResourceRefreshCoolingDown(false), resourceRefreshCooldownMs);
    } catch (caught) {
      setResourcesError(
        caught instanceof Error ? caught.message : "Different resources could not be found.",
      );
    } finally {
      setRefreshingResources(false);
    }
  }

  async function markResourceNotUseful(resourceId: string) {
    if (!token || !currentStep || dismissingResourceId) return;
    setDismissingResourceId(resourceId);
    setResourcesError(null);
    try {
      await apiRequest<void>(
        `/roadmap-steps/${currentStep.id}/resources/${resourceId}/not-useful`,
        { method: "POST", token },
      );
      setStepResources((current) => {
        if (!current) return current;
        const resources = current.resources.filter((resource) => resource.id !== resourceId);
        return {
          ...current,
          available: resources.length > 0,
          message: resources.length
            ? ""
            : "We’ll avoid that recommendation. Find another set whenever you’re ready.",
          resources,
        };
      });
    } catch (caught) {
      setResourcesError(
        caught instanceof Error ? caught.message : "That resource could not be dismissed.",
      );
    } finally {
      setDismissingResourceId(null);
    }
  }

  const workDirty = Boolean(
    currentStep &&
      (notes.trim() !== currentStep.notes ||
        evidenceSummary.trim() !== currentStep.evidence_summary ||
        evidenceUrl.trim() !== currentStep.evidence_url),
  );

  const workPayload = {
    evidence_summary: evidenceSummary,
    evidence_url: evidenceUrl,
    notes,
  };

  async function saveStepWork(step: RoadmapStep) {
    if (!token || step.progress_status !== "current") return;
    setActionError(null);
    setSavingAction("work");
    try {
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Your work could not be saved.");
    } finally {
      setSavingAction(null);
    }
  }

  async function completeStep(step: RoadmapStep) {
    if (!token || step.progress_status !== "current" || !completionConfirmed) return;
    setActionError(null);
    setSavingAction("completion");
    try {
      const saved = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      setRoadmap(saved);
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/progress`, {
        body: { completed: true, completion_confirmed: true },
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Progress could not be saved.");
    } finally {
      setSavingAction(null);
    }
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
  }
  if (!roadmap) return <LoadingState />;

  return (
    <Screen>
      <View style={styles.topBar}>
        <Brand />
        <Pressable accessibilityRole="button" onPress={() => router.push("/goals" as never)}>
          <Text style={styles.goalsLink}>All goals</Text>
        </Pressable>
      </View>
      <Text style={styles.title}>{roadmap.title}</Text>
      <View style={styles.progressHeader}>
        <Text style={styles.progressText}>
          {roadmap.completed_steps} of {roadmap.total_steps} steps
        </Text>
        <Text style={styles.progressPercent}>{roadmap.progress_percent}%</Text>
      </View>
      <View style={styles.progressTrack}>
        <View
          style={[
            styles.progressFill,
            { width: `${roadmap.progress_percent}%` as `${number}%` },
          ]}
        />
      </View>

      {currentStep ? (
        <View style={styles.nextCard}>
          <Text style={styles.nextEyebrow}>Your next move</Text>
          <Text style={styles.nextTitle}>{currentStep.title}</Text>
          <Text numberOfLines={2} style={styles.nextAction}>{currentStep.action}</Text>
          <View style={styles.nextMeta}>
            <Text style={styles.nextMetaText}>Step {stepNumberById.get(currentStep.id)} of {roadmap.total_steps}</Text>
            <Text style={styles.nextMetaText}>{currentStep.effort_label}</Text>
          </View>
        </View>
      ) : null}

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
                  <Text
                    style={[
                      styles.mapNodeText,
                      (milestone.isCurrent || milestone.completed === milestone.steps.length) &&
                        styles.mapNodeTextActive,
                    ]}
                  >
                    {milestone.completed === milestone.steps.length ? "✓" : milestone.position}
                  </Text>
                </View>
                {index < milestoneProgress.length - 1 ? <View style={styles.mapConnector} /> : null}
              </View>
              <View style={styles.mapMilestoneContent}>
                <Text style={styles.mapMilestoneTitle}>{milestone.title}</Text>
                <Text numberOfLines={2} style={styles.mapMilestoneOutcome}>
                  {milestone.outcome}
                </Text>
                <Text style={styles.mapMilestoneProgress}>
                  {milestone.completed}/{milestone.steps.length} missions complete
                  {milestone.isCurrent ? " · You are here" : ""}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {roadmap.current_step_id === null ? (
        <View style={styles.goalComplete}>
          <Text style={styles.goalCompleteEyebrow}>Goal complete</Text>
          <Text style={styles.goalCompleteTitle}>You finished the full roadmap.</Text>
          <Text style={styles.goalCompleteBody}>
            Every step remains below so you can return to the work and materials you used.
          </Text>
        </View>
      ) : null}

      {actionError ? <Text style={styles.actionError}>{actionError}</Text> : null}

      <View style={styles.path}>
        {roadmap.milestones.map((milestone, milestoneIndex) => (
          <View key={milestone.id}>
            <View style={styles.milestoneHeader}>
              <Text style={styles.milestoneLabel}>Milestone {milestone.position}</Text>
              <Text style={styles.milestoneTitle}>{milestone.title}</Text>
              <Text style={styles.milestoneOutcome}>{milestone.outcome}</Text>
            </View>
            {milestone.steps.map((step, stepIndex) => {
              const isCurrent = step.progress_status === "current";
              const isCompleted = step.progress_status === "completed";
              const isBlocked = step.progress_status === "blocked";
              const isLast =
                milestoneIndex === roadmap.milestones.length - 1 &&
                stepIndex === milestone.steps.length - 1;
              const nodeLabel = isCompleted
                ? "✓"
                : isCurrent
                  ? "▶"
                  : isBlocked
                    ? "·"
                    : String(stepNumberById.get(step.id));

              return (
                <View key={step.id} style={styles.pathRow}>
                  <View style={styles.rail}>
                    <View
                      style={[
                        styles.node,
                        isCurrent && styles.nodeCurrent,
                        isCompleted && styles.nodeCompleted,
                        isBlocked && styles.nodeBlocked,
                      ]}
                    >
                      <Text
                        style={[
                          styles.nodeLabel,
                          (isCurrent || isCompleted) && styles.nodeLabelActive,
                        ]}
                      >
                        {nodeLabel}
                      </Text>
                    </View>
                    {!isLast ? (
                      <View style={[styles.connector, isCompleted && styles.connectorCompleted]} />
                    ) : null}
                  </View>
                  <View
                    style={[
                      styles.stepCard,
                      isCurrent && styles.currentCard,
                      isCompleted && styles.completedCard,
                      isBlocked && styles.blockedCard,
                    ]}
                  >
                    <View style={styles.missionMeta}>
                      <Text style={styles.missionKind}>{step.kind}</Text>
                      <Text style={[styles.stateLabel, isCurrent && styles.currentState]}>
                        {stateLabels[step.progress_status]}
                      </Text>
                    </View>
                    <Text style={styles.stepTitle}>{step.title}</Text>
                    {isCompleted &&
                    (step.notes || step.evidence_summary || step.evidence_url) ? (
                      <View style={styles.savedWork}>
                        <Text style={styles.savedWorkLabel}>Your saved work</Text>
                        {step.notes ? <Text style={styles.savedWorkText}>{step.notes}</Text> : null}
                        {step.evidence_summary ? (
                          <Text style={styles.savedWorkText}>{step.evidence_summary}</Text>
                        ) : null}
                        {step.evidence_url ? (
                          <Pressable
                            accessibilityRole="link"
                            onPress={() => void Linking.openURL(step.evidence_url)}
                          >
                            <Text style={styles.savedWorkLink}>Open evidence ↗</Text>
                          </Pressable>
                        ) : null}
                      </View>
                    ) : null}
                    {isCurrent ? (
                      <>
                        <Text style={styles.objective}>{step.objective}</Text>
                        <View style={styles.actionBox}>
                          <Text style={styles.actionLabel}>Do this now</Text>
                          <Text style={styles.actionText}>{step.action}</Text>
                        </View>
                        {step.resource_queries.length ? (
                          <View style={styles.resources}>
                            <View style={styles.resourceHeading}>
                              <Text style={styles.resourceLabel}>Recommended resources</Text>
                              <Text style={styles.verifiedLabel}>Fresh source checks</Text>
                            </View>
                            {resourcesLoading ? (
                              <View style={styles.resourceNotice}>
                                <Text style={styles.resourceNoticeText}>
                                  Finding and checking useful material…
                                </Text>
                              </View>
                            ) : null}
                            {!resourcesLoading && stepResources?.available
                              ? stepResources.resources.map((resource, resourceIndex) => {
                                  const isPrimaryVideo =
                                    resource.resource_type === "video" &&
                                    resourceIndex ===
                                      stepResources.resources.findIndex(
                                        (item) => item.resource_type === "video",
                                      );
                                  return (
                                  <View key={resource.id} style={styles.resourceCardShell}>
                                    <Pressable
                                      accessibilityHint={
                                        isPrimaryVideo
                                          ? "Opens the primary video course or tutorial"
                                          : "Opens this recommended resource"
                                      }
                                      accessibilityRole="link"
                                      onPress={() => void Linking.openURL(resource.url)}
                                      style={({ pressed }) => [
                                        styles.resourceCard,
                                        isPrimaryVideo && styles.primaryVideoCard,
                                        pressed && styles.resourceLinkPressed,
                                      ]}
                                    >
                                      {isPrimaryVideo && resource.thumbnail_url ? (
                                        <Image
                                          accessibilityLabel={`${resource.title} video thumbnail`}
                                          source={{ uri: resource.thumbnail_url }}
                                          style={styles.courseThumbnail}
                                        />
                                      ) : null}
                                      <View style={styles.resourceMeta}>
                                        <Text style={styles.resourceType}>
                                          {isPrimaryVideo ? "Start here · video course" : resource.resource_type}
                                        </Text>
                                        <Text style={styles.resourceSource}>
                                          {resource.source_name}
                                        </Text>
                                      </View>
                                      <Text style={styles.resourceTitle}>{resource.title}</Text>
                                      {resource.description ? (
                                        <Text numberOfLines={3} style={styles.resourceDescription}>
                                          {resource.description}
                                        </Text>
                                      ) : null}
                                      <Text style={styles.resourceReason}>
                                        Why this fits: {resource.why_relevant}
                                      </Text>
                                      <Text style={styles.resourceOpen}>
                                        {isPrimaryVideo ? "Watch free course ↗" : "Open resource ↗"}
                                      </Text>
                                    </Pressable>
                                    <Pressable
                                      accessibilityHint="Removes this resource and prevents it appearing again for this step"
                                      accessibilityRole="button"
                                      disabled={dismissingResourceId !== null}
                                      onPress={() => void markResourceNotUseful(resource.id)}
                                      style={({ pressed }) => [
                                        styles.notUseful,
                                        (pressed || dismissingResourceId === resource.id) &&
                                          styles.resourceLinkPressed,
                                      ]}
                                    >
                                      <Text style={styles.notUsefulText}>
                                        {dismissingResourceId === resource.id
                                          ? "Removing…"
                                          : "Not useful for me"}
                                      </Text>
                                    </Pressable>
                                  </View>
                                  );
                                })
                              : null}
                            {!resourcesLoading && stepResources?.available ? (
                              <Pressable
                                accessibilityHint="Finds different relevant courses and resources"
                                accessibilityRole="button"
                                disabled={refreshingResources || resourceRefreshCoolingDown}
                                onPress={() => void findAnotherResourceSet()}
                                style={({ pressed }) => [
                                  styles.findAnother,
                                  (pressed || refreshingResources || resourceRefreshCoolingDown) &&
                                    styles.resourceLinkPressed,
                                ]}
                              >
                                <Text style={styles.findAnotherText}>
                                  {refreshingResources
                                    ? "Finding another set…"
                                    : resourceRefreshCoolingDown
                                      ? "More alternatives in a few seconds"
                                      : "Not your style? Find another"}
                                </Text>
                              </Pressable>
                            ) : null}
                            {!resourcesLoading &&
                            (resourcesError || (stepResources && !stepResources.available)) ? (
                              <View style={styles.resourceNotice}>
                                <Text style={styles.resourceNoticeText}>
                                  {resourcesError ?? stepResources?.message}
                                </Text>
                                <Pressable
                                  accessibilityRole="button"
                                  onPress={() => setResourceAttempt((value) => value + 1)}
                                >
                                  <Text style={styles.resourceRetry}>Try again</Text>
                                </Pressable>
                              </View>
                            ) : null}
                          </View>
                        ) : null}
                        <Text style={styles.completeLabel}>Complete when</Text>
                        <Text style={styles.completeText}>{step.completion_condition}</Text>
                        {step.evidence_suggestion ? (
                          <Text style={styles.evidence}>Keep: {step.evidence_suggestion}</Text>
                        ) : null}
                        <Text style={styles.effort}>{step.effort_label} · no deadline</Text>
                        <View style={styles.workSection}>
                          <Text style={styles.workTitle}>Your learning record</Text>
                          <Text style={styles.workIntro}>
                            Keep anything useful for returning to this work or showing it later.
                          </Text>
                          <Field
                            accessibilityLabel="Notes or reflections"
                            maxLength={4000}
                            multiline
                            onChangeText={setNotes}
                            placeholder="Notes or reflections (optional)"
                            style={styles.workField}
                            value={notes}
                          />
                          <Field
                            accessibilityLabel="Output or evidence summary"
                            maxLength={1000}
                            multiline
                            onChangeText={setEvidenceSummary}
                            placeholder="What did you produce? (optional)"
                            style={styles.workField}
                            value={evidenceSummary}
                          />
                          <Field
                            accessibilityLabel="Evidence link"
                            autoCapitalize="none"
                            autoCorrect={false}
                            keyboardType="url"
                            maxLength={2048}
                            onChangeText={setEvidenceUrl}
                            placeholder="https://… evidence link (optional)"
                            style={styles.linkField}
                            value={evidenceUrl}
                          />
                          <View style={styles.saveRow}>
                            <View style={styles.saveButton}>
                              <Button
                                disabled={!workDirty || savingAction !== null}
                                loading={savingAction === "work"}
                                onPress={() => void saveStepWork(step)}
                                secondary
                              >
                                Save record
                              </Button>
                            </View>
                            {!workDirty && step.work_updated_at ? (
                              <Text style={styles.savedLabel}>Saved</Text>
                            ) : null}
                          </View>
                        </View>
                        <Pressable
                          accessibilityRole="checkbox"
                          accessibilityState={{ checked: completionConfirmed }}
                          onPress={() => setCompletionConfirmed((value) => !value)}
                          style={styles.confirmationRow}
                        >
                          <View
                            style={[
                              styles.checkbox,
                              completionConfirmed && styles.checkboxChecked,
                            ]}
                          >
                            {completionConfirmed ? (
                              <Text style={styles.checkboxMark}>✓</Text>
                            ) : null}
                          </View>
                          <Text style={styles.confirmationText}>
                            I met this step’s completion condition.
                          </Text>
                        </Pressable>
                        <View style={styles.completeButton}>
                          <Button
                            disabled={!completionConfirmed || savingAction !== null}
                            loading={savingAction === "completion"}
                            onPress={() => void completeStep(step)}
                          >
                            Complete this step
                          </Button>
                        </View>
                      </>
                    ) : null}
                  </View>
                </View>
              );
            })}
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  topBar: { alignItems: "flex-start", flexDirection: "row", justifyContent: "space-between" },
  goalsLink: { color: colors.forest, fontSize: 15, fontWeight: "800", paddingVertical: 2 },
  title: {
    color: colors.ink,
    fontSize: 29,
    fontWeight: "800",
    letterSpacing: -0.5,
    lineHeight: 35,
  },
  progressHeader: { flexDirection: "row", justifyContent: "space-between", marginTop: 18 },
  progressText: { color: colors.muted, fontSize: 14 },
  progressPercent: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  progressTrack: {
    backgroundColor: colors.line,
    borderRadius: 4,
    height: 7,
    marginBottom: 32,
    marginTop: 9,
    overflow: "hidden",
  },
  progressFill: { backgroundColor: colors.forest, borderRadius: 4, height: 7 },
  nextCard: {
    backgroundColor: colors.forest,
    borderRadius: 20,
    marginBottom: 16,
    padding: 18,
  },
  nextEyebrow: { color: "#D8E9DC", fontSize: 11, fontWeight: "900", textTransform: "uppercase" },
  nextTitle: { color: colors.white, fontSize: 19, fontWeight: "800", lineHeight: 25, marginTop: 5 },
  nextAction: { color: "#EDF6EF", fontSize: 14, lineHeight: 20, marginTop: 7 },
  nextMeta: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 14 },
  nextMetaText: { color: "#D8E9DC", fontSize: 11, fontWeight: "800" },
  mapCard: {
    backgroundColor: colors.forestSoft,
    borderColor: "#C7D9CB",
    borderRadius: 20,
    borderWidth: 1,
    marginBottom: 30,
    padding: 18,
  },
  mapEyebrow: { color: colors.forest, fontSize: 11, fontWeight: "800", textTransform: "uppercase" },
  mapTitle: { color: colors.ink, fontSize: 17, fontWeight: "800", lineHeight: 23, marginTop: 5 },
  mapBody: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 5 },
  mapMilestones: { marginTop: 17 },
  mapMilestoneRow: { flexDirection: "row", minHeight: 76 },
  mapRail: { alignItems: "center", width: 33 },
  mapNode: {
    alignItems: "center", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 15,
    borderWidth: 2, height: 30, justifyContent: "center", width: 30,
  },
  mapNodeCurrent: { backgroundColor: colors.forest, borderColor: colors.forest },
  mapNodeCompleted: { backgroundColor: colors.forest, borderColor: colors.forest },
  mapNodeText: { color: colors.muted, fontSize: 12, fontWeight: "900" },
  mapNodeTextActive: { color: colors.white },
  mapConnector: { backgroundColor: "#B8CFBD", flex: 1, marginVertical: 3, width: 2 },
  mapMilestoneContent: { flex: 1, paddingBottom: 14, paddingLeft: 10 },
  mapMilestoneTitle: { color: colors.ink, fontSize: 15, fontWeight: "800", lineHeight: 20 },
  mapMilestoneOutcome: { color: colors.muted, fontSize: 12, lineHeight: 18, marginTop: 2 },
  mapMilestoneProgress: { color: colors.forestDark, fontSize: 11, fontWeight: "800", marginTop: 5 },
  goalComplete: {
    backgroundColor: colors.forestSoft,
    borderRadius: 18,
    marginBottom: 28,
    padding: 20,
  },
  goalCompleteEyebrow: {
    color: colors.forest,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  goalCompleteTitle: { color: colors.ink, fontSize: 21, fontWeight: "800", marginTop: 6 },
  goalCompleteBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 6 },
  actionError: { color: "#A13B32", fontSize: 14, marginBottom: 22 },
  path: { gap: 30 },
  milestoneHeader: { marginBottom: 15, marginLeft: 68 },
  milestoneLabel: {
    color: colors.forest,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  milestoneTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", marginTop: 4 },
  milestoneOutcome: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 5 },
  pathRow: { alignItems: "stretch", flexDirection: "row", minHeight: 100 },
  rail: { alignItems: "center", width: 54 },
  node: {
    alignItems: "center",
    backgroundColor: "#E7ECE8",
    borderColor: colors.line,
    borderRadius: 24,
    borderWidth: 2,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  nodeCurrent: {
    backgroundColor: colors.forest,
    borderColor: colors.forestDark,
    shadowColor: colors.forest,
    shadowOpacity: 0.2,
    shadowRadius: 8,
  },
  nodeCompleted: { backgroundColor: colors.forest, borderColor: colors.forest },
  nodeBlocked: { opacity: 0.62 },
  nodeLabel: { color: colors.muted, fontSize: 13, fontWeight: "800" },
  nodeLabelActive: { color: colors.white, fontSize: 15 },
  connector: { backgroundColor: colors.line, flex: 1, minHeight: 28, width: 3 },
  connectorCompleted: { backgroundColor: colors.forest },
  stepCard: {
    backgroundColor: "#F0F3F0",
    borderColor: colors.line,
    borderRadius: 18,
    borderWidth: 1,
    flex: 1,
    marginBottom: 18,
    marginLeft: 14,
    padding: 18,
  },
  currentCard: { backgroundColor: colors.card, borderColor: colors.forest, borderWidth: 2 },
  completedCard: { backgroundColor: colors.card },
  blockedCard: { opacity: 0.68 },
  missionMeta: { alignItems: "center", flexDirection: "row", gap: 8, marginBottom: 7 },
  missionKind: {
    backgroundColor: colors.forestSoft, borderRadius: 99, color: colors.forestDark, fontSize: 10,
    fontWeight: "900", overflow: "hidden", paddingHorizontal: 8, paddingVertical: 4, textTransform: "uppercase",
  },
  stateLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  currentState: { color: colors.forest },
  stepTitle: { color: colors.ink, fontSize: 18, fontWeight: "800", lineHeight: 24 },
  objective: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 8 },
  actionBox: { backgroundColor: colors.forestSoft, borderRadius: 14, marginTop: 16, padding: 14 },
  actionLabel: {
    color: colors.forestDark,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  actionText: { color: colors.forestDark, fontSize: 14, lineHeight: 21, marginTop: 5 },
  resources: { gap: 10, marginTop: 18 },
  resourceHeading: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  resourceLabel: {
    color: colors.ink,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  verifiedLabel: { color: colors.forest, fontSize: 11, fontWeight: "700" },
  resourceCard: {
    backgroundColor: colors.background,
    borderColor: colors.line,
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
  },
  resourceCardShell: { gap: 7 },
  primaryVideoCard: { backgroundColor: colors.card, borderColor: colors.forest, borderWidth: 2, padding: 12 },
  courseThumbnail: { backgroundColor: colors.line, borderRadius: 10, height: 154, marginBottom: 12, width: "100%" },
  resourceLinkPressed: { opacity: 0.72 },
  resourceMeta: { alignItems: "center", flexDirection: "row", gap: 8 },
  resourceType: {
    backgroundColor: colors.forestSoft,
    borderRadius: 99,
    color: colors.forestDark,
    fontSize: 10,
    fontWeight: "800",
    overflow: "hidden",
    paddingHorizontal: 8,
    paddingVertical: 4,
    textTransform: "uppercase",
  },
  resourceSource: { color: colors.muted, fontSize: 11, fontWeight: "700" },
  resourceTitle: {
    color: colors.ink,
    fontSize: 15,
    fontWeight: "800",
    lineHeight: 21,
    marginTop: 9,
  },
  resourceDescription: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 5 },
  resourceReason: { color: colors.forestDark, fontSize: 12, lineHeight: 18, marginTop: 9 },
  resourceOpen: { color: colors.forest, fontSize: 12, fontWeight: "800", marginTop: 10 },
  findAnother: {
    alignItems: "center",
    borderColor: colors.line,
    borderRadius: 12,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 42,
    paddingHorizontal: 12,
  },
  findAnotherText: { color: colors.forest, fontSize: 13, fontWeight: "800" },
  notUseful: { alignSelf: "flex-start", minHeight: 30, paddingHorizontal: 2, paddingVertical: 4 },
  notUsefulText: { color: colors.muted, fontSize: 12, fontWeight: "700" },
  resourceNotice: {
    backgroundColor: colors.background,
    borderColor: colors.line,
    borderRadius: 12,
    borderWidth: 1,
    gap: 7,
    padding: 13,
  },
  resourceNoticeText: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  resourceRetry: { color: colors.forest, fontSize: 13, fontWeight: "800" },
  completeLabel: {
    color: colors.ink,
    fontSize: 12,
    fontWeight: "800",
    marginTop: 16,
    textTransform: "uppercase",
  },
  completeText: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 4 },
  evidence: { color: colors.muted, fontSize: 13, fontStyle: "italic", marginTop: 12 },
  effort: { color: colors.forest, fontSize: 12, fontWeight: "700", marginTop: 14 },
  savedWork: {
    backgroundColor: colors.forestSoft,
    borderRadius: 12,
    gap: 6,
    marginTop: 13,
    padding: 13,
  },
  savedWorkLabel: {
    color: colors.forestDark,
    fontSize: 11,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  savedWorkText: { color: colors.forestDark, fontSize: 13, lineHeight: 19 },
  savedWorkLink: { color: colors.forest, fontSize: 13, fontWeight: "800", marginTop: 2 },
  workSection: {
    borderTopColor: colors.line,
    borderTopWidth: 1,
    marginTop: 20,
    paddingTop: 18,
  },
  workTitle: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  workIntro: { color: colors.muted, fontSize: 13, lineHeight: 19, marginBottom: 13, marginTop: 4 },
  workField: { fontSize: 15, lineHeight: 22, marginBottom: 10, minHeight: 94 },
  linkField: { fontSize: 15, marginBottom: 10, minHeight: 50 },
  saveRow: { alignItems: "center", flexDirection: "row", gap: 12 },
  saveButton: { minWidth: 154 },
  savedLabel: { color: colors.forest, fontSize: 13, fontWeight: "800" },
  confirmationRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    marginTop: 20,
    minHeight: 44,
  },
  checkbox: {
    alignItems: "center",
    backgroundColor: colors.card,
    borderColor: colors.muted,
    borderRadius: 7,
    borderWidth: 2,
    height: 25,
    justifyContent: "center",
    width: 25,
  },
  checkboxChecked: { backgroundColor: colors.forest, borderColor: colors.forest },
  checkboxMark: { color: colors.white, fontSize: 16, fontWeight: "900" },
  confirmationText: { color: colors.ink, flex: 1, fontSize: 14, fontWeight: "700", lineHeight: 20 },
  completeButton: { marginTop: 18 },
});
