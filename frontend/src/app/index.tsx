import { useRouter } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ProviderSignIn } from "@/components/provider-sign-in";
import { Body, Brand, Button, ErrorState, Field, Heading, LoadingState, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
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

const exampleSteps = [
  ["1", "Define the outcome", "Turn an ambition into a measurable destination."],
  ["2", "Build the right sequence", "Focus on the few milestones that unlock progress."],
  ["3", "Take the next move", "Start with one concrete, finishable action."],
];

export default function IndexRoute() {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const router = useRouter();
  const session = useSession();
  const [title, setTitle] = useState("");
  const [showSignIn, setShowSignIn] = useState(false);
  const [signingIn, setSigningIn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const signInInProgress = useRef(false);

  useEffect(() => {
    if (!session.ready || !session.token || signInInProgress.current) return;
    let active = true;
    async function openNext() {
      try {
        setError(null);
        const goals = await apiRequest<Goal[]>("/goals", { token: session.token });
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
  const handleIdentityToken = useCallback(
    async (provider: IdentityProvider, identityToken: string) => {
      if (signInInProgress.current) return;
      signInInProgress.current = true;
      setSigningIn(true);
      setError(null);
      try {
        const token = await session.signIn(provider, identityToken);
        const goalTitle = title.trim();
        if (goalTitle) {
          const goal = await apiRequest<Goal>("/goals", {
            body: { title: goalTitle },
            method: "POST",
            token,
          });
          router.replace(`/goals/${goal.id}/discovery` as never);
        } else {
          const goals = await apiRequest<Goal[]>("/goals", { token });
          if (goals.length === 0) router.replace("/goals/new" as never);
          else if (goals.length === 1 && goals[0]) router.replace(routeForGoal(goals[0]) as never);
          else router.replace("/goals" as never);
        }
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Sign-in could not be completed.");
      } finally {
        signInInProgress.current = false;
        setSigningIn(false);
      }
    },
    [router, session, title],
  );

  if (!session.ready) return <LoadingState />;
  if (session.error) return <ErrorState message={session.error} onRetry={session.retry} />;
  if (session.token && !error) return <LoadingState label="Opening your saved path…" />;

  return (
    <Screen>
      <Brand />
      <View style={styles.hero}>
        <Text style={styles.eyebrow}>A clear path from ambition to action</Text>
        <Heading>Turn one goal into your next move.</Heading>
        <Body>
          CareerOS asks what matters, builds a focused roadmap, and keeps the next useful action
          obvious.
        </Body>
      </View>

      <View style={styles.startCard}>
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

      <View style={styles.example}>
        <Text style={styles.exampleLabel}>Example path</Text>
        <Text style={styles.exampleTitle}>Move into an AI product role</Text>
        <Text style={styles.exampleBody}>A roadmap stays small enough to act on.</Text>
        <View style={styles.steps}>
          {exampleSteps.map(([number, stepTitle, description]) => (
            <View key={number} style={styles.step}>
              <View style={styles.stepNumber}>
                <Text style={styles.stepNumberText}>{number}</Text>
              </View>
              <View style={styles.stepCopy}>
                <Text style={styles.stepTitle}>{stepTitle}</Text>
                <Text style={styles.stepBody}>{description}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

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
  cardTitle: { color: colors.ink, fontSize: 22, fontWeight: "800", marginBottom: 7 },
  errorArea: { gap: 10 },
  errorText: { color: colors.danger, fontSize: 14, lineHeight: 21 },
  example: { backgroundColor: colors.forestSoft, borderColor: colors.softBorder, borderRadius: 22, borderWidth: 1, marginBottom: 28, padding: 20 },
  exampleBody: { color: colors.muted, fontSize: 14, lineHeight: 21, marginBottom: 18 },
  exampleLabel: { color: colors.forest, fontSize: 12, fontWeight: "900", letterSpacing: 0.7, marginBottom: 6, textTransform: "uppercase" },
  exampleTitle: { color: colors.ink, fontSize: 21, fontWeight: "800", marginBottom: 5 },
  eyebrow: { color: colors.forest, fontSize: 13, fontWeight: "900", letterSpacing: 0.6, marginBottom: 10, textTransform: "uppercase" },
  footerLink: { color: colors.muted, fontSize: 13, fontWeight: "700" },
  footerLinks: { flexDirection: "row", gap: 22, justifyContent: "center", paddingBottom: 10 },
  hero: { marginBottom: 8 },
  loadingText: { color: colors.muted, fontSize: 13, textAlign: "center" },
  saveNotice: { backgroundColor: colors.cardMuted, borderRadius: 14, gap: 5, padding: 14 },
  saveNoticeBody: { color: colors.ink, fontSize: 15, fontWeight: "700", lineHeight: 22 },
  saveNoticeMeta: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  saveNoticeTitle: { color: colors.ink, fontSize: 15, fontWeight: "800" },
  signInArea: { gap: 14 },
  startCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 22, borderWidth: 1, gap: 6, marginBottom: 24, padding: 20 },
  step: { alignItems: "flex-start", flexDirection: "row", gap: 12 },
  stepBody: { color: colors.muted, fontSize: 13, lineHeight: 19 },
  stepCopy: { flex: 1 },
  stepNumber: { alignItems: "center", backgroundColor: colors.forest, borderRadius: 14, height: 28, justifyContent: "center", width: 28 },
  stepNumberText: { color: colors.onForest, fontSize: 13, fontWeight: "900" },
  stepTitle: { color: colors.ink, fontSize: 15, fontWeight: "800", marginBottom: 2 },
  steps: { gap: 16 },
});
