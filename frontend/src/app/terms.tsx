import { LegalDocument, LegalSection, SUPPORT_EMAIL } from "@/components/legal-document";

export default function TermsRoute() {
  return (
    <LegalDocument title="Terms of use">
      <LegalSection title="Purpose">
        CareerOS is an early-stage planning tool that turns a goal and your answers into a suggested learning or action roadmap. You remain responsible for deciding whether a recommendation is suitable and for checking important requirements with qualified sources.
      </LegalSection>
      <LegalSection title="No professional guarantee">
        Roadmaps and resources may be incomplete, inaccurate, or unavailable. CareerOS does not guarantee admission, employment, certification, income, health, legal, financial, or other outcomes and is not a substitute for professional advice.
      </LegalSection>
      <LegalSection title="Acceptable use">
        Use CareerOS lawfully and only for information you are permitted to submit. Do not try to disrupt the service, bypass limits, access another user’s data, upload malicious content, or use generated material to mislead others.
      </LegalSection>
      <LegalSection title="Accounts and availability">
        Guest access is tied to the session stored on that device. Linking Apple or Google enables account recovery and cross-device access once those providers are configured. Features may change during beta, and the service may be paused for maintenance or provider outages.
      </LegalSection>
      <LegalSection title="Your content and deletion">
        You keep responsibility for the content you submit. You allow CareerOS and its service providers to process that content only as needed to operate the app. You may permanently delete guest data or a saved account from Settings.
      </LegalSection>
      <LegalSection title="Contact">
        {SUPPORT_EMAIL
          ? `Questions about these terms can be sent to ${SUPPORT_EMAIL}.`
          : "A dedicated support contact will be published here before public beta."}
      </LegalSection>
    </LegalDocument>
  );
}
