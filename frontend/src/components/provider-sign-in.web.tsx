import { useEffect, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import type { ProviderSignInProps } from "@/components/provider-sign-in";
import { ThemeColors, useTheme } from "@/lib/theme";

type GoogleCredentialResponse = { credential?: string };

type GoogleAccounts = {
  id: {
    initialize: (options: {
      callback: (response: GoogleCredentialResponse) => void;
      client_id: string;
    }) => void;
    renderButton: (
      element: HTMLElement,
      options: { shape: string; size: string; text: string; theme: string; width: number },
    ) => void;
  };
};

declare global {
  interface Window {
    google?: { accounts: GoogleAccounts };
  }
}

const GOOGLE_SCRIPT_ID = "careeros-google-identity";

function loadGoogleIdentity(): Promise<void> {
  if (window.google?.accounts) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google sign-in could not load.")), {
        once: true,
      });
      return;
    }
    const script = document.createElement("script");
    script.async = true;
    script.defer = true;
    script.id = GOOGLE_SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google sign-in could not load."));
    document.head.appendChild(script);
  });
}

export function ProviderSignIn({
  disabled,
  mode = "sign-in",
  onError,
  onEmailTestSignIn,
  onIdentityToken,
  providerConfig,
}: ProviderSignInProps) {
  const { colors, isDark } = useTheme();
  const styles = createStyles(colors);
  const buttonHost = useRef<View>(null);
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const clientId = providerConfig.google_web_client_id;

  useEffect(() => {
    if (!clientId || disabled) return;
    let active = true;
    setLoading(true);
    loadGoogleIdentity()
      .then(() => {
        if (!active || !window.google || !buttonHost.current) return;
        window.google.accounts.id.initialize({
          callback: (response) => {
            if (response.credential) onIdentityToken("google", response.credential);
            else onError("Google did not return a sign-in response. Please try again.");
          },
          client_id: clientId,
        });
        const element = buttonHost.current as unknown as HTMLElement;
        element.replaceChildren();
        window.google.accounts.id.renderButton(element, {
          shape: "pill",
          size: "large",
          text: mode === "sign-in" ? "continue_with" : "signin_with",
          theme: isDark ? "filled_black" : "outline",
          width: Math.min(360, element.clientWidth || 320),
        });
      })
      .catch((caught) => {
        if (active) onError(caught instanceof Error ? caught.message : "Google sign-in could not load.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [clientId, disabled, isDark, mode, onError, onIdentityToken]);

  const emailTestEnabled = providerConfig.email_test && Boolean(onEmailTestSignIn);

  if (!clientId && !emailTestEnabled) {
    return (
      <View style={styles.note}>
        <Text style={styles.title}>Sign-in setup is the final activation step.</Text>
        <Text style={styles.body}>
          Add the Apple and Google OAuth client IDs to activate secure sign-in. CareerOS does not
          save goals before sign-in.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.providerArea}>
      {clientId ? (
        <>
          <View accessibilityLabel="Sign in with Google" ref={buttonHost} style={styles.googleHost} />
          {loading ? <Text style={styles.loading}>Loading secure Google sign-in…</Text> : null}
        </>
      ) : null}
      {emailTestEnabled ? (
        <View style={styles.emailTestCard}>
          <Text style={styles.emailTestTitle}>Email sign-in for beta testing</Text>
          <Text style={styles.body}>
            Use the approved email and temporary access code provided by CareerOS.
          </Text>
          <TextInput
            autoCapitalize="none"
            autoComplete="email"
            editable={!disabled}
            keyboardType="email-address"
            onChangeText={setEmail}
            placeholder="Email address"
            placeholderTextColor={colors.muted}
            style={styles.emailInput}
            value={email}
          />
          <TextInput
            autoCapitalize="characters"
            editable={!disabled}
            onChangeText={setAccessCode}
            placeholder="Temporary access code"
            placeholderTextColor={colors.muted}
            secureTextEntry
            style={styles.emailInput}
            value={accessCode}
          />
          <Pressable
            accessibilityRole="button"
            disabled={disabled || !email.trim() || !accessCode}
            onPress={() => onEmailTestSignIn?.(email.trim(), accessCode)}
            style={({ pressed }) => [
              styles.emailButton,
              (disabled || !email.trim() || !accessCode) && styles.disabled,
              pressed && styles.pressed,
            ]}
          >
            <Text style={styles.emailButtonLabel}>Continue with email</Text>
          </Pressable>
        </View>
      ) : null}
      {!providerConfig.apple ? (
        <Text style={styles.body}>Sign in with Apple activates with the iOS build configuration.</Text>
      ) : null}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
    disabled: { opacity: 0.5 },
    emailButton: { alignItems: "center", backgroundColor: colors.forest, borderRadius: 22, minHeight: 48, justifyContent: "center", paddingHorizontal: 18 },
    emailButtonLabel: { color: colors.onForest, fontSize: 15, fontWeight: "800" },
    emailInput: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, color: colors.ink, fontSize: 15, minHeight: 46, paddingHorizontal: 13 },
    emailTestCard: { backgroundColor: colors.cardMuted, borderColor: colors.line, borderRadius: 14, borderWidth: 1, gap: 10, padding: 14 },
    emailTestTitle: { color: colors.ink, fontSize: 15, fontWeight: "800" },
    googleHost: { alignItems: "center", minHeight: 44, width: "100%" },
    loading: { color: colors.muted, fontSize: 13, textAlign: "center" },
    note: {
      backgroundColor: colors.cardMuted,
      borderColor: colors.line,
      borderRadius: 14,
      borderWidth: 1,
      gap: 5,
      padding: 14,
    },
    providerArea: { gap: 10 },
    pressed: { opacity: 0.86 },
    title: { color: colors.ink, fontSize: 14, fontWeight: "800" },
  });
