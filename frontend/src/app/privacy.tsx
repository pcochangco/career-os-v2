import { LegalDocument, LegalSection, SUPPORT_EMAIL } from "@/components/legal-document";

export default function PrivacyRoute() {
  return (
    <LegalDocument title="Privacy policy">
      <LegalSection title="What CareerOS stores">
        CareerOS stores the goals, discovery answers, roadmaps, step progress, notes, and evidence links you choose to add. A random guest session token is stored on your device so you can return without signing in. If you save your progress with Apple or Google, CareerOS also stores the provider account identifier and any email address the provider supplies.
      </LegalSection>
      <LegalSection title="How the data is used">
        Your information is used to create and maintain your personal roadmap, restore your progress, protect your session, and improve reliability. CareerOS does not sell your personal information or use it for advertising.
      </LegalSection>
      <LegalSection title="AI and external services">
        Goal and discovery content needed to generate a roadmap may be sent to the configured AI provider. Learning-resource searches may be sent to search, video, or reference providers. CareerOS is hosted on Render, and Apple or Google processes sign-in when you choose an account. Do not put passwords, financial records, medical records, or another person’s private information into a goal or note.
      </LegalSection>
      <LegalSection title="Retention and deletion">
        CareerOS keeps app data while the guest session or saved account exists. Deleting guest data or a saved account removes the associated CareerOS goals, roadmaps, progress, notes, identities, and active sessions. Limited operational records or backups may remain temporarily where needed for security, recovery, or legal compliance before expiring under the relevant provider’s retention process.
      </LegalSection>
      <LegalSection title="Your choices">
        You can use CareerOS as a guest, link an account only when you want cross-device access, sign out, or permanently delete your CareerOS data from Settings. You can also revoke CareerOS access from Apple or Google; revoking provider access does not replace deleting the CareerOS account.
      </LegalSection>
      <LegalSection title="Contact and changes">
        {SUPPORT_EMAIL
          ? `Privacy questions can be sent to ${SUPPORT_EMAIL}. Material changes to this policy will be reflected on this page with a new effective date.`
          : "A dedicated privacy contact will be published here before public beta. Material changes to this policy will be reflected on this page with a new effective date."}
      </LegalSection>
    </LegalDocument>
  );
}
