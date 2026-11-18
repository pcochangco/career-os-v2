import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { SUPPORT_EMAIL } from "@/components/legal-document";
import { radius, ThemeColors, useTheme } from "@/lib/theme";

/**
 * Premium can't be bought yet (no public billing), so every plan limit offers a plain way to
 * ask, never a fake upgrade button. Without a configured support address it renders nothing.
 */
export function AskAboutPremium({ topic }: { topic: "goals" | "roadmap" }) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  // Callers already say Premium can't be bought yet; without an address there's nothing to add.
  if (!SUPPORT_EMAIL) return null;
  const subject = topic === "goals" ? "More goals on CareerOS" : "Unlocking my full roadmap";
  return (
    <Pressable
      accessibilityHint="Opens an email to the CareerOS team"
      accessibilityRole="link"
      hitSlop={8}
      onPress={() =>
        void Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(subject)}`)
      }
      style={({ pressed }) => [styles.link, pressed && styles.pressed]}
    >
      <Text style={styles.linkText}>Ask about Premium</Text>
    </Pressable>
  );
}

/** Shown when a Free account has used every goal its plan includes. */
export function GoalLimitCard({ limit }: { limit: number }) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  return (
    <View accessibilityRole="summary" style={styles.card}>
      <Text style={styles.title}>You’ve used all {limit} free goals</Text>
      <Text style={styles.body}>
        The Free plan includes {limit} goals in total. Everything you’ve created stays yours:
        keep working on your roadmaps any time. Premium isn’t available to buy yet.
      </Text>
      <AskAboutPremium topic="goals" />
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    card: {
      backgroundColor: colors.card,
      borderColor: colors.line,
      borderRadius: radius.lg,
      borderWidth: 1,
      gap: 8,
      padding: 18,
    },
    title: { color: colors.ink, fontSize: 17, fontWeight: "700" },
    body: { color: colors.muted, fontSize: 15, lineHeight: 22 },
    link: { alignSelf: "flex-start", justifyContent: "center", minHeight: 44 },
    linkText: { color: colors.forest, fontSize: 15, fontWeight: "700" },
    pressed: { opacity: 0.7 },
  });
