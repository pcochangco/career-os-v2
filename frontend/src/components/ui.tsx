import { ReactNode, RefObject } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useTheme } from "@/lib/theme";

export const colors = {
  background: "#F6F8F4",
  card: "#FFFFFF",
  forest: "#1E6044",
  forestDark: "#184634",
  forestSoft: "#DCEDE3",
  ink: "#17211B",
  line: "#DDE4DE",
  muted: "#607067",
  white: "#FFFFFF",
};

export function Screen({
  children,
  scrollViewRef,
}: {
  children: ReactNode;
  scrollViewRef?: RefObject<ScrollView | null>;
}) {
  const { colors } = useTheme();
  return (
    <SafeAreaView style={[styles.safeArea, { backgroundColor: colors.background }]}> 
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        ref={scrollViewRef}
      >
        <View style={styles.content}>{children}</View>
      </ScrollView>
    </SafeAreaView>
  );
}

export function Brand({ compact = false }: { compact?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.brand, compact && styles.brandCompact]}>
      <Image
        accessibilityIgnoresInvertColors
        source={require("../../assets/logo-mark.png")}
        style={styles.brandMark}
      />
      <Text style={[styles.brandText, { color: colors.forest }]}>CareerOS</Text>
    </View>
  );
}

export function AppHeader({ children }: { children?: ReactNode }) {
  return (
    <View style={styles.appHeader}>
      <Brand compact />
      {children ? <View style={styles.headerActions}>{children}</View> : null}
    </View>
  );
}

export function SettingsGlyph() {
  const { colors } = useTheme();
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={styles.settingsGlyph}
    >
      {([3, 10, 6] as const).map((left, index) => (
        <View key={index} style={styles.settingsGlyphRow}>
          <View style={[styles.settingsGlyphLine, { backgroundColor: colors.forest }]} />
          <View
            style={[
              styles.settingsGlyphKnob,
              { backgroundColor: colors.card, borderColor: colors.forest, left },
            ]}
          />
        </View>
      ))}
    </View>
  );
}

export function ThumbDownGlyph() {
  const { colors } = useTheme();
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={styles.thumbGlyph}
    >
      <View style={[styles.thumbCuff, { borderColor: colors.muted }]} />
      <View style={[styles.thumbPalm, { borderColor: colors.muted }]} />
      <View style={[styles.thumbStem, { borderColor: colors.muted }]} />
    </View>
  );
}

export function Heading({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  return <Text style={[styles.heading, { color: colors.ink }]}>{children}</Text>;
}

export function Body({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  return <Text style={[styles.body, { color: colors.muted }]}>{children}</Text>;
}

type ButtonProps = {
  children: ReactNode;
  disabled?: boolean;
  loading?: boolean;
  onPress: () => void;
  secondary?: boolean;
};

export function Button({ children, disabled, loading, onPress, secondary }: ButtonProps) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary ? { backgroundColor: colors.forestSoft } : { backgroundColor: colors.forest },
        (disabled || loading) && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? colors.forest : colors.onForest} />
      ) : (
        <Text style={[styles.buttonLabel, { color: secondary ? colors.forestDark : colors.onForest }]}>{children}</Text>
      )}
    </Pressable>
  );
}

export function Field(props: TextInputProps) {
  const { colors } = useTheme();
  return (
    <TextInput
      placeholderTextColor={colors.fieldPlaceholder}
      {...props}
      style={[styles.field, { backgroundColor: colors.card, borderColor: colors.line, color: colors.ink }, props.multiline && styles.fieldMultiline, props.style]}
    />
  );
}

export function LoadingState({ label = "Opening your path…" }: { label?: string }) {
  const { colors } = useTheme();
  return (
    <Screen>
      <View style={styles.centered}>
        <Image
          accessibilityLabel="CareerOS"
          accessibilityIgnoresInvertColors
          source={require("../../assets/logo-mark.png")}
          style={styles.loadingMark}
        />
        <Text style={[styles.loadingBrand, { color: colors.forest }]}>CareerOS</Text>
        <ActivityIndicator color={colors.forest} size="large" />
        <Text style={[styles.loadingLabel, { color: colors.muted }]}>{label}</Text>
      </View>
    </Screen>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Screen>
      <View style={styles.centered}>
        <Heading>We couldn’t open CareerOS.</Heading>
        <Body>{message}</Body>
        <Button onPress={onRetry}>Try again</Button>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  safeArea: { backgroundColor: colors.background, flex: 1 },
  scrollContent: { flexGrow: 1, paddingHorizontal: 20, paddingVertical: 28 },
  content: { alignSelf: "center", flex: 1, maxWidth: 680, width: "100%" },
  appHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 24, minHeight: 44 },
  brand: { alignItems: "center", flexDirection: "row", gap: 8, marginBottom: 22 },
  brandCompact: { marginBottom: 0 },
  brandMark: { height: 30, width: 30 },
  brandText: { fontSize: 15, fontWeight: "900", letterSpacing: 0.6 },
  headerActions: { alignItems: "center", flexDirection: "row", gap: 8 },
  heading: {
    color: colors.ink,
    fontSize: 34,
    fontWeight: "800",
    letterSpacing: -0.8,
    lineHeight: 40,
    marginBottom: 14,
  },
  body: { color: colors.muted, fontSize: 17, lineHeight: 26, marginBottom: 22 },
  button: {
    alignItems: "center",
    borderRadius: 16,
    justifyContent: "center",
    minHeight: 52,
    paddingHorizontal: 22,
    paddingVertical: 14,
  },
  buttonPrimary: { backgroundColor: colors.forest },
  buttonSecondary: { backgroundColor: colors.forestSoft },
  buttonDisabled: { opacity: 0.48 },
  buttonPressed: { opacity: 0.82 },
  buttonLabel: { color: colors.white, fontSize: 16, fontWeight: "800" },
  buttonLabelSecondary: { color: colors.forestDark },
  field: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderRadius: 16,
    borderWidth: 1,
    color: colors.ink,
    fontSize: 18,
    lineHeight: 26,
    marginBottom: 20,
    minHeight: 56,
    paddingHorizontal: 17,
    paddingVertical: 14,
  },
  fieldMultiline: { minHeight: 140, textAlignVertical: "top" },
  centered: { alignItems: "center", flex: 1, gap: 14, justifyContent: "center", minHeight: 420 },
  loadingBrand: { fontSize: 18, fontWeight: "900", letterSpacing: 0.4, marginBottom: 4 },
  loadingLabel: { color: colors.muted, fontSize: 16, textAlign: "center" },
  loadingMark: { alignSelf: "center", height: 92, width: 92 },
  settingsGlyph: { height: 18, justifyContent: "space-between", paddingVertical: 1, width: 18 },
  settingsGlyphRow: { height: 5, justifyContent: "center", position: "relative", width: 18 },
  settingsGlyphLine: { borderRadius: 1, height: 2, width: 18 },
  settingsGlyphKnob: { borderRadius: 3, borderWidth: 1.5, height: 6, position: "absolute", top: -0.5, width: 6 },
  thumbGlyph: { height: 18, position: "relative", width: 19 },
  thumbCuff: { borderRadius: 2, borderWidth: 1.5, height: 8, left: 1, position: "absolute", top: 3, width: 4 },
  thumbPalm: { borderRadius: 3, borderWidth: 1.5, height: 10, left: 4, position: "absolute", top: 2, width: 13 },
  thumbStem: { borderBottomLeftRadius: 4, borderBottomWidth: 1.5, borderLeftWidth: 1.5, height: 7, left: 11, position: "absolute", top: 9, width: 5 },
});
