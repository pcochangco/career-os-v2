import { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

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

export function Screen({ children }: { children: ReactNode }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.content}>{children}</View>
      </ScrollView>
    </SafeAreaView>
  );
}

export function Brand() {
  return <Text style={styles.brand}>CareerOS</Text>;
}

export function Heading({ children }: { children: ReactNode }) {
  return <Text style={styles.heading}>{children}</Text>;
}

export function Body({ children }: { children: ReactNode }) {
  return <Text style={styles.body}>{children}</Text>;
}

type ButtonProps = {
  children: ReactNode;
  disabled?: boolean;
  loading?: boolean;
  onPress: () => void;
  secondary?: boolean;
};

export function Button({ children, disabled, loading, onPress, secondary }: ButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        secondary ? styles.buttonSecondary : styles.buttonPrimary,
        (disabled || loading) && styles.buttonDisabled,
        pressed && styles.buttonPressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? colors.forest : colors.white} />
      ) : (
        <Text style={[styles.buttonLabel, secondary && styles.buttonLabelSecondary]}>{children}</Text>
      )}
    </Pressable>
  );
}

export function Field(props: TextInputProps) {
  return (
    <TextInput
      placeholderTextColor="#8A978F"
      {...props}
      style={[styles.field, props.multiline && styles.fieldMultiline, props.style]}
    />
  );
}

export function LoadingState({ label = "Opening your path…" }: { label?: string }) {
  return (
    <Screen>
      <View style={styles.centered}>
        <ActivityIndicator color={colors.forest} size="large" />
        <Text style={styles.loadingLabel}>{label}</Text>
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
  brand: {
    color: colors.forest,
    fontSize: 15,
    fontWeight: "800",
    letterSpacing: 0.8,
    marginBottom: 22,
    textTransform: "uppercase",
  },
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
  centered: { flex: 1, gap: 14, justifyContent: "center", minHeight: 420 },
  loadingLabel: { color: colors.muted, fontSize: 16, textAlign: "center" },
});
