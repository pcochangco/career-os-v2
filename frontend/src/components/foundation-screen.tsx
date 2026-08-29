import { SafeAreaView } from "react-native-safe-area-context";
import { StyleSheet, Text, View } from "react-native";

export function FoundationScreen() {
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <Text style={styles.eyebrow}>CareerOS</Text>
        <Text style={styles.title}>Your goal. A clear path forward.</Text>
        <Text style={styles.description}>
          CareerOS is being built around one simple experience: open a goal,
          see your roadmap, and continue from where you stopped.
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F8FAF7",
    flex: 1,
  },
  content: {
    alignSelf: "center",
    flex: 1,
    justifyContent: "center",
    maxWidth: 560,
    paddingHorizontal: 24,
    paddingVertical: 48,
    width: "100%",
  },
  eyebrow: {
    color: "#286447",
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: 0.8,
    marginBottom: 16,
    textTransform: "uppercase",
  },
  title: {
    color: "#17211B",
    fontSize: 40,
    fontWeight: "700",
    letterSpacing: -1.2,
    lineHeight: 46,
    marginBottom: 20,
  },
  description: {
    color: "#526158",
    fontSize: 18,
    lineHeight: 28,
  },
});
