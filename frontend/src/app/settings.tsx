import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { Body, Brand, Heading, Screen } from "@/components/ui";
import { ThemeColors, ThemePreference, useTheme } from "@/lib/theme";

const options: Array<{ label: string; value: ThemePreference; description: string }> = [
  { label: "System", value: "system", description: "Follow your device setting" },
  { label: "Light", value: "light", description: "Always use the light theme" },
  { label: "Dark", value: "dark", description: "Always use the dark theme" },
];

export default function SettingsRoute() {
  const router = useRouter();
  const { colors, preference, setPreference } = useTheme();
  const styles = createStyles(colors);
  return (
    <Screen>
      <Brand />
      <Pressable accessibilityRole="button" onPress={() => router.back()} style={styles.back}>
        <Text style={styles.backText}>‹ Back</Text>
      </Pressable>
      <Heading>Appearance</Heading>
      <Body>Choose how CareerOS looks on this device.</Body>
      <View accessibilityRole="radiogroup" style={styles.options}>
        {options.map((option) => {
          const selected = preference === option.value;
          return (
            <Pressable
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              key={option.value}
              onPress={() => setPreference(option.value)}
              style={({ pressed }) => [styles.option, selected && styles.optionSelected, pressed && styles.pressed]}
            >
              <View style={[styles.radio, selected && styles.radioSelected]}>{selected ? <View style={styles.radioDot} /> : null}</View>
              <View style={styles.copy}>
                <Text style={styles.optionLabel}>{option.label}</Text>
                <Text style={styles.optionDescription}>{option.description}</Text>
              </View>
            </Pressable>
          );
        })}
      </View>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  back: { alignSelf: "flex-start", marginBottom: 18, minHeight: 44, justifyContent: "center" },
  backText: { color: colors.forest, fontSize: 15, fontWeight: "800" },
  options: { gap: 12 },
  option: { alignItems: "center", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, flexDirection: "row", minHeight: 76, paddingHorizontal: 17, paddingVertical: 14 },
  optionSelected: { backgroundColor: colors.forestSoft, borderColor: colors.forest, borderWidth: 2 },
  pressed: { opacity: 0.8 },
  radio: { alignItems: "center", borderColor: colors.muted, borderRadius: 12, borderWidth: 2, height: 24, justifyContent: "center", marginRight: 14, width: 24 },
  radioSelected: { borderColor: colors.forest },
  radioDot: { backgroundColor: colors.forest, borderRadius: 6, height: 12, width: 12 },
  copy: { flex: 1 },
  optionLabel: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  optionDescription: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 3 },
});
