import { Linking } from "react-native";

import { LegalDocument, LegalSection, SUPPORT_EMAIL } from "@/components/legal-document";
import { Button } from "@/components/ui";

export default function SupportRoute() {
  return (
    <LegalDocument title="CareerOS support">
      <LegalSection title="Recover your progress">
        CareerOS first tries the guest session stored on this device. If you linked Apple or Google, open Settings and use the same provider to restore the saved account. Do not delete app storage before linking an account if the guest progress matters.
      </LegalSection>
      <LegalSection title="Roadmap or connection errors">
        Retry the action once after checking your connection. CareerOS keeps completed discovery answers and existing roadmap state during normal retries. If an error displays a request reference, include that reference in a support message without sending your access token or private notes.
      </LegalSection>
      <LegalSection title="Contact">
        {SUPPORT_EMAIL
          ? `Email ${SUPPORT_EMAIL} for account, privacy, or technical support. Do not include passwords, provider tokens, or sensitive goal content.`
          : "A dedicated support email will be published here before public beta. Account and guest-data deletion remain available directly in Settings."}
      </LegalSection>
      {SUPPORT_EMAIL ? (
        <Button onPress={() => void Linking.openURL(`mailto:${SUPPORT_EMAIL}`)}>Email support</Button>
      ) : null}
    </LegalDocument>
  );
}
