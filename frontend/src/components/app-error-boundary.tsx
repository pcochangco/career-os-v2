import { Component, ErrorInfo, ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ThemeColors, useTheme } from "@/lib/theme";

type BoundaryProps = { children: ReactNode; colors: ThemeColors };
type BoundaryState = { hasError: boolean };

class Boundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { hasError: false };

  static getDerivedStateFromError(): BoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("CareerOS screen crashed", error.name, info.componentStack);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const styles = createStyles(this.props.colors);
    return (
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.content}>
          <Text style={styles.brand}>CareerOS</Text>
          <Text accessibilityRole="header" style={styles.heading}>This screen needs a fresh start.</Text>
          <Text style={styles.body}>
            Your saved progress is still available. Reopen the screen and try the last action again.
          </Text>
          <Pressable
            accessibilityRole="button"
            onPress={() => this.setState({ hasError: false })}
            style={({ pressed }) => [styles.button, pressed && styles.pressed]}
          >
            <Text style={styles.buttonLabel}>Reopen CareerOS</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }
}

export function AppErrorBoundary({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  return <Boundary colors={colors}>{children}</Boundary>;
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  body: { color: colors.muted, fontSize: 17, lineHeight: 26, marginBottom: 24 },
  brand: { color: colors.forest, fontSize: 15, fontWeight: "800", letterSpacing: 0.8, marginBottom: 22, textTransform: "uppercase" },
  button: { alignItems: "center", backgroundColor: colors.forest, borderRadius: 16, justifyContent: "center", minHeight: 52, paddingHorizontal: 22 },
  buttonLabel: { color: colors.onForest, fontSize: 16, fontWeight: "800" },
  content: { alignSelf: "center", flex: 1, justifyContent: "center", maxWidth: 560, paddingHorizontal: 20, width: "100%" },
  heading: { color: colors.ink, fontSize: 32, fontWeight: "800", lineHeight: 39, marginBottom: 14 },
  pressed: { opacity: 0.82 },
  safeArea: { backgroundColor: colors.background, flex: 1 },
});
