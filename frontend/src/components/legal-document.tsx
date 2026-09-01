import { useRouter } from "expo-router";
import { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Brand, Button, Screen } from "@/components/ui";
import { ThemeColors, useTheme } from "@/lib/theme";

export const SUPPORT_EMAIL = (process.env.EXPO_PUBLIC_SUPPORT_EMAIL ?? "").trim();

export function LegalSection({ children, title }: { children: ReactNode; title: string }) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  return (
    <View style={styles.section}>
      <Text accessibilityRole="header" style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.body}>{children}</Text>
    </View>
  );
}

export function LegalDocument({ children, effectiveDate = "September 1, 2026", title }: { children: ReactNode; effectiveDate?: string; title: string }) {
  const router = useRouter();
  const { colors } = useTheme();
  const styles = createStyles(colors);
  return (
    <Screen>
      <Brand />
      <Text accessibilityRole="header" style={styles.title}>{title}</Text>
      <Text style={styles.effective}>Effective {effectiveDate}</Text>
      {children}
      <View style={styles.links}>
        <Pressable accessibilityRole="link" onPress={() => router.push("/privacy" as never)} style={styles.link}>
          <Text style={styles.linkText}>Privacy</Text>
        </Pressable>
        <Pressable accessibilityRole="link" onPress={() => router.push("/terms" as never)} style={styles.link}>
          <Text style={styles.linkText}>Terms</Text>
        </Pressable>
        <Pressable accessibilityRole="link" onPress={() => router.push("/account-deletion" as never)} style={styles.link}>
          <Text style={styles.linkText}>Delete data</Text>
        </Pressable>
        <Pressable accessibilityRole="link" onPress={() => router.push("/support" as never)} style={styles.link}>
          <Text style={styles.linkText}>Support</Text>
        </Pressable>
      </View>
      <Button onPress={() => router.replace("/" as never)}>Open CareerOS</Button>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  body: { color: colors.muted, fontSize: 16, lineHeight: 25 },
  effective: { color: colors.muted, fontSize: 14, marginBottom: 28 },
  link: { justifyContent: "center", minHeight: 44, paddingHorizontal: 6 },
  links: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginBottom: 20, marginTop: 12 },
  linkText: { color: colors.forest, fontSize: 14, fontWeight: "800" },
  section: { borderBottomColor: colors.line, borderBottomWidth: 1, gap: 8, paddingBottom: 22, paddingTop: 2 },
  sectionTitle: { color: colors.ink, fontSize: 20, fontWeight: "800", marginTop: 22 },
  title: { color: colors.ink, fontSize: 34, fontWeight: "800", letterSpacing: -0.8, lineHeight: 40, marginBottom: 8 },
});
