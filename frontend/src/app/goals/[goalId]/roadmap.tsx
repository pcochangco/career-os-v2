import { useLocalSearchParams, useRouter } from "expo-router";
import { ComponentRef, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  ExternalLink,
  Play,
  X,
} from "@/components/icons";
import { Image, Linking, Pressable, ScrollView, Text, View } from "react-native";

import {
  AppHeader,
  Button,
  ErrorState,
  Field,
  LockGlyph,
  Screen,
  ThumbDownGlyph,
} from "@/components/ui";
import { AskAboutPremium } from "@/components/plan-limit";
import {
  AUTOSAVE_DELAY_MS,
  isValidEvidenceLink,
  learningRecordFor,
  resourceRefreshCooldownMs,
  resourceUndoWindowMs,
  stateLabels,
} from "@/components/roadmap/helpers";
import { MilestoneMap } from "@/components/roadmap/milestone-map";
import { PracticeCard } from "@/components/roadmap/practice-card";
import { createRoadmapStyles } from "@/components/roadmap/styles";
import { RoadmapSkeleton } from "@/components/skeleton";
import { apiRequest } from "@/lib/api";
import { clearDraft, readDraft, writeDraft } from "@/lib/drafts";
import { useSession } from "@/lib/session";
import { LearningResource, Roadmap, RoadmapStep, StepResources } from "@/lib/types";
import { useTheme } from "@/lib/theme";

export default function RoadmapRoute() {
  const { colors } = useTheme();
  const styles = useMemo(() => createRoadmapStyles(colors), [colors]);
  const { roadmapId } = useLocalSearchParams<{ goalId: string; roadmapId: string }>();
  const router = useRouter();
  const { token } = useSession();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState<"work" | "completion" | "practice" | null>(null);
  const [learningRecord, setLearningRecord] = useState("");
  const [evidenceLink, setEvidenceLink] = useState("");
  const [stepError, setStepError] = useState<string | null>(null);
  const [practiceError, setPracticeError] = useState<string | null>(null);
  const [autosaveState, setAutosaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  // The step whose saved work is loaded into the editor. Autosave waits for this so the first
  // render (empty fields, before loading) can never be mistaken for the user clearing their work.
  const [editorStepId, setEditorStepId] = useState<string | null>(null);
  const [completionConfirmed, setCompletionConfirmed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [stepResources, setStepResources] = useState<StepResources | null>(null);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [resourcesError, setResourcesError] = useState<string | null>(null);
  const [resourceAttempt, setResourceAttempt] = useState(0);
  const [refreshingResources, setRefreshingResources] = useState(false);
  const [resourceRefreshCoolingDown, setResourceRefreshCoolingDown] = useState(false);
  const [dismissingResourceId, setDismissingResourceId] = useState<string | null>(null);
  const [restoringResource, setRestoringResource] = useState(false);
  const [dismissedResource, setDismissedResource] = useState<{
    index: number;
    resource: LearningResource;
    stepId: string;
  } | null>(null);
  const [completionNotice, setCompletionNotice] = useState<string | null>(null);
  const [expandedMilestoneIds, setExpandedMilestoneIds] = useState<Set<string>>(new Set());
  const [practiceTaskOffset, setPracticeTaskOffset] = useState(0);
  const scrollViewRef = useRef<ComponentRef<typeof ScrollView>>(null);
  const resourceUndoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pathOffset, setPathOffset] = useState<number | null>(null);
  const [currentMilestoneOffset, setCurrentMilestoneOffset] = useState<number | null>(null);
  const [currentRowOffset, setCurrentRowOffset] = useState<number | null>(null);
  const currentStepOffset =
    pathOffset === null || currentMilestoneOffset === null || currentRowOffset === null
      ? null
      : pathOffset + currentMilestoneOffset + currentRowOffset;

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

  const practiceTasks = useMemo(() => {
    if ((roadmap?.practice_tasks.length ?? 0) > 0) return roadmap!.practice_tasks;
    return (roadmap?.milestones ?? [])
      .flatMap((milestone) => milestone.steps)
      .slice(0, 5)
      .map((step) => ({
        title: `Practice: ${step.title}`,
        instruction: `Choose one small, self-contained part of this step: ${step.objective}`,
        completion_signal: `Keep a short note or artifact: ${step.evidence_suggestion}`,
      }));
  }, [roadmap]);
  const todayPracticeIndex = useMemo(() => {
    if (practiceTasks.length === 0) return 0;
    const dayKey = Math.floor(Date.now() / 86_400_000);
    return (dayKey + practiceTaskOffset) % practiceTasks.length;
  }, [practiceTaskOffset, practiceTasks.length]);
  const todayPractice = practiceTasks[todayPracticeIndex];

  useEffect(() => {
    const currentMilestone = roadmap?.milestones.find((milestone) =>
      milestone.steps.some((step) => step.progress_status === "current"),
    );
    if (!currentMilestone) return;
    setExpandedMilestoneIds((current) => {
      if (current.has(currentMilestone.id)) return current;
      return new Set(current).add(currentMilestone.id);
    });
  }, [roadmap?.current_step_id, roadmap?.id]);

  async function completeTodayPractice() {
    if (!roadmap || !token || roadmap.practice_completed_today || savingAction) return;
    setPracticeError(null);
    setSavingAction("practice");
    try {
      const updated = await apiRequest<Roadmap>(`/roadmaps/${roadmap.id}/practice/today`, {
        method: "PUT",
        token,
      });
      setRoadmap(updated);
    } catch (caught) {
      setPracticeError(caught instanceof Error ? caught.message : "Practice couldn’t be saved. Please try again.");
    } finally {
      setSavingAction(null);
    }
  }

  function toggleMilestone(milestoneId: string) {
    setExpandedMilestoneIds((current) => {
      const next = new Set(current);
      if (next.has(milestoneId)) next.delete(milestoneId);
      else next.add(milestoneId);
      return next;
    });
  }

  useEffect(() => {
    const draft = currentStep ? readDraft(`step-work.${currentStep.id}`) : null;
    let restored: { notes: string; link: string } | null = null;
    try {
      restored = draft ? (JSON.parse(draft) as { notes: string; link: string }) : null;
    } catch {
      restored = null;
    }
    // Only an unsaved draft with content may replace what the server has.
    if (restored && !restored.notes?.trim() && !restored.link?.trim()) {
      if (currentStep) clearDraft(`step-work.${currentStep.id}`);
      restored = null;
    }
    setLearningRecord(restored?.notes ?? learningRecordFor(currentStep));
    setEvidenceLink(restored?.link ?? currentStep?.evidence_url ?? "");
    setEditorStepId(currentStep?.id ?? null);
    setAutosaveState("idle");
    setStepError(null);
    setCompletionConfirmed(false);
    setResourceRefreshCoolingDown(false);
    setDismissedResource(null);
    if (resourceUndoTimerRef.current) clearTimeout(resourceUndoTimerRef.current);
  }, [currentStep?.id]);

  useEffect(
    () => () => {
      if (resourceUndoTimerRef.current) clearTimeout(resourceUndoTimerRef.current);
    },
    [],
  );

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
    const resourceIndex = stepResources?.resources.findIndex(
      (resource) => resource.id === resourceId,
    ) ?? -1;
    const resource = resourceIndex >= 0 ? stepResources?.resources[resourceIndex] : null;
    if (!resource) return;
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
      if (resourceUndoTimerRef.current) clearTimeout(resourceUndoTimerRef.current);
      setDismissedResource({ index: resourceIndex, resource, stepId: currentStep.id });
      resourceUndoTimerRef.current = setTimeout(() => {
        setDismissedResource(null);
        resourceUndoTimerRef.current = null;
      }, resourceUndoWindowMs);
    } catch (caught) {
      setResourcesError(
        caught instanceof Error ? caught.message : "That resource could not be dismissed.",
      );
    } finally {
      setDismissingResourceId(null);
    }
  }

  async function undoResourceDismissal() {
    if (!token || !dismissedResource || restoringResource) return;
    setRestoringResource(true);
    setResourcesError(null);
    try {
      await apiRequest<void>(
        `/roadmap-steps/${dismissedResource.stepId}/resources/${dismissedResource.resource.id}/not-useful`,
        { method: "DELETE", token },
      );
      setStepResources((current) => {
        if (!current || current.step_id !== dismissedResource.stepId) return current;
        const resources = [...current.resources];
        resources.splice(Math.min(dismissedResource.index, resources.length), 0, dismissedResource.resource);
        return { ...current, available: true, message: "", resources };
      });
      setDismissedResource(null);
      if (resourceUndoTimerRef.current) clearTimeout(resourceUndoTimerRef.current);
      resourceUndoTimerRef.current = null;
    } catch (caught) {
      setResourcesError(
        caught instanceof Error ? caught.message : "That resource could not be restored.",
      );
    } finally {
      setRestoringResource(false);
    }
  }

  const workDirty = Boolean(
    currentStep &&
      (learningRecord.trim() !== learningRecordFor(currentStep) ||
        evidenceLink.trim() !== (currentStep.evidence_url ?? "").trim()),
  );
  const evidenceLinkValid = isValidEvidenceLink(evidenceLink);

  const workPayload = {
    evidence_summary: "",
    evidence_url: evidenceLink.trim(),
    notes: learningRecord,
  };

  async function saveStepWork(step: RoadmapStep) {
    if (!token || step.progress_status !== "current" || !evidenceLinkValid) return;
    setAutosaveState("saving");
    try {
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      clearDraft(`step-work.${step.id}`);
      setRoadmap(updated);
      setAutosaveState("saved");
    } catch {
      // The draft stays on this device, so nothing typed is lost; the next edit retries.
      setAutosaveState("error");
    }
  }

  // Keep a local draft while typing and save to the server shortly after the user pauses.
  useEffect(() => {
    if (!currentStep || currentStep.progress_status !== "current" || !workDirty) return;
    if (editorStepId !== currentStep.id) return;
    writeDraft(
      `step-work.${currentStep.id}`,
      JSON.stringify({ notes: learningRecord, link: evidenceLink }),
    );
    if (!evidenceLinkValid) return;
    const timer = setTimeout(() => void saveStepWork(currentStep), AUTOSAVE_DELAY_MS);
    return () => clearTimeout(timer);
    // saveStepWork reads the latest state through workPayload on each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learningRecord, evidenceLink, currentStep?.id, editorStepId, workDirty, evidenceLinkValid]);

  async function completeStep(step: RoadmapStep) {
    if (!token || step.progress_status !== "current" || !completionConfirmed) return;
    if (!evidenceLinkValid) {
      setStepError("Fix the evidence link (it should start with https://) or clear it first.");
      return;
    }
    setStepError(null);
    setSavingAction("completion");
    try {
      const saved = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/work`, {
        body: workPayload,
        method: "PUT",
        token,
      });
      clearDraft(`step-work.${step.id}`);
      setRoadmap(saved);
      const updated = await apiRequest<Roadmap>(`/roadmap-steps/${step.id}/progress`, {
        body: { completed: true, completion_confirmed: true },
        method: "PUT",
        token,
      });
      setRoadmap(updated);
      const nextStep = updated.milestones
        .flatMap((milestone) => milestone.steps)
        .find((candidate) => candidate.progress_status === "current");
      setCompletionNotice(
        nextStep
          ? `Nice work. Your next step, “${nextStep.title},” is ready when you are.`
          : "Nice work. You completed the final step in this roadmap.",
      );
      scrollViewRef.current?.scrollTo({ animated: true, y: 0 });
    } catch (caught) {
      setStepError(
        caught instanceof Error
          ? caught.message
          : "Your progress couldn’t be saved. Your notes are kept; please try again.",
      );
    } finally {
      setSavingAction(null);
    }
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => setAttempt((value) => value + 1)} />;
  }
  if (!roadmap) return <RoadmapSkeleton />;

  return (
    <Screen scrollViewRef={scrollViewRef}>
      <AppHeader />
      <Pressable
        accessibilityRole="link"
        onPress={() => router.push("/goals" as never)}
        style={styles.backLink}
      >
        <ChevronLeft color={colors.muted} size={16} strokeWidth={2.2} />
        <Text style={styles.goalsLink}>All goals</Text>
      </Pressable>
      <Text accessibilityRole="header" style={styles.title}>{roadmap.title}</Text>
      {completionNotice ? (
        <View accessibilityLiveRegion="polite" style={styles.completionNotice}>
          <View style={styles.completionNoticeCopy}>
            <Text style={styles.completionNoticeLabel}>Step complete</Text>
            <Text style={styles.completionNoticeText}>{completionNotice}</Text>
          </View>
          <Pressable
            accessibilityLabel="Dismiss completion message"
            accessibilityRole="button"
            onPress={() => setCompletionNotice(null)}
            style={styles.iconButton}
          >
            <X color={colors.forestDark} size={22} strokeWidth={2.2} />
          </Pressable>
        </View>
      ) : null}
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
        <Pressable
          accessibilityHint="Moves to the current step and its recommended resources"
          accessibilityRole="button"
          onPress={() => currentStepOffset !== null && scrollViewRef.current?.scrollTo({ y: currentStepOffset - 16, animated: true })}
          style={({ pressed }) => [styles.nextCard, pressed && styles.nextCardPressed]}
        >
          <Text style={styles.nextEyebrow}>Your next move</Text>
          <Text style={styles.nextTitle}>{currentStep.title}</Text>
          <Text numberOfLines={2} style={styles.nextAction}>{currentStep.action}</Text>
          <View style={styles.nextMeta}>
            <Text style={styles.nextMetaText}>Step {stepNumberById.get(currentStep.id)} of {roadmap.total_steps}</Text>
            <Text style={styles.nextMetaText}>{currentStep.effort_label}</Text>
          </View>
          <View style={styles.inlineRow}>
            <Text style={styles.nextOpen}>Open current step</Text>
            <ChevronDown color={colors.onForest} size={16} strokeWidth={2.6} />
          </View>
        </Pressable>
      ) : null}

      <MilestoneMap roadmap={roadmap} styles={styles} />

      {roadmap.status === "accepted" && todayPractice ? (
        <PracticeCard
          error={practiceError}
          hasAlternatives={practiceTasks.length > 1}
          onComplete={completeTodayPractice}
          onShowAnother={() => setPracticeTaskOffset((value) => value + 1)}
          practicedToday={roadmap.practice_completed_today}
          saving={savingAction === "practice"}
          styles={styles}
          task={todayPractice}
        />
      ) : null}

      {roadmap.locked_step_count > 0 ? (
        <View style={styles.premiumCard}>
          <Text style={styles.premiumEyebrow}>Free plan</Text>
          <Text style={styles.premiumTitle}>Your first milestone is included.</Text>
          <Text style={styles.premiumBody}>
            You can see the whole roadmap. The next
            {roadmap.locked_step_count === 1 ? " step is" : ` ${roadmap.locked_step_count} steps are`}{" "}
            part of Premium, which isn’t available to buy yet.
          </Text>
          <AskAboutPremium topic="roadmap" />
        </View>
      ) : null}

      {roadmap.current_step_id === null && roadmap.locked_step_count === 0 ? (
        <View style={styles.goalComplete}>
          <Text style={styles.goalCompleteEyebrow}>Goal complete</Text>
          <Text style={styles.goalCompleteTitle}>You finished the full roadmap.</Text>
          <Text style={styles.goalCompleteBody}>
            Every step remains below so you can return to the work and materials you used.
          </Text>
        </View>
      ) : null}


      <View onLayout={(event) => setPathOffset(event.nativeEvent.layout.y)} style={styles.path}>
        {roadmap.milestones.map((milestone, milestoneIndex) => (
          <View
            key={milestone.id}
            onLayout={
              milestone.steps.some((step) => step.progress_status === "current")
                ? (event) => setCurrentMilestoneOffset(event.nativeEvent.layout.y)
                : undefined
            }
          >
            <Pressable
              accessibilityHint="Expands or collapses this milestone"
              accessibilityRole="button"
              accessibilityState={{ expanded: expandedMilestoneIds.has(milestone.id) }}
              onPress={() => toggleMilestone(milestone.id)}
              style={({ pressed }) => [styles.milestoneHeader, pressed && styles.milestoneHeaderPressed]}
            >
              <View style={styles.milestoneHeaderTopline}>
                <Text style={styles.milestoneLabel}>Milestone {milestone.position}</Text>
                <View style={styles.inlineRow}>
                  <Text style={styles.milestoneToggle}>
                    {expandedMilestoneIds.has(milestone.id) ? "Hide steps" : "Show steps"}
                  </Text>
                  {expandedMilestoneIds.has(milestone.id) ? (
                    <ChevronUp color={colors.forest} size={15} strokeWidth={2.6} />
                  ) : (
                    <ChevronDown color={colors.forest} size={15} strokeWidth={2.6} />
                  )}
                </View>
              </View>
              <Text style={styles.milestoneTitle}>{milestone.title}</Text>
              <Text style={styles.milestoneOutcome}>{milestone.outcome}</Text>
              <Text style={styles.milestoneSummary}>
                {milestone.steps.filter((step) => step.progress_status === "completed").length}/
                {milestone.steps.length} complete
                {milestone.steps.some((step) => step.progress_status === "current") ? " · In progress" : ""}
              </Text>
            </Pressable>
            {(expandedMilestoneIds.has(milestone.id) ||
              milestone.steps.some((step) => step.progress_status === "current")) &&
              milestone.steps.map((step, stepIndex) => {
              const isCurrent = step.progress_status === "current";
              const isCompleted = step.progress_status === "completed";
              const isBlocked = step.progress_status === "blocked";
              const isLocked = step.progress_status === "locked";
              const isLast =
                milestoneIndex === roadmap.milestones.length - 1 &&
                stepIndex === milestone.steps.length - 1;
              const nodeLabel = isBlocked ? "·" : String(stepNumberById.get(step.id));

              return (
                <View key={step.id} style={styles.pathRow}>
                  <View style={styles.rail}>
                    <View
                      style={[
                        styles.node,
                        isCurrent && styles.nodeCurrent,
                        isCompleted && styles.nodeCompleted,
                        isBlocked && styles.nodeBlocked,
                        isLocked && styles.nodeLocked,
                      ]}
                    >
                      {isLocked ? <LockGlyph /> : isCompleted ? (
                        <Check color={colors.onForest} size={18} strokeWidth={3} />
                      ) : isCurrent ? (
                        <Play color={colors.onForest} fill={colors.onForest} size={14} strokeWidth={2.4} />
                      ) : (
                        <Text
                          style={[
                            styles.nodeLabel,
                            (isCurrent || isCompleted) && styles.nodeLabelActive,
                          ]}
                        >
                          {nodeLabel}
                        </Text>
                      )}
                    </View>
                    {!isLast ? (
                      <View style={[styles.connector, isCompleted && styles.connectorCompleted]} />
                    ) : null}
                  </View>
                  <View
                    onLayout={isCurrent ? (event) => setCurrentRowOffset(event.nativeEvent.layout.y) : undefined}
                    style={[
                      styles.stepCard,
                      isCurrent && styles.currentCard,
                      isCompleted && styles.completedCard,
                      isBlocked && styles.blockedCard,
                      isLocked && styles.lockedCard,
                    ]}
                  >
                    <View style={styles.missionMeta}>
                      <Text style={styles.missionKind}>{step.kind}</Text>
                      <Text style={[styles.stateLabel, isCurrent && styles.currentState]}>
                        {stateLabels[step.progress_status]}
                      </Text>
                    </View>
                    <Text style={styles.stepTitle}>{step.title}</Text>
                    {isCompleted && (learningRecordFor(step) || step.evidence_url) ? (
                      <View style={styles.savedWork}>
                        <Text style={styles.savedWorkLabel}>Your learning record</Text>
                        {learningRecordFor(step) ? (
                          <Text selectable style={styles.savedWorkText}>
                            {learningRecordFor(step)}
                          </Text>
                        ) : null}
                        {step.evidence_url ? (
                          <Pressable
                            accessibilityRole="link"
                            onPress={() => void Linking.openURL(step.evidence_url)}
                            style={styles.savedWorkLinkTarget}
                          >
                            <Text numberOfLines={1} style={styles.savedWorkLink}>
                              {step.evidence_url}
                            </Text>
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
                                  <View
                                    key={resource.id}
                                    style={[
                                      styles.resourceCardShell,
                                      isPrimaryVideo && styles.primaryVideoCard,
                                    ]}
                                  >
                                    <Pressable
                                      accessibilityHint={
                                        isPrimaryVideo
                                          ? "Opens the primary video course or tutorial"
                                          : "Opens this recommended resource"
                                      }
                                      accessibilityRole="link"
                                      onPress={() => void Linking.openURL(resource.url)}
                                      style={({ pressed }) => [
                                        styles.resourceCardContent,
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
                                    </Pressable>
                                    <View style={styles.resourceFooter}>
                                      <Pressable
                                        accessibilityRole="link"
                                        onPress={() => void Linking.openURL(resource.url)}
                                        style={({ pressed }) => [
                                          styles.resourceFooterLink,
                                          pressed && styles.resourceLinkPressed,
                                        ]}
                                      >
                                        <View style={styles.inlineRow}>
                                          <Text style={styles.resourceOpen}>
                                            {isPrimaryVideo ? "Watch free course" : "Open resource"}
                                          </Text>
                                          <ExternalLink color={colors.forest} size={14} strokeWidth={2.4} />
                                        </View>
                                      </Pressable>
                                      <Pressable
                                        accessibilityHint="Hides this resource. An Undo option will appear briefly."
                                        accessibilityLabel="Not useful for me"
                                        accessibilityRole="button"
                                        disabled={dismissingResourceId !== null}
                                        onPress={() => void markResourceNotUseful(resource.id)}
                                        style={({ pressed }) => [
                                          styles.notUseful,
                                          (pressed || dismissingResourceId === resource.id) &&
                                            styles.resourceLinkPressed,
                                        ]}
                                      >
                                        {dismissingResourceId === resource.id ? (
                                          <Text style={styles.notUsefulText}>…</Text>
                                        ) : (
                                          <ThumbDownGlyph />
                                        )}
                                      </Pressable>
                                    </View>
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
                            {dismissedResource?.stepId === step.id ? (
                              <View
                                accessibilityLiveRegion="polite"
                                accessibilityRole="alert"
                                style={styles.undoNotice}
                              >
                                <Text style={styles.undoNoticeText}>Resource hidden</Text>
                                <Pressable
                                  accessibilityRole="button"
                                  disabled={restoringResource}
                                  onPress={() => void undoResourceDismissal()}
                                  style={({ pressed }) => [
                                    styles.undoButton,
                                    pressed && styles.resourceLinkPressed,
                                  ]}
                                >
                                  <Text style={styles.undoButtonText}>
                                    {restoringResource ? "Restoring…" : "Undo"}
                                  </Text>
                                </Pressable>
                              </View>
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
                            Keep what you learned, made, or want to remember in one place.
                          </Text>
                          <Field
                            accessibilityLabel="Learning record"
                            maxLength={4000}
                            multiline
                            onChangeText={setLearningRecord}
                            placeholder="What did you learn, make, or want to remember? (optional)"
                            style={styles.workField}
                            value={learningRecord}
                          />
                          <Text style={styles.fieldLabel}>Evidence link (optional)</Text>
                          <Field
                            accessibilityHint="A link to your work, such as a document, portfolio, repository, or video"
                            accessibilityLabel="Evidence link"
                            autoCapitalize="none"
                            autoCorrect={false}
                            inputMode="url"
                            keyboardType="url"
                            maxLength={2048}
                            onChangeText={setEvidenceLink}
                            placeholder="https://… link to a doc, portfolio, repo, or video"
                            value={evidenceLink}
                          />
                          {!evidenceLinkValid ? (
                            <Text accessibilityLiveRegion="polite" style={styles.fieldHint}>
                              Use a full link that starts with https://
                            </Text>
                          ) : null}
                          <Text accessibilityLiveRegion="polite" style={styles.savedLabel}>
                            {!evidenceLinkValid
                              ? ""
                              : autosaveState === "saving"
                              ? "Saving…"
                              : autosaveState === "error"
                                ? "Not saved yet. Kept on this device; it will retry when you edit."
                                : !workDirty && (autosaveState === "saved" || step.work_updated_at)
                                  ? "Saved"
                                  : workDirty
                                    ? "Saves automatically"
                                    : ""}
                          </Text>
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
                              <Check color={colors.onForest} size={18} strokeWidth={3} />
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
                          {stepError ? (
                            <Text accessibilityLiveRegion="polite" style={styles.inlineError}>
                              {stepError}
                            </Text>
                          ) : null}
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
