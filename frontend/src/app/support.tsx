import { Linking } from "react-native";

import { LegalDocument, LegalSection, SUPPORT_EMAIL } from "@/components/legal-document";
import { Button } from "@/components/ui";

export default function SupportRoute() {
  return (
    <LegalDocument title="CareerOS support">
      <LegalSection title="Open your progress">
        Sign in with the same Apple or Google identity you used when creating the account. CareerOS opens only that saved account’s goals and never imports data from another browser session.
      </LegalSection>
      <LegalSection title="Roadmap or connection errors">
        Retry the action once after checking your connection. CareerOS keeps completed discovery answers and existing roadmap state during normal retries. If an error displays a request reference, include that reference in a support message without sending your access token or private notes.
      </LegalSection>
      <LegalSection title="Contact">
        {SUPPORT_EMAIL
          ? `Email ${SUPPORT_EMAIL} for account, privacy, or technical support. Do not include passwords, provider tokens, or sensitive goal content.`
          : "A dedicated support email will be published here before public beta. Account deletion remains available directly in Settings."}
      </LegalSection>
      {SUPPORT_EMAIL ? (
        <Button onPress={() => void Linking.openURL(`mailto:${SUPPORT_EMAIL}`)}>Email support</Button>
      ) : null}
    </LegalDocument>
  );
}
