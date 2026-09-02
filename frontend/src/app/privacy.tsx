import { LegalDocument, LegalSection, SUPPORT_EMAIL } from "@/components/legal-document";

export default function PrivacyRoute() {
  return (
    <LegalDocument title="Privacy policy">
      <LegalSection title="What CareerOS stores">
        CareerOS stores the goals, discovery answers, roadmaps, step progress, learning records, and issue reports you choose to add after signing in. A random CareerOS session token is stored on your device so you can return securely. CareerOS also stores the Apple or Google account identifier and any email address the provider supplies. Text typed on the public start screen stays only in the current screen until you sign in and confirm it.
      </LegalSection>
      <LegalSection title="How the data is used">
        Your information is used to create and maintain your personal roadmap, restore your progress, protect your session, and improve reliability. CareerOS does not sell your personal information or use it for advertising.
      </LegalSection>
      <LegalSection title="AI and external services">
        Goal and discovery content needed to generate a roadmap may be sent to the configured AI provider. Learning-resource searches may be sent to search, video, or reference providers. CareerOS is hosted on Render, and Apple or Google processes sign-in when you choose an account. Do not put passwords, financial records, medical records, or another person’s private information into a goal or note.
      </LegalSection>
      <LegalSection title="Retention and deletion">
        CareerOS keeps app data while your account exists. Deleting the account removes its CareerOS goals, roadmaps, progress, learning records, issue reports, identities, and active sessions. Limited operational records or backups may remain temporarily where needed for security, recovery, or legal compliance before expiring under the relevant provider’s retention process.
      </LegalSection>
      <LegalSection title="Your choices">
        You can preview how CareerOS works without an account. Sign-in is required before a goal is saved. You can sign out or permanently delete your CareerOS data from Settings. You can also revoke CareerOS access from Apple or Google; revoking provider access does not replace deleting the CareerOS account.
      </LegalSection>
      <LegalSection title="Contact and changes">
        {SUPPORT_EMAIL
          ? `Privacy questions can be sent to ${SUPPORT_EMAIL}. Material changes to this policy will be reflected on this page with a new effective date.`
          : "A dedicated privacy contact will be published here before public beta. Material changes to this policy will be reflected on this page with a new effective date."}
      </LegalSection>
    </LegalDocument>
  );
}
