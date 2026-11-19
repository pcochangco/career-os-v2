import { useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useIsWide } from "@/components/app-shell";
import { Check, Play } from "@/components/icons";
import { ProviderSignIn } from "@/components/provider-sign-in";
import { Body, Brand, Button, ErrorState, Field, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { loadGoals } from "@/lib/prefetch";
import { IdentityProvider, useSession } from "@/lib/session";
import { ThemeColors, useTheme } from "@/lib/theme";
import { Goal } from "@/lib/types";

function routeForGoal(goal: Goal): string {
  if (goal.active_roadmap_id) {
    return `/goals/${goal.id}/roadmap?roadmapId=${goal.active_roadmap_id}`;
  }
  if (goal.latest_draft_roadmap_id) {
    return `/goals/${goal.id}/review?roadmapId=${goal.latest_draft_roadmap_id}`;
  }
  return `/goals/${goal.id}/discovery`;
}

// Mirrors the real roadmap screen: done, current ("You are here"), and what comes next.
const exampleSteps: Array<{ title: string; detail: string; state: "done" | "current" | "next" }> = [
  { title: "Map the product skills you already have", detail: "A one-page inventory with two clear gaps.", state: "done" },
  { title: "Ship a small AI feature end to end", detail: "One working prototype you can demo in five minutes.", state: "current" },
  { title: "Write the case study", detail: "Problem, decisions, and results, ready for interviews.", state: "next" },
];

export default function IndexRoute() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const wide = useIsWide();
  const router = useRouter();
  const session = useSession();
  const [title, setTitle] = useState("");
  const [showSignIn, setShowSignIn] = useState(Boolean(session.notice));
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const signInInProgress = useRef(false);

  useEffect(() => {
    if (!session.ready || !session.token || signInInProgress.current) return;
    const token: string = session.token;
    let active = true;
    async function openNext() {
      try {
        setError(null);
        const goals = await loadGoals(token);
        if (!active) return;
        if (goals.length === 0) router.replace("/goals/new" as never);
        else if (goals.length === 1 && goals[0]) router.replace(routeForGoal(goals[0]) as never);
        else router.replace("/goals" as never);
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Your goals could not be loaded.");
        }
      }
    }
    void openNext();
    return () => {
      active = false;
    };
  }, [attempt, router, session.ready, session.token]);

  const handleProviderError = useCallback((message: string) => setError(message), []);
  /** Shared by every sign-in method: sign in, then create the typed goal or open saved ones. */
  const completeSignIn = useCallback(
    async (signIn: () => Promise<string>, failure: string) => {
      if (signInInProgress.current) return;
      signInInProgress.current = true;
      setSigningIn(true);
      setError(null);
      try {
        const token = await signIn();
        const goalTitle = title.trim();
        if (goalTitle) {
          const goal = await apiRequest<Goal>("/goals", {
            body: { title: goalTitle },
            method: "POST",
            token,
          });
          router.replace(`/goals/${goal.id}/discovery` as never);
        } else {
          const goals = await loadGoals(token);
          if (goals.length === 0) router.replace("/goals/new" as never);
          else if (goals.length === 1 && goals[0]) router.replace(routeForGoal(goals[0]) as never);
          else router.replace("/goals" as never);
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : failure);
      } finally {
        signInInProgress.current = false;
        setSigningIn(false);
      }
    },
    [router, title],
  );
  const handleIdentityToken = useCallback(
    (provider: IdentityProvider, identityToken: string) =>
      completeSignIn(() => session.signIn(provider, identityToken), "Sign-in could not be completed."),
    [completeSignIn, session],
  );
  const handleEmailTestSignIn = useCallback(
    (email: string, accessCode: string) =>
      completeSignIn(
        () => session.signInWithEmailTestAccess(email, accessCode),
        "Email sign-in could not be completed.",
      ),
    [completeSignIn, session],
  );
  const handleEmailCodeSignIn = useCallback(
    (email: string, code: string) =>
      completeSignIn(
        () => session.signInWithEmailCode(email, code),
        "Email sign-in could not be completed.",
      ),
    [completeSignIn, session],
  );

  if (!session.ready) return <LoadingState />;
  if (session.error) return <ErrorState message={session.error} onRetry={session.retry} />;
  if (session.token && !error) return <LoadingState label="Opening your roadmap…" />;

  const startCard = (
    <View style={[styles.startCard, wide && styles.startCardWide]}>
      {session.notice ? (
        <View accessibilityLiveRegion="polite" accessibilityRole="alert" style={styles.notice}>
          <Text style={styles.noticeText}>{session.notice}</Text>
        </View>
      ) : null}
      <Text style={styles.cardTitle}>What do you want to achieve?</Text>
      <Text style={styles.cardBody}>
        Try your goal here. It stays only on this screen until you sign in and confirm it.
      </Text>
      <Field
        maxLength={140}
        onChangeText={(value) => {
          setTitle(value);
          setError(null);
          if (!value.trim()) setShowSignIn(false);
        }}
        onSubmitEditing={() => {
          if (title.trim().length >= 3) setShowSignIn(true);
        }}
        placeholder="e.g. Become confident building AI agents"
        returnKeyType="next"
        value={title}
      />
      {!showSignIn ? (
        <>
          <Button
            disabled={title.trim().length < 3}
            onPress={() => setShowSignIn(true)}
          >
            Build my roadmap
          </Button>
          <Pressable
            accessibilityRole="button"
            onPress={() => setShowSignIn(true)}
            style={styles.accountLink}
          >
            <Text style={styles.accountLinkText}>Already have an account? Sign in</Text>
          </Pressable>
        </>
      ) : (
        <View style={styles.signInArea}>
          <View style={styles.saveNotice}>
            <Text style={styles.saveNoticeTitle}>
              {title.trim() ? "Sign in to create this goal" : "Sign in to open your goals"}
            </Text>
            {title.trim() ? (
              <Text style={styles.saveNoticeBody}>“{title.trim()}”</Text>
            ) : null}
            <Text style={styles.saveNoticeMeta}>
              Nothing is copied from another browser session. Only this confirmed goal is created
              after sign-in.
            </Text>
          </View>
          <ProviderSignIn
            disabled={signingIn || session.accountLoading}
            mode="sign-in"
            onError={handleProviderError}
            onEmailCodeSignIn={handleEmailCodeSignIn}
            onEmailTestSignIn={handleEmailTestSignIn}
            onIdentityToken={handleIdentityToken}
            providerConfig={session.providerConfig}
          />
          {signingIn ? (
            <Text accessibilityLiveRegion="polite" style={styles.loadingText}>
              Opening your secure account…
            </Text>
          ) : null}
        </View>
      )}
      {error ? (
        <View style={styles.errorArea}>
          <Text accessibilityLiveRegion="polite" style={styles.errorText}>{error}</Text>
          {session.token ? (
            <Button onPress={() => setAttempt((value) => value + 1)} secondary>
              Open my saved goals
            </Button>
          ) : null}
        </View>
      ) : null}
    </View>
  );

  const hero = (
    <View style={styles.hero}>
      <Text style={styles.eyebrow}>A clear path from ambition to action</Text>
      <Heading>Turn one goal into your next move.</Heading>
      <Body>
        CareerOS asks what matters, builds a focused roadmap, and keeps the next useful action
        obvious.
      </Body>
    </View>
  );

  const example = (
    <View style={styles.example}>
      <Text style={styles.exampleLabel}>Example roadmap</Text>
      <Text style={styles.exampleTitle}>Move into an AI product role</Text>
      <View style={styles.exampleProgressRow}>
        <Text style={styles.exampleProgressText}>1 of 3 steps</Text>
        <Text style={styles.exampleProgressPercent}>33%</Text>
      </View>
      <View style={styles.exampleTrack}>
        <View style={styles.exampleFill} />
      </View>
      <View style={styles.steps}>
        {exampleSteps.map((step, index) => (
          <View key={step.title} style={[styles.step, step.state === "current" && styles.stepCurrent]}>
            <View
              style={[
                styles.stepNode,
                step.state !== "next" && styles.stepNodeActive,
              ]}
            >
              {step.state === "done" ? (
                <Check color={colors.onForest} size={15} strokeWidth={3} />
              ) : step.state === "current" ? (
                <Play color={colors.onForest} fill={colors.onForest} size={12} strokeWidth={2.4} />
              ) : (
                <Text style={styles.stepNumberText}>{index + 1}</Text>
              )}
            </View>
            <View style={styles.stepCopy}>
              {step.state === "current" ? <Text style={styles.stepHere}>You are here</Text> : null}
              <Text style={[styles.stepTitle, step.state === "done" && styles.stepTitleDone]}>{step.title}</Text>
              <Text style={styles.stepBody}>{step.detail}</Text>
            </View>
          </View>
        ))}
      </View>
      <Text style={styles.exampleBody}>One step at a time, each ending in something you can show.</Text>
    </View>
  );

  return (
    <Screen width="wide">
      <Brand />
      {wide ? (
        <View style={styles.columns}>
          <View style={styles.columnMain}>
            {hero}
            {example}
          </View>
          <View style={styles.columnSide}>{startCard}</View>
        </View>
      ) : (
        <>
          {hero}
          {startCard}
          {example}
        </>
      )}
      <View style={styles.footerLinks}>
        {[
          ["Privacy", "/privacy"],
          ["Terms", "/terms"],
          ["Support", "/support"],
        ].map(([label, route]) => (
          <Pressable accessibilityRole="link" key={route} onPress={() => router.push(route as never)}>
            <Text style={styles.footerLink}>{label}</Text>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  accountLink: { alignItems: "center", justifyContent: "center", minHeight: 48, paddingTop: 8 },
  accountLinkText: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  cardBody: { color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 18 },
  cardTitle: { color: colors.ink, fontSize: 20, fontWeight: "700", marginBottom: 6 },
  errorArea: { gap: 10 },
  errorText: { color: colors.danger, fontSize: 14, lineHeight: 21 },
  columns: { alignItems: "flex-start", flexDirection: "row", gap: 48, marginTop: 24 },
  columnMain: { flex: 1, minWidth: 0 },
  columnSide: { width: 420 },
  example: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, marginBottom: 28, padding: 20 },
  exampleBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginTop: 18 },
  exampleLabel: { color: colors.forest, fontSize: 12, fontWeight: "900", letterSpacing: 0.7, marginBottom: 6, textTransform: "uppercase" },
  exampleTitle: { color: colors.ink, fontSize: 18, fontWeight: "700", marginBottom: 4 },
  eyebrow: { color: colors.forest, fontSize: 13, fontWeight: "700", marginBottom: 10 },
  footerLink: { color: colors.muted, fontSize: 13, fontWeight: "700" },
  footerLinks: { flexDirection: "row", gap: 22, justifyContent: "center", paddingBottom: 10 },
  hero: { marginBottom: 8 },
  notice: { backgroundColor: colors.cardMuted, borderColor: colors.line, borderRadius: 10, borderWidth: 1, marginBottom: 12, padding: 12 },
  noticeText: { color: colors.ink, fontSize: 14, fontWeight: "600", lineHeight: 20 },
  loadingText: { color: colors.muted, fontSize: 13, textAlign: "center" },
  saveNotice: { backgroundColor: colors.cardMuted, borderRadius: 14, gap: 5, padding: 14 },
  saveNoticeBody: { color: colors.ink, fontSize: 15, fontWeight: "700", lineHeight: 22 },
  saveNoticeMeta: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  saveNoticeTitle: { color: colors.ink, fontSize: 15, fontWeight: "800" },
  signInArea: { gap: 14 },
  startCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, gap: 6, marginBottom: 24, padding: 20 },
  startCardWide: { padding: 24, shadowColor: "#101828", shadowOffset: { height: 8, width: 0 }, shadowOpacity: 0.06, shadowRadius: 24 },
  step: { alignItems: "flex-start", flexDirection: "row", gap: 12 },
  stepBody: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  stepCopy: { flex: 1 },
  stepCurrent: { backgroundColor: colors.forestSoft, borderRadius: 10, marginHorizontal: -10, padding: 10 },
  stepHere: { color: colors.forestDark, fontSize: 12, fontWeight: "800", marginBottom: 2, textTransform: "uppercase" },
  stepNode: { alignItems: "center", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 14, borderWidth: 2, height: 28, justifyContent: "center", width: 28 },
  stepNodeActive: { backgroundColor: colors.forest, borderColor: colors.forest },
  stepNumberText: { color: colors.muted, fontSize: 13, fontWeight: "800" },
  stepTitleDone: { color: colors.muted },
  exampleProgressRow: { flexDirection: "row", justifyContent: "space-between", marginTop: 10 },
  exampleProgressText: { color: colors.muted, fontSize: 13, fontWeight: "600" },
  exampleProgressPercent: { color: colors.forest, fontSize: 13, fontWeight: "800" },
  exampleTrack: { backgroundColor: colors.line, borderRadius: 4, height: 6, marginBottom: 18, marginTop: 6, overflow: "hidden" },
  exampleFill: { backgroundColor: colors.forest, borderRadius: 4, height: 6, width: "33%" },
  stepTitle: { color: colors.ink, fontSize: 15, fontWeight: "800", marginBottom: 2 },
  steps: { gap: 16 },
});
