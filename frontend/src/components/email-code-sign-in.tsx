import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { apiRequest } from "@/lib/api";
import { ThemeColors, useTheme } from "@/lib/theme";

/**
 * Passwordless sign-in: enter an email, get a 6-digit code, enter it. Works the same on web and
 * native. The code request reveals nothing about whether an account exists.
 */
export function EmailCodeSignIn({
  disabled,
  onError,
  onSignIn,
}: {
  disabled: boolean;
  onError: (message: string) => void;
  onSignIn: (email: string, code: string) => void;
}) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function sendCode() {
    const address = email.trim();
    if (!address) return;
    setSending(true);
    try {
      await apiRequest<void>("/auth/email-code/request", { body: { email: address }, method: "POST" });
      setSentTo(address);
      setCode("");
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "We couldn't send the code. Try again.");
    } finally {
      setSending(false);
    }
  }

  const busy = disabled || sending;
  const codeComplete = /^\d{6}$/.test(code);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Continue with email</Text>
      {sentTo ? (
        <>
          <Text accessibilityLiveRegion="polite" style={styles.body}>
            We sent a 6-digit code to {sentTo}. It expires in 10 minutes.
          </Text>
          <TextInput
            accessibilityLabel="6-digit sign-in code"
            autoComplete="one-time-code"
            editable={!busy}
            inputMode="numeric"
            maxLength={6}
            onChangeText={(value) => setCode(value.replace(/\D/g, ""))}
            onSubmitEditing={() => codeComplete && onSignIn(sentTo, code)}
            placeholder="123456"
            placeholderTextColor={colors.muted}
            style={[styles.input, styles.codeInput]}
            textContentType="oneTimeCode"
            value={code}
          />
          <Pressable
            accessibilityRole="button"
            disabled={busy || !codeComplete}
            onPress={() => onSignIn(sentTo, code)}
            style={({ pressed }) => [
              styles.button,
              (busy || !codeComplete) && styles.disabled,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.buttonLabel}>Sign in</Text>
          </Pressable>
          <View style={styles.links}>
            <Pressable accessibilityRole="button" disabled={busy} onPress={() => void sendCode()} style={styles.link}>
              <Text style={styles.linkText}>{sending ? "Sending…" : "Send a new code"}</Text>
            </Pressable>
            <Pressable accessibilityRole="button" disabled={busy} onPress={() => setSentTo(null)} style={styles.link}>
              <Text style={styles.linkText}>Use a different email</Text>
            </Pressable>
          </View>
        </>
      ) : (
        <>
          <Text style={styles.body}>We’ll email you a one-time code. No password needed.</Text>
          <TextInput
            accessibilityLabel="Email address"
            autoCapitalize="none"
            autoComplete="email"
            editable={!busy}
            inputMode="email"
            keyboardType="email-address"
            onChangeText={setEmail}
            onSubmitEditing={() => void sendCode()}
            placeholder="you@example.com"
            placeholderTextColor={colors.muted}
            style={styles.input}
            textContentType="emailAddress"
            value={email}
          />
          <Pressable
            accessibilityRole="button"
            disabled={busy || !email.trim()}
            onPress={() => void sendCode()}
            style={({ pressed }) => [
              styles.button,
              (busy || !email.trim()) && styles.disabled,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.buttonLabel}>{sending ? "Sending…" : "Email me a code"}</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    card: { backgroundColor: colors.cardMuted, borderColor: colors.line, borderRadius: 14, borderWidth: 1, gap: 10, padding: 14 },
    title: { color: colors.ink, fontSize: 15, fontWeight: "800" },
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
    input: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, color: colors.ink, fontSize: 15, minHeight: 46, paddingHorizontal: 13 },
    codeInput: { fontSize: 22, fontWeight: "700", letterSpacing: 6, textAlign: "center" },
    button: { alignItems: "center", backgroundColor: colors.forest, borderRadius: 12, justifyContent: "center", minHeight: 48, paddingHorizontal: 18 },
    buttonLabel: { color: colors.onForest, fontSize: 15, fontWeight: "800" },
    links: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between" },
    link: { justifyContent: "center", minHeight: 44 },
    linkText: { color: colors.forest, fontSize: 14, fontWeight: "700" },
    disabled: { opacity: 0.5 },
    pressed: { opacity: 0.86 },
  });
