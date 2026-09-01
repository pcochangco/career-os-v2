import * as AppleAuthentication from "expo-apple-authentication";
import { useEffect, useState } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
import {
  GoogleSignInButton,
  GoogleOneTapSignIn,
} from "react-native-nitro-google-signin";

import { Account, IdentityProvider } from "@/lib/session";
import { ThemeColors, useTheme } from "@/lib/theme";

export type ProviderSignInProps = {
  account: Account;
  disabled: boolean;
  onError: (message: string) => void;
  onIdentityToken: (provider: IdentityProvider, token: string) => void;
};

export function ProviderSignIn({
  account,
  disabled,
  onError,
  onIdentityToken,
}: ProviderSignInProps) {
  const { colors, isDark } = useTheme();
  const styles = createStyles(colors);
  const [appleAvailable, setAppleAvailable] = useState(false);
  const [providerLoading, setProviderLoading] = useState<IdentityProvider | null>(null);
  const googleConfigured = Boolean(
    account.provider_config.google && account.provider_config.google_web_client_id,
  );

  useEffect(() => {
    if (!googleConfigured) return;
    GoogleOneTapSignIn.configure({
      autoSelectOnSignIn: false,
      iosClientId: account.provider_config.google_ios_client_id || undefined,
      webClientId: account.provider_config.google_web_client_id,
    });
  }, [
    account.provider_config.google_ios_client_id,
    account.provider_config.google_web_client_id,
    googleConfigured,
  ]);

  useEffect(() => {
    if (Platform.OS !== "ios" || !account.provider_config.apple) return;
    let active = true;
    AppleAuthentication.isAvailableAsync()
      .then((available) => active && setAppleAvailable(available))
      .catch(() => active && setAppleAvailable(false));
    return () => {
      active = false;
    };
  }, [account.provider_config.apple]);

  async function handleAppleSignIn() {
    try {
      setProviderLoading("apple");
      const credential = await AppleAuthentication.signInAsync({
        requestedScopes: [
          AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
          AppleAuthentication.AppleAuthenticationScope.EMAIL,
        ],
      });
      if (!credential.identityToken) {
        throw new Error("Apple did not return a secure identity token.");
      }
      await onIdentityToken("apple", credential.identityToken);
    } catch (caught) {
      if (
        caught instanceof Error &&
        "code" in caught &&
        caught.code === "ERR_REQUEST_CANCELED"
      ) {
        return;
      }
      onError(caught instanceof Error ? caught.message : "Apple sign-in could not start.");
    } finally {
      setProviderLoading(null);
    }
  }

  if (!googleConfigured && !appleAvailable) {
    return (
      <View style={styles.note}>
        <Text style={styles.title}>Account linking is ready for provider setup.</Text>
        <Text style={styles.body}>
          Add the Apple and Google client IDs to activate sign-in. Guest progress remains safely
          stored on this device in the meantime.
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.providerArea}>
      {appleAvailable ? (
        <AppleAuthentication.AppleAuthenticationButton
          buttonStyle={
            isDark
              ? AppleAuthentication.AppleAuthenticationButtonStyle.WHITE
              : AppleAuthentication.AppleAuthenticationButtonStyle.BLACK
          }
          buttonType={AppleAuthentication.AppleAuthenticationButtonType.CONTINUE}
          cornerRadius={22}
          onPress={() => {
            if (!disabled && providerLoading === null) void handleAppleSignIn();
          }}
          style={[styles.providerButton, (disabled || providerLoading !== null) && styles.disabled]}
        />
      ) : null}
      {googleConfigured ? (
        <GoogleSignInButton
          colorScheme={isDark ? "dark" : "light"}
          disabled={disabled || providerLoading !== null}
          onSignInError={(caught) => {
            onError(caught instanceof Error ? caught.message : "Google sign-in could not start.");
          }}
          onSignInSuccess={(data) => {
            if (!data.idToken) {
              onError("Google did not return a secure identity token.");
              return;
            }
            void onIdentityToken("google", data.idToken);
          }}
          signInBehavior="buttonFlow"
          size="wide"
          style={styles.providerButton}
        />
      ) : null}
      {providerLoading ? (
        <Text accessibilityLiveRegion="polite" style={styles.loading}>
          Opening {providerLoading === "apple" ? "Apple" : "Google"} sign-in…
        </Text>
      ) : null}
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
    disabled: { opacity: 0.5 },
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
    providerButton: { height: 48, width: "100%" },
    title: { color: colors.ink, fontSize: 14, fontWeight: "800" },
  });
