import { useRouter } from "expo-router";
import { View } from "react-native";

import { LegalDocument, LegalSection } from "@/components/legal-document";
import { Button } from "@/components/ui";

export default function AccountDeletionRoute() {
  const router = useRouter();
  return (
    <LegalDocument title="Delete your CareerOS data">
      <LegalSection title="Delete from the app">
        Open Settings, find Account, choose “Delete guest data” or “Delete account,” review the warning, and confirm permanent deletion. The request takes effect immediately in CareerOS and signs out every session attached to the deleted user.
      </LegalSection>
      <LegalSection title="What is deleted">
        Deletion removes the CareerOS user record and its provider identity links, sessions, goals, discovery answers, roadmap versions, progress, private notes, evidence links, resource feedback, and generation history. The app then opens a new empty guest session on the current device.
      </LegalSection>
      <LegalSection title="If you are on another device">
        Open CareerOS, sign in with the Apple or Google identity connected to your saved account, then delete it from Settings. If provider sign-in is not yet enabled for the beta, use the support route shown on this site once the public contact address is published.
      </LegalSection>
      <LegalSection title="Provider access">
        Deleting CareerOS data removes CareerOS’s stored identity link. You may separately revoke CareerOS in your Apple ID or Google Account settings. Revoking provider access by itself does not delete data already stored in CareerOS.
      </LegalSection>
      <View style={{ marginTop: 22 }}>
        <Button onPress={() => router.push("/settings" as never)}>Open deletion settings</Button>
      </View>
    </LegalDocument>
  );
}
