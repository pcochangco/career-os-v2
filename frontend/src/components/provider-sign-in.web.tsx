import { useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

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
  account,
  disabled,
  onError,
  onIdentityToken,
}: ProviderSignInProps) {
  const { colors, isDark } = useTheme();
  const styles = createStyles(colors);
  const buttonHost = useRef<View>(null);
  const [loading, setLoading] = useState(false);
  const clientId = account.provider_config.google_web_client_id;

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
          text: account.status === "guest" ? "continue_with" : "signin_with",
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
  }, [account.status, clientId, disabled, isDark, onError, onIdentityToken]);

  if (!clientId) {
    return (
      <View style={styles.note}>
        <Text style={styles.title}>Account linking is ready for provider setup.</Text>
        <Text style={styles.body}>
          Add the Apple and Google OAuth client IDs to activate sign-in. Guest progress remains on
          this device in the meantime.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.providerArea}>
      <View accessibilityLabel="Sign in with Google" ref={buttonHost} style={styles.googleHost} />
      {loading ? <Text style={styles.loading}>Loading secure Google sign-in…</Text> : null}
      {!account.provider_config.apple ? (
        <Text style={styles.body}>Sign in with Apple activates with the iOS build configuration.</Text>
      ) : null}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
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
    title: { color: colors.ink, fontSize: 14, fontWeight: "800" },
  });
