import { useRouter } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { ProviderSignIn } from "@/components/provider-sign-in";
import { Body, Brand, Button, Heading, Screen } from "@/components/ui";
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
  const { account, accountLoading, deleteAccount, linkIdentity, signOut } = useSession();
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
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

  async function handleSignOut() {
    try {
      setActionError(null);
      await signOut();
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "You could not be signed out.");
    }
  }

  async function handleDeleteAccount() {
    try {
      setActionError(null);
      await deleteAccount();
      setConfirmDelete(false);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : "Your account could not be deleted.");
    }
  }

  return (
    <Screen>
      <Brand />
      <Pressable accessibilityRole="button" onPress={() => router.back()} style={styles.back}>
        <Text style={styles.backText}>‹ Back</Text>
      </Pressable>
      <Heading>Settings</Heading>
      <Text style={styles.sectionTitle}>Account</Text>
      <View style={styles.accountCard}>
        <Text style={styles.accountStatus}>
          {account?.status === "saved" ? "Progress saved" : "Guest mode"}
        </Text>
        <Text style={styles.accountDescription}>
          {account?.status === "saved"
            ? account.email || `Connected with ${account.providers.map((provider) => provider === "apple" ? "Apple" : "Google").join(" and ")}`
            : "Start immediately. Link an account when you want your goals on another device."}
        </Text>
        {account ? (
          <ProviderSignIn
            account={account}
            disabled={accountLoading}
            onError={handleProviderError}
            onIdentityToken={handleIdentityToken}
          />
        ) : (
          <Text style={styles.accountDescription}>Opening your account settings…</Text>
        )}
        {actionError ? (
          <Text accessibilityLiveRegion="polite" style={styles.errorText}>{actionError}</Text>
        ) : null}
        {account ? (
          <View style={styles.accountActions}>
            {account.status === "saved" ? (
              <Button disabled={accountLoading} loading={accountLoading} onPress={handleSignOut} secondary>
                Sign out
              </Button>
            ) : null}
            {confirmDelete ? (
              <View style={styles.deleteConfirm}>
                <Text style={styles.deleteWarning}>
                  {account.status === "saved"
                    ? "This permanently deletes your account, goals, roadmaps, notes, and progress on every device."
                    : "This permanently deletes this guest’s goals, roadmaps, notes, and progress. A new empty guest session will open."}
                </Text>
                <Button disabled={accountLoading} loading={accountLoading} onPress={handleDeleteAccount}>
                  {account.status === "saved" ? "Delete account permanently" : "Delete guest data permanently"}
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
                  {account.status === "saved" ? "Delete account" : "Delete guest data"}
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
  accountCard: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, gap: 12, marginBottom: 30, padding: 18 },
  accountDescription: { color: colors.muted, fontSize: 15, lineHeight: 22 },
  accountStatus: { color: colors.ink, fontSize: 19, fontWeight: "800" },
  back: { alignSelf: "flex-start", marginBottom: 18, minHeight: 44, justifyContent: "center" },
  backText: { color: colors.forest, fontSize: 15, fontWeight: "800" },
  deleteConfirm: { backgroundColor: colors.cardMuted, borderRadius: 14, gap: 12, padding: 14 },
  deleteLabel: { color: colors.danger, fontSize: 14, fontWeight: "800", textAlign: "center" },
  deleteWarning: { color: colors.danger, fontSize: 14, lineHeight: 21, textAlign: "center" },
  errorText: { color: colors.danger, fontSize: 14, lineHeight: 21 },
  legalLink: { alignItems: "center", borderBottomColor: colors.line, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 52, paddingHorizontal: 2 },
  legalLinkArrow: { color: colors.muted, fontSize: 24 },
  legalLinkText: { color: colors.forest, fontSize: 15, fontWeight: "800" },
  legalLinks: { backgroundColor: colors.card, borderColor: colors.line, borderRadius: 18, borderWidth: 1, marginBottom: 18, paddingHorizontal: 16 },
  legalTitle: { marginTop: 30 },
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
  sectionTitle: { color: colors.ink, fontSize: 21, fontWeight: "800", marginBottom: 10 },
  textAction: { alignItems: "center", justifyContent: "center", minHeight: 44, paddingHorizontal: 12 },
  textActionLabel: { color: colors.forest, fontSize: 14, fontWeight: "800" },
});
