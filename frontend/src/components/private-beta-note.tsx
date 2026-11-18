import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { SUPPORT_EMAIL } from "@/components/legal-document";
import { radius, ThemeColors, useTheme } from "@/lib/theme";

/**
 * Shown on the sign-in screen while public sign-up is closed (no Google, Apple or real
 * email sign-in yet). Honest about the beta, with a way to reach the team when a
 * support address is configured.
 */
export function PrivateBetaNote({ compact = false }: { compact?: boolean }) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  return (
    <View style={[styles.note, compact && styles.compact]}>
      {!compact ? <Text style={styles.title}>CareerOS is in private beta</Text> : null}
      <Text style={styles.body}>
        {compact
          ? "Don’t have an access code? CareerOS is in private beta, and new sign-ups open soon."
          : "New sign-ups open soon. If you’ve been invited, use the sign-in details the CareerOS team sent you."}
      </Text>
      {SUPPORT_EMAIL ? (
        <Pressable
          accessibilityRole="link"
          hitSlop={8}
          onPress={() =>
            void Linking.openURL(`mailto:${SUPPORT_EMAIL}?subject=CareerOS%20beta%20access`)
          }
          style={styles.link}
        >
          <Text style={styles.linkText}>Ask for beta access</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    note: {
      backgroundColor: colors.cardMuted,
      borderRadius: radius.md,
      gap: 6,
      padding: 14,
    },
    compact: { backgroundColor: "transparent", paddingHorizontal: 0, paddingVertical: 4 },
    title: { color: colors.ink, fontSize: 15, fontWeight: "700" },
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
    link: { alignSelf: "flex-start", minHeight: 44, justifyContent: "center" },
    linkText: { color: colors.forest, fontSize: 14, fontWeight: "700" },
  });
