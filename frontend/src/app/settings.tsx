import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Platform, Pressable, Share, StyleSheet, Text, View } from "react-native";

import { ProviderSignIn } from "@/components/provider-sign-in";
import { AppHeader, Body, Button, Heading, Screen } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { IdentityProvider, useSession } from "@/lib/session";
import { ThemeColors, ThemePreference, useTheme } from "@/lib/theme";

const options: Array<{ label: string; value: ThemePreference; description: string }> = [
  { label: "System", value: "system", description: "Follow your device setting" },
  { label: "Light", value: "light", description: "Always use the light theme" },
  { label: "Dark", value: "dark", description: "Always use the dark theme" },
];

export default function SettingsRoute() {
  const router = useRouter();
  const { colors, preference, setPreference } = useTheme();
  const { account, accountLoading, deleteAccount, linkIdentity, signOut, token } = useSession();
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [exporting, setExporting] = useState(false);
  const styles = createStyles(colors);

  const handleProviderError = useCallback((message: string) => setActionError(message), []);
  const handleIdentityToken = useCallback(
    async (provider: IdentityProvider, identityToken: string) => {
      try {
        setActionError(null);
        await linkIdentity(provider, identityToken);
      } catch (caught) {
        setActionError(caught instanceof Error ? caught.message : "Your account could not be linked.");
      }
    },
    [linkIdentity],
  );

  async function handleExport() {
    if (!token || exporting) return;
    try {
      setExporting(true);
      setActionError(null);
      const data = await apiRequest<unknown>("/auth/account/export", { token });
      const json = JSON.stringify(data, null, 2);
      const filename = `careeros-export-${new Date().toISOString().slice(0, 10)}.json`;
      if (Platform.OS === "web" && typeof document !== "undefined") {
        const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } else {
        await Share.share({ message: json, title: filename });
      }
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Your data couldn’t be downloaded.");
    } finally {
      setExporting(false);
    }
  }

  async function handleSignOut() {
    try {
      setActionError(null);
      await signOut();
      router.replace("/");
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "You could not be signed out.");
    }
  }

  async function handleDeleteAccount() {
    try {
      setActionError(null);
      await deleteAccount();
      setConfirmDelete(false);
      router.replace("/");
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Your account could not be deleted.");
    }
  }

  return (
    <Screen width="narrow">
      <AppHeader />
      <Heading>Settings</Heading>
      <Text style={styles.sectionTitle}>Account</Text>
      <View style={styles.accountCard}>
        <Text style={styles.accountStatus}>Signed in</Text>
        <Text style={styles.accountDescription}>
          {account?.email || (account ? `Connected with ${account.providers.map((provider) => provider === "apple" ? "Apple" : provider === "google" ? "Google" : "email").join(" and ")}` : "Opening your account…")}
        </Text>
        {account ? (
          <Text style={styles.planLine}>
            {account.plan === "premium"
              ? "Premium plan · unlimited goals"
              : `Free plan · ${account.goal_limit ?? 2} goals in total`}
          </Text>
        ) : null}
        {account ? (
          <ProviderSignIn
            disabled={accountLoading}
            mode="link"
            onError={handleProviderError}
            onIdentityToken={handleIdentityToken}
            providerConfig={account.provider_config}
          />
        ) : (
          <Text style={styles.accountDescription}>Opening your account settings…</Text>
        )}
        {actionError ? (
          <Text accessibilityLiveRegion="polite" style={styles.errorText}>{actionError}</Text>
        ) : null}
        {account ? (
          <View style={styles.accountActions}>
            <Button disabled={accountLoading || exporting} loading={exporting} onPress={() => void handleExport()} secondary>
              Download my data
            </Button>
            <Button disabled={accountLoading} loading={accountLoading} onPress={handleSignOut} secondary>
              Sign out
            </Button>
            {confirmDelete ? (
              <View style={styles.deleteConfirm}>
                <Text style={styles.deleteWarning}>
                  This permanently deletes your account, goals, roadmaps, notes, and progress on
                  every device.
                </Text>
                <Button danger disabled={accountLoading} loading={accountLoading} onPress={handleDeleteAccount}>
                  Delete account permanently
                </Button>
                <Pressable
                  accessibilityRole="button"
                  disabled={accountLoading}
                  onPress={() => setConfirmDelete(false)}
                  style={styles.textAction}
                >
                  <Text style={styles.textActionLabel}>Keep my account</Text>
                </Pressable>
              </View>
            ) : (
              <Pressable
                accessibilityRole="button"
                disabled={accountLoading}
                onPress={() => setConfirmDelete(true)}
                style={styles.textAction}
              >
                <Text style={styles.deleteLabel}>
                  Delete account
                </Text>
              </Pressable>
            )}
          </View>
        ) : null}
      </View>
      <Text style={styles.sectionTitle}>Appearance</Text>
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
      <Text style={[styles.sectionTitle, styles.legalTitle]}>Privacy and support</Text>
      <View style={styles.legalLinks}>
        {[
          ["Privacy policy", "/privacy"],
          ["Terms of use", "/terms"],
          ["Account deletion", "/account-deletion"],
          ["Report an issue", "/report-issue"],
          ["Support", "/support"],
        ].map(([label, route]) => (
          <Pressable
            accessibilityRole="link"
            key={route}
            onPress={() => router.push(route as never)}
            style={({ pressed }) => [styles.legalLink, pressed && styles.pressed]}
          >
            <Text style={styles.legalLinkText}>{label}</Text>
            <Text style={styles.legalLinkArrow}>›</Text>
          </Pressable>
        ))}
      </View>
    </Screen>
  );
}

const createStyles = (colors: ThemeColors) => StyleSheet.create({
  accountActions: { gap: 12, marginTop: 4 },
  accountCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, gap: 12, marginBottom: 30, padding: 18 },
  accountDescription: { color: colors.muted, fontSize: 15, lineHeight: 22 },
  accountStatus: { color: colors.ink, fontSize: 17, fontWeight: "700" },
  planLine: { color: colors.subtle, fontSize: 14 },
  deleteConfirm: { backgroundColor: colors.cardMuted, borderRadius: 14, gap: 12, padding: 14 },
  deleteLabel: { color: colors.danger, fontSize: 14, fontWeight: "800", textAlign: "center" },
  deleteWarning: { color: colors.danger, fontSize: 14, lineHeight: 21, textAlign: "center" },
  errorText: { color: colors.danger, fontSize: 14, lineHeight: 21 },
  legalLink: { alignItems: "center", borderBottomColor: colors.line, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 52, paddingHorizontal: 2 },
  legalLinkArrow: { color: colors.muted, fontSize: 24 },
  legalLinkText: { color: colors.forest, fontSize: 15, fontWeight: "800" },
  legalLinks: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, marginBottom: 18, paddingHorizontal: 16 },
  legalTitle: { marginTop: 30 },
  options: { gap: 12 },
  option: { alignItems: "center", backgroundColor: colors.card, borderColor: colors.line, borderRadius: 12, borderWidth: 1, flexDirection: "row", minHeight: 76, paddingHorizontal: 17, paddingVertical: 14 },
  optionSelected: { backgroundColor: colors.forestSoft, borderColor: colors.forest, borderWidth: 2 },
  pressed: { opacity: 0.8 },
  radio: { alignItems: "center", borderColor: colors.muted, borderRadius: 12, borderWidth: 2, height: 24, justifyContent: "center", marginRight: 14, width: 24 },
  radioSelected: { borderColor: colors.forest },
  radioDot: { backgroundColor: colors.forest, borderRadius: 6, height: 12, width: 12 },
  copy: { flex: 1 },
  optionLabel: { color: colors.ink, fontSize: 16, fontWeight: "800" },
  optionDescription: { color: colors.muted, fontSize: 13, lineHeight: 19, marginTop: 3 },
  sectionTitle: { color: colors.ink, fontSize: 17, fontWeight: "700", marginBottom: 10, marginTop: 16 },
  textAction: { alignItems: "center", justifyContent: "center", minHeight: 44, paddingHorizontal: 12 },
  textActionLabel: { color: colors.forest, fontSize: 14, fontWeight: "800" },
});
