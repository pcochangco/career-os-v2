import { ReactNode, useEffect, useRef, useState } from "react";
import { AccessibilityInfo, Animated, DimensionValue, StyleSheet, Text, View } from "react-native";

import { useIsWide } from "@/components/app-shell";
import { Screen } from "@/components/ui";
import { radius, useTheme } from "@/lib/theme";

/**
 * Placeholder shapes in the layout of the screen that's loading, so content lands where the eye
 * already is instead of replacing a centred spinner. Pulses gently unless Reduce Motion is on.
 */
function usePulse(): Animated.Value {
  const opacity = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    let loop: Animated.CompositeAnimation | null = null;
    let cancelled = false;
    void AccessibilityInfo.isReduceMotionEnabled()
      .catch(() => false)
      .then((reduced) => {
        if (cancelled || reduced) return;
        loop = Animated.loop(
          Animated.sequence([
            Animated.timing(opacity, { duration: 700, toValue: 0.45, useNativeDriver: true }),
            Animated.timing(opacity, { duration: 700, toValue: 1, useNativeDriver: true }),
          ]),
        );
        loop.start();
      });
    return () => {
      cancelled = true;
      loop?.stop();
    };
  }, [opacity]);
  return opacity;
}

function Bone({
  height = 14,
  width = "100%",
  round = false,
}: {
  height?: number;
  width?: DimensionValue;
  round?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View
      style={{
        backgroundColor: colors.line,
        borderRadius: round ? height / 2 : radius.sm,
        height,
        width,
      }}
    />
  );
}

function Card({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.line }]}>
      {children}
    </View>
  );
}

/** Same wording as LoadingState: the free host sleeps when idle and can take a minute to wake. */
function SlowHint() {
  const { colors } = useTheme();
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 5000);
    return () => clearTimeout(timer);
  }, []);
  if (!slow) return null;
  return (
    <Text accessibilityLiveRegion="polite" style={[styles.hint, { color: colors.subtle }]}>
      Still working. If CareerOS hasn’t been used for a while, waking it up can take up to a
      minute.
    </Text>
  );
}

function SkeletonScreen({
  label,
  width,
  children,
}: {
  label: string;
  width?: "wide";
  children: ReactNode;
}) {
  const opacity = usePulse();
  return (
    <Screen width={width}>
      <View accessibilityLabel={label} accessibilityRole="progressbar" accessible>
        <Animated.View style={[styles.stack, { opacity }]}>{children}</Animated.View>
      </View>
      <SlowHint />
    </Screen>
  );
}

export function GoalsSkeleton() {
  const wide = useIsWide();
  return (
    <SkeletonScreen label="Loading your goals" width="wide">
      <Bone height={30} width={180} />
      <Bone width={300} />
      <View style={[styles.list, wide && styles.grid]}>
        {[0, 1].map((key) => (
          <View key={key} style={wide ? styles.gridItem : undefined}>
            <Card>
              <Bone height={20} width="70%" />
              <Bone width="45%" />
              <Bone height={8} round />
              <Bone width={80} />
            </Card>
          </View>
        ))}
      </View>
    </SkeletonScreen>
  );
}

export function RoadmapSkeleton() {
  const { colors } = useTheme();
  return (
    <SkeletonScreen label="Loading your roadmap">
      <Bone width={90} />
      <Bone height={30} width="80%" />
      <Bone height={8} round />
      <View style={[styles.hero, { backgroundColor: colors.line }]} />
      <Card>
        <Bone width={140} />
        <Bone height={20} width="65%" />
        {[0, 1, 2].map((key) => (
          <View key={key} style={styles.mapRow}>
            <Bone height={30} round width={30} />
            <View style={styles.mapCopy}>
              <Bone height={16} width="55%" />
              <Bone width="85%" />
            </View>
          </View>
        ))}
      </Card>
    </SkeletonScreen>
  );
}

const styles = StyleSheet.create({
  stack: { gap: 14 },
  card: { borderRadius: radius.lg, borderWidth: 1, gap: 12, padding: 18 },
  list: { gap: 12, marginTop: 10 },
  grid: { flexDirection: "row", flexWrap: "wrap" },
  gridItem: { flexBasis: "48%", flexGrow: 1 },
  hero: { borderRadius: radius.lg, height: 150 },
  mapRow: { alignItems: "center", flexDirection: "row", gap: 14 },
  mapCopy: { flex: 1, gap: 8 },
  hint: { fontSize: 13, lineHeight: 19, marginTop: 20, textAlign: "center" },
});
