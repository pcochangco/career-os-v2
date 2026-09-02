import Constants from "expo-constants";
import { useRouter } from "expo-router";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { AppHeader, Body, Button, Field, Heading, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSession } from "@/lib/session";
import { ThemeColors, useTheme } from "@/lib/theme";

type IssueCategory = "technical" | "roadmap" | "account" | "other";

type IssueReportResponse = {
  id: string;
  reference: string;
  category: IssueCategory;
  created_at: string;
};

const categories: Array<{ label: string; value: IssueCategory }> = [
  { label: "Technical", value: "technical" },
  { label: "Roadmap", value: "roadmap" },
  { label: "Account", value: "account" },
  { label: "Other", value: "other" },
];

export default function ReportIssueRoute() {
  const router = useRouter();
  const { token } = useSession();
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [category, setCategory] = useState<IssueCategory>("technical");
  const [message, setMessage] = useState("");
  const [requestReference, setRequestReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<IssueReportResponse | null>(null);

  async function submit() {
    if (!token || message.trim().length < 10) {
      setError("Describe what happened in at least 10 characters.");
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      const response = await apiRequest<IssueReportResponse>("/issue-reports", {
        method: "POST",
        token,
        body: {
          category,
          message,
          request_reference: requestReference,
          platform: Platform.OS === "web" || Platform.OS === "ios" || Platform.OS === "android"
            ? Platform.OS
            : "unknown",
          app_version: Constants.expoConfig?.version ?? "unknown",
        },
      });
      setSubmitted(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Your report could not be sent.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Screen>
      <AppHeader>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.replace("/settings" as never)}
          style={styles.done}
        >
          <Text style={styles.doneText}>Done</Text>
        </Pressable>
      </AppHeader>
      {submitted ? (
        <View style={styles.confirmation}>
          <Heading>Report received</Heading>
          <Body>Thank you. Keep this reference in case you need to follow up.</Body>
          <Text selectable style={styles.reference}>{submitted.reference}</Text>
          <Button onPress={() => router.replace("/goals" as never)}>Back to goals</Button>
        </View>
      ) : (
        <>
          <Heading>Report an issue</Heading>
          <Body>
            Tell us what happened and what you expected. Do not include passwords, sign-in tokens,
            or sensitive personal details.
          </Body>
          <Text style={styles.label}>Type of issue</Text>
          <View accessibilityRole="radiogroup" style={styles.categories}>
            {categories.map((option) => {
              const selected = option.value === category;
              return (
                <Pressable
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                  key={option.value}
                  onPress={() => setCategory(option.value)}
                  style={({ pressed }) => [
                    styles.category,
                    selected && styles.categorySelected,
                    pressed && styles.pressed,
                  ]}
                >
                  <Text style={[styles.categoryText, selected && styles.categoryTextSelected]}>
                    {option.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          <Text style={styles.label}>What happened?</Text>
          <Field
            accessibilityLabel="Issue details"
            maxLength={2000}
            multiline
            onChangeText={setMessage}
            placeholder="Example: I tapped Generate roadmap, then…"
            value={message}
          />
          <Text style={styles.label}>Error reference (optional)</Text>
          <Field
            accessibilityLabel="Error reference"
            autoCapitalize="none"
            maxLength={100}
            onChangeText={setRequestReference}
            placeholder="Paste the reference shown with the error"
            value={requestReference}
          />
          {error ? <Text accessibilityLiveRegion="polite" style={styles.error}>{error}</Text> : null}
          <Button disabled={submitting} loading={submitting} onPress={() => void submit()}>
            Send report
          </Button>
        </>
      )}
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  categories: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 24 },
  category: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, minHeight: 40, paddingHorizontal: 15, paddingVertical: 9 },
  categorySelected: { backgroundColor: colors.forestSoft, borderColor: colors.forest },
  categoryText: { color: colors.muted, fontSize: 14, fontWeight: "700" },
  categoryTextSelected: { color: colors.forestDark },
  confirmation: { flex: 1, justifyContent: "center", minHeight: 420 },
  done: { justifyContent: "center", minHeight: 44, paddingHorizontal: 4 },
  doneText: { color: colors.forest, fontSize: 15, fontWeight: "800" },
  error: { color: colors.danger, fontSize: 14, lineHeight: 21, marginBottom: 16 },
  label: { color: colors.ink, fontSize: 15, fontWeight: "800", marginBottom: 8 },
  pressed: { opacity: 0.8 },
  reference: { color: colors.forest, fontSize: 20, fontWeight: "900", letterSpacing: 0.8, marginBottom: 28 },
});
