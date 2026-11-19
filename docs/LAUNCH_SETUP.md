# Launch setup (owner checklist)

Everything here is account, money, DNS or environment work that only the owner can do. The code
for each step is already built and deployed; these steps switch it on. Work top to bottom: later
steps depend on earlier ones. Tick each box as you go.

Never paste keys or passwords into chat. Put them straight into Render → `career-os` → Environment.

## 1. Domain
- [ ] Buy the domain (e.g. `careeros.app`) from any registrar.
- [ ] Keep the registrar login handy: steps 2 and 3 add DNS records there.

## 2. Email sending (Resend)
- [ ] Create a Resend account (e.g. with `careeros.app.io@gmail.com`).
- [ ] Add the domain in Resend and copy the DNS records it shows (SPF, DKIM, optionally DMARC) into the registrar. Wait until Resend says **Verified**.
- [ ] Create a Resend API key (sending access only).

## 3. Custom domain on Render
- [ ] Render → `career-os` → Settings → Custom Domains → add the domain (and `www` if wanted).
- [ ] Add the DNS record Render shows at the registrar. Render issues HTTPS automatically.
- [ ] Open `https://your-domain/api/v1/health` → must return 200.
- [ ] If CareerOS is ever called from another site or a native build, add the domain to `CAREEROS_CORS_ORIGINS` (the web app is same-origin and doesn't need it).

## 4. Turn on email-code sign-in
Set in Render → Environment, then let it redeploy:
- [ ] `CAREEROS_EMAIL_CODE_LOGIN_ENABLED` = `true`
- [ ] `CAREEROS_EMAIL_SENDER` = `resend`
- [ ] `CAREEROS_EMAIL_FROM` = `CareerOS <sign-in@your-domain>`
- [ ] `CAREEROS_RESEND_API_KEY` = the key from step 2
- [ ] Check: `https://your-domain/api/v1/auth/config` shows `"email_code": true`.
- [ ] Sign in with a fresh email: the code arrives, signing in works, and it isn't in spam.
- [ ] Sign in with your beta email by code: you land in your existing account.
- [ ] Retire the beta access code: delete `CAREEROS_EMAIL_TEST_LOGIN_EMAILS` and `CAREEROS_EMAIL_TEST_ACCESS_CODE`. Keep `CAREEROS_MANUAL_PREMIUM_EMAILS` if you still want your account on Premium.

## 5. Google sign-in (when the appeal is resolved)
- [ ] Google Cloud project `careeros-production-508315`: confirm the Terms of Service review is cleared. Don't create a new project to work around it.
- [ ] OAuth client → Authorized JavaScript origins: add `https://your-domain` (and `https://career-os-41i5.onrender.com` while it's still used).
- [ ] Render: set `CAREEROS_GOOGLE_WEB_CLIENT_ID` (plus iOS/Android IDs for native builds).
- [ ] Check: the Google button appears on the sign-in screen and signing in works.

## 6. Database backups (before inviting real users)
Pick one:
- [ ] **Supabase Pro**: daily automatic backups, restore from the dashboard (paid). Confirm under Database → Backups.
- [ ] **Free**: ask Claude to add the nightly `pg_dump` GitHub Action, then add the database URL as a GitHub secret.
- [ ] Do one test restore into a throwaway database so you know it works.

## 7. AI provider decision
- [ ] Decide whether Groq's free tier is enough. Today it often hits limits, so many users get the (decent) fallback roadmap. Options: a paid Groq tier, or a different provider via `CAREEROS_AI_*` variables. No code change needed either way.

## 8. Native apps (only when shipping to the stores)
- [ ] Build with `EXPO_PUBLIC_API_URL=https://your-domain/api/v1`.
- [ ] Fill in the Apple privacy disclosure and Google Play Data safety form (analytics are first-party; no third-party SDK tracking).

## 9. Final launch check
- [ ] Run `docs/RELEASE_CHECKLIST.md` end to end on the new domain, including deleting a test account.
- [ ] Ask Claude to tag the launch release.
- [ ] Update `docs/HANDOVER.md` section 7 (auth) and section 9 (open items) to match.
