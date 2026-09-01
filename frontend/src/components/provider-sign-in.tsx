import { StyleSheet, Text, View } from "react-native";

import { Account, IdentityProvider } from "@/lib/session";
import { ThemeColors, useTheme } from "@/lib/theme";

export type ProviderSignInProps = {
  account: Account;
  disabled: boolean;
  onError: (message: string) => void;
  onIdentityToken: (provider: IdentityProvider, token: string) => void;
};

export function ProviderSignIn({ account }: ProviderSignInProps) {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const nativeProviderReady = account.provider_config.apple || account.provider_config.google;
  return (
    <View style={styles.note}>
      <Text style={styles.title}>
        {nativeProviderReady ? "Sign-in is configured." : "Account sign-in needs the native build."}
      </Text>
      <Text style={styles.body}>
        Apple and Google buttons will activate in the installable iOS and Android build. Your
        guest progress remains safely stored on this device until then.
      </Text>
    </View>
  );
}

const createStyles = (colors: ThemeColors) =>
  StyleSheet.create({
    body: { color: colors.muted, fontSize: 14, lineHeight: 21 },
    note: {
      backgroundColor: colors.cardMuted,
      borderColor: colors.line,
      borderRadius: 14,
      borderWidth: 1,
      gap: 5,
      padding: 14,
    },
    title: { color: colors.ink, fontSize: 14, fontWeight: "800" },
  });
