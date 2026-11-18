import { ReactNode, RefObject, useEffect, useState } from "react";
import { LockKeyhole, SlidersHorizontal, ThumbsDown } from "@/components/icons";
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
import { Edge, SafeAreaView } from "react-native-safe-area-context";

import { useIsWide, useShell } from "@/components/app-shell";
import { radius, useTheme } from "@/lib/theme";

/** Content column widths: forms and focused flows, regular pages, and grid pages. */
const contentWidths = { narrow: 640, default: 760, wide: 1080 } as const;
export type ScreenWidth = keyof typeof contentWidths;

export function Screen({
  children,
  footer,
  scrollViewRef,
  width = "default",
}: {
  children: ReactNode;
  /** Pinned below the scrolling content, for the screen's one primary action. */
  footer?: ReactNode;
  scrollViewRef?: RefObject<ScrollView | null>;
  width?: ScreenWidth;
}) {
  const { colors } = useTheme();
  const { inShell } = useShell();
  const wide = useIsWide();
  // Inside the shell the sidebar or bottom tabs own the remaining edges.
  const edges: Edge[] = inShell ? (wide ? [] : ["top"]) : ["top", "bottom", "left", "right"];
  return (
    <SafeAreaView edges={edges} style={[styles.safeArea, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={[styles.scrollContent, wide ? styles.scrollContentWide : null]}
        keyboardShouldPersistTaps="handled"
        ref={scrollViewRef}
      >
        <View style={[styles.content, { maxWidth: contentWidths[width] }]}>{children}</View>
      </ScrollView>
      {footer ? (
        <View style={[styles.footer, { backgroundColor: colors.card, borderTopColor: colors.line }]}>
          <View style={[styles.footerInner, { maxWidth: contentWidths[width] }]}>{footer}</View>
        </View>
      ) : null}
    </SafeAreaView>
  );
}

export function Brand({ compact = false }: { compact?: boolean }) {
  const { colors } = useTheme();
  const { inShell, wide } = useShell();
  // On desktop the sidebar already shows the brand.
  if (inShell && wide) return null;
  return (
    <View style={[styles.brand, inShell && styles.brandInShell, compact && styles.brandCompact]}>
      <Image
        accessibilityIgnoresInvertColors
        source={require("../../assets/logo-mark.png")}
        style={styles.brandMark}
      />
      <Text style={[styles.brandText, { color: colors.ink }]}>CareerOS</Text>
    </View>
  );
}

export function AppHeader({ children }: { children?: ReactNode }) {
  const { inShell, wide } = useShell();
  if (inShell && wide && !children) return null;
  return (
    <View style={[styles.appHeader, inShell && wide && styles.appHeaderEnd]}>
      <Brand compact />
      {children ? <View style={styles.headerActions}>{children}</View> : null}
    </View>
  );
}

function Glyph({ children }: { children: ReactNode }) {
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={styles.iconFrame}
    >
      {children}
    </View>
  );
}

export function SettingsGlyph() {
  const { colors } = useTheme();
  return (
    <Glyph>
      <SlidersHorizontal color={colors.muted} size={18} strokeWidth={1.9} />
    </Glyph>
  );
}

export function ThumbDownGlyph() {
  const { colors } = useTheme();
  return (
    <Glyph>
      <ThumbsDown color={colors.muted} size={18} strokeWidth={1.8} />
    </Glyph>
  );
}

export function LockGlyph() {
  const { colors } = useTheme();
  return (
    <Glyph>
      <LockKeyhole color={colors.muted} size={16} strokeWidth={1.9} />
    </Glyph>
  );
}

export function Heading({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  const wide = useIsWide();
  return (
    <Text
      accessibilityRole="header"
      style={[styles.heading, wide && styles.headingWide, { color: colors.ink }]}
    >
      {children}
    </Text>
  );
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
  /** For irreversible actions such as deleting an account. */
  danger?: boolean;
};

export function Button({ children, danger, disabled, loading, onPress, secondary }: ButtonProps) {
  const { colors } = useTheme();
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ busy: loading, disabled: inactive }}
      disabled={inactive}
      onPress={onPress}
      style={({ hovered, pressed }: { hovered?: boolean; pressed: boolean }) => [
        styles.button,
        danger
          ? { backgroundColor: colors.danger, opacity: hovered ? 0.9 : 1 }
          : secondary
            ? { backgroundColor: hovered ? colors.hover : colors.card, borderColor: colors.line, borderWidth: 1 }
            : { backgroundColor: hovered ? colors.forestDark : colors.forest },
        inactive && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? colors.forest : colors.onForest} />
      ) : (
        <Text
          style={[
            styles.buttonLabel,
            { color: danger ? colors.card : secondary ? colors.ink : colors.onForest },
          ]}
        >
          {children}
        </Text>
      )}
    </Pressable>
  );
}

export function Field(props: TextInputProps) {
  const { colors } = useTheme();
  const [focused, setFocused] = useState(false);
  return (
    <TextInput
      placeholderTextColor={colors.fieldPlaceholder}
      {...props}
      onBlur={(event) => {
        setFocused(false);
        props.onBlur?.(event);
      }}
      onFocus={(event) => {
        setFocused(true);
        props.onFocus?.(event);
      }}
      style={[
        styles.field,
        { backgroundColor: colors.card, borderColor: focused ? colors.forest : colors.line, color: colors.ink },
        focused && styles.fieldFocused,
        props.multiline && styles.fieldMultiline,
        props.style,
      ]}
    />
  );
}

export function LoadingState({ label = "Opening CareerOS…" }: { label?: string }) {
  const { colors } = useTheme();
  // The free hosting plan sleeps when idle; the first request can take up to a minute.
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 5000);
    return () => clearTimeout(timer);
  }, []);
  return (
    <Screen>
      <View style={styles.centered}>
        <Image
          accessibilityLabel="CareerOS"
          accessibilityIgnoresInvertColors
          source={require("../../assets/logo-mark.png")}
          style={styles.loadingMark}
        />
        <ActivityIndicator color={colors.forest} />
        <Text style={[styles.loadingLabel, { color: colors.muted }]}>{label}</Text>
        {slow ? (
          <Text accessibilityLiveRegion="polite" style={[styles.loadingHint, { color: colors.subtle }]}>
            Still working. If CareerOS hasn’t been used for a while, waking it up can take up
            to a minute.
          </Text>
        ) : null}
      </View>
    </Screen>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Screen width="narrow">
      <View style={styles.centered}>
        <Heading>We couldn’t open CareerOS.</Heading>
        <Body>{message}</Body>
        <Button onPress={onRetry}>Try again</Button>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingHorizontal: 16, paddingVertical: 20 },
  scrollContentWide: { paddingHorizontal: 40, paddingVertical: 36 },
  content: { alignSelf: "center", flex: 1, width: "100%" },
  footer: { borderTopWidth: 1, paddingHorizontal: 16, paddingVertical: 12 },
  footerInner: { alignSelf: "center", width: "100%" },
  appHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 20, minHeight: 40 },
  appHeaderEnd: { justifyContent: "flex-end" },
  brand: { alignItems: "center", flexDirection: "row", gap: 8, marginBottom: 28 },
  brandInShell: { marginBottom: 16 },
  brandCompact: { marginBottom: 0 },
  brandMark: { height: 28, width: 28 },
  brandText: { fontSize: 16, fontWeight: "800", letterSpacing: 0.2 },
  headerActions: { alignItems: "center", flexDirection: "row", gap: 8 },
  heading: { fontSize: 26, fontWeight: "700", letterSpacing: -0.5, lineHeight: 32, marginBottom: 8 },
  headingWide: { fontSize: 30, letterSpacing: -0.6, lineHeight: 36 },
  body: { fontSize: 16, lineHeight: 24, marginBottom: 20 },
  button: {
    alignItems: "center",
    borderRadius: radius.md,
    justifyContent: "center",
    minHeight: 46,
    paddingHorizontal: 18,
    paddingVertical: 12,
  },
  buttonDisabled: { opacity: 0.45 },
  buttonPressed: { opacity: 0.85 },
  buttonLabel: { fontSize: 15, fontWeight: "700" },
  field: {
    borderRadius: radius.md,
    borderWidth: 1,
    fontSize: 16,
    lineHeight: 22,
    marginBottom: 16,
    minHeight: 48,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  fieldFocused: { borderWidth: 1.5 },
  fieldMultiline: { minHeight: 132, textAlignVertical: "top" },
  centered: { alignItems: "center", flex: 1, gap: 12, justifyContent: "center", minHeight: 420 },
  loadingLabel: { fontSize: 15, textAlign: "center" },
  loadingHint: { fontSize: 14, lineHeight: 20, maxWidth: 340, textAlign: "center" },
  loadingMark: { alignSelf: "center", height: 56, marginBottom: 4, width: 56 },
  iconFrame: { alignItems: "center", height: 20, justifyContent: "center", width: 20 },
});
