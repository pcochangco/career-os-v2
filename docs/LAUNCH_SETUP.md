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
- [ ] Decide whether Groq's free tier is enough. Staged generation (Nov 2026) fits its output caps, but its per-minute limits make big roadmaps slow (about a minute for a typical goal, several for a large career change). Options: a paid Groq tier, or a different provider via `CAREEROS_AI_*` variables. No code change needed either way.
- [ ] Before switching, compare locally: put the new model's settings and key in `backend/.env`, then run `uv run python evals/run_live.py --limit 1 --confirm-live --strategy staged` (and `--strategy single`). It prints quality score, milestones, steps, tokens and time.
- [ ] When switching to a stronger model, change on Render: the three model names (`CAREEROS_AI_MODEL`, `_CRITIC_MODEL`, `_REPAIR_MODEL`); raise the `*_MAX_COMPLETION_TOKENS` caps to what the model allows; consider `CAREEROS_AI_REASONING_EFFORT=medium`; switch `CAREEROS_AI_GENERATION_STRATEGY` to `single` only if the model handles ~15,000+ output tokens in one answer. Check the result at `/api/v1/health`.

## 8. Native apps (only when shipping to the stores)
- [ ] Build with `EXPO_PUBLIC_API_URL=https://your-domain/api/v1`.
- [ ] Fill in the Apple privacy disclosure and Google Play Data safety form (analytics are first-party; no third-party SDK tracking).

## 9. Final launch check
- [ ] Run `docs/RELEASE_CHECKLIST.md` end to end on the new domain, including deleting a test account.
- [ ] Ask Claude to tag the launch release.
- [ ] Update `docs/HANDOVER.md` section 7 (auth) and section 9 (open items) to match.

## Environment variables (reference)

### How Render settings work
- **Render → `career-os` → Environment** lists only the variables someone set explicitly. Every other setting still exists: it uses the **default in code** (`backend/app/core/config.py`). Those are the "hidden" settings below; to change one, add it on that page with the same name.
- `render.yaml` in the repo is **reference only**. The live service is configured in the dashboard, and the dashboard wins. (Example: `render.yaml` once said `CAREEROS_AI_MODE=live`, but production runs `auto`.)
- Saving a change on the Environment page redeploys the service.
- Check what's live without opening Render: `https://<your-domain>/api/v1/health` shows the AI mode, provider, model, generation strategy, roadmap skill, and whether the fallback is on. It never shows keys.
- **Secret** values (marked 🔒) go straight into Render. Never paste them into chat, docs, or commits.

Shown = "on Render" means it's normally set on the Environment page; "hidden" means it runs on the code default unless you add it.

### App and hosting
| Variable | What it does | Default | Where |
|---|---|---|---|
| `CAREEROS_ENVIRONMENT` | `production` turns on production-only rules (e.g. email codes can't be printed to logs) | `local` | on Render |
| `CAREEROS_APP_VERSION` | Version shown at `/api/v1/health` | `0.1.0` | on Render |
| `CAREEROS_DATABASE_URL` 🔒 | Supabase Postgres connection (Session pooler) | local Postgres | on Render |
| `CAREEROS_CORS_ORIGINS` | Other sites/apps allowed to call the API (the web app itself doesn't need it) | localhost dev ports | hidden |
| `CAREEROS_STATIC_DIRECTORY` | Where the built web app is served from | set by the Dockerfile to `/app/static` | hidden (Dockerfile) |
| `EXPO_PUBLIC_SUPPORT_EMAIL` | Support address shown in the web app; baked in at build time | empty | on Render |
| `EXPO_PUBLIC_API_URL` | API address for **native** builds only (step 8) | same-origin on web | build-time only |

### AI roadmap generation
| Variable | What it does | Default | Where |
|---|---|---|---|
| `CAREEROS_AI_MODE` | `fixture` = always the built-in roadmap; `live` = AI only (errors if it fails); `auto` = AI with the built-in roadmap as fallback | `fixture` | on Render (`auto`) |
| `CAREEROS_AI_PROVIDER` | Provider label used in logs/health (e.g. `groq`) | `openai` | on Render |
| `CAREEROS_AI_BASE_URL` | Provider's OpenAI-compatible API address | OpenAI | on Render |
| `CAREEROS_AI_API_KEY` 🔒 | Provider key; without it, `auto` uses the built-in roadmap | none | on Render |
| `CAREEROS_AI_MODEL` | Main model: writes the outline and milestone details | `gpt-5.6-terra` | on Render |
| `CAREEROS_AI_CRITIC_MODEL` | Reviews the roadmap outline; also takes turns writing milestone details (staged) | same as main | on Render |
| `CAREEROS_AI_REPAIR_MODEL` | Fixes the whole roadmap (single strategy only). In staged mode, a failed outline is fixed by the main model | same as main | on Render |
| `CAREEROS_AI_DISCOVERY_MODEL` | Asks the discovery questions and checks goal titles. If it fails (e.g. the provider retires the model), `auto` mode uses the built-in check and questions, and a retired model is retried with the main model; check logs for `Live discovery failed` / `AI model not found` | same as main | on Render (`openai/gpt-oss-20b`) |
| `CAREEROS_AI_RESPONSE_FORMAT` | `json_schema` (strict) or `json_object` (wider provider support) | `json_schema` | on Render |
| `CAREEROS_AI_REASONING_EFFORT` | `low`/`medium`/`high` thinking, for models that support it | off | on Render |
| `CAREEROS_AI_GENERATION_STRATEGY` | `staged` = outline, then one small call per milestone (fits free-tier caps); `single` = whole roadmap in one call (big paid models) | `staged` | hidden |
| `CAREEROS_ROADMAP_SKILL` | Folder under `backend/app/ai/skills/` with the roadmap guidance (`SKILL.md`). A wrong name stops the server at startup | `roadmap-mentor` | hidden |
| `CAREEROS_AI_GENERATION_TIME_BUDGET_SECONDS` | Total time for one roadmap; past it, the built-in roadmap is used | `240` | hidden |
| `CAREEROS_AI_MAX_COMPLETION_TOKENS` | Output cap for the outline and its repair (staged) or whole roadmap (single). On free tiers, raising it causes rate-limit errors | `5000` | on Render |
| `CAREEROS_AI_EXPAND_MAX_COMPLETION_TOKENS` | Output cap for each milestone's details (staged) | `2500` | hidden |
| `CAREEROS_AI_EXPAND_MODELS` | Comma-separated models that write milestone details in turn (staged). Avoid models whose hidden reasoning eats the answer budget (Qwen did, in Nov 2026 tests) | main + critic model | hidden |
| `CAREEROS_AI_CRITIC_MAX_COMPLETION_TOKENS` | Output cap for the review | `1600` | on Render |
| `CAREEROS_AI_REPAIR_MAX_COMPLETION_TOKENS` | Output cap for a whole-roadmap repair (single strategy) | `4800` | on Render |
| `CAREEROS_AI_DISCOVERY_MAX_COMPLETION_TOKENS` | Output cap for each discovery question | `700` | on Render |
| `CAREEROS_AI_REQUEST_TIMEOUT_SECONDS` | Max wait for one AI call | `60` | on Render |
| `CAREEROS_AI_TRANSIENT_RETRY_ATTEMPTS` / `_DELAY_SECONDS` | Whole-run retries on outages (single strategy only; staged waits out rate limits per call) | `1` / `3` | on Render |
| `CAREEROS_AI_MAX_REPAIR_ATTEMPTS` | Repair rounds before falling back | `1` | on Render |
| `CAREEROS_AI_QUALITY_THRESHOLD` | Minimum quality score (0–100) to accept an AI roadmap | `80` | on Render |
| `CAREEROS_AI_GENERATION_LIMIT_PER_HOUR` / `_GLOBAL_…` | Roadmap generations per user / for everyone per hour | `3` / `12` | on Render |
| `CAREEROS_AI_DISCOVERY_LIMIT_PER_HOUR` / `_GLOBAL_…` | Discovery questions per user / everyone per hour | `8` / `40` | hidden |
| `CAREEROS_AI_GOAL_INTENT_LIMIT_PER_HOUR` / `_GLOBAL_…` | Goal-title checks per user / everyone per hour | `4` / `40` | hidden |
| `CAREEROS_AI_LIVE_EVALUATION_CASE_LIMIT` | Max cases `evals/run_live.py` may run at once | `3` | hidden |

Roadmap **size** (up to 10 milestones / 40 steps) is set by the skill and the quality checks in code, not by an environment variable.

### Learning resources
| Variable | What it does | Default | Where |
|---|---|---|---|
| `CAREEROS_YOUTUBE_API_KEY` 🔒 | Finds videos for steps | none (no videos) | on Render |
| `CAREEROS_BRAVE_SEARCH_API_KEY` 🔒 | Finds articles for steps | none (no articles) | on Render |
| `CAREEROS_RESOURCE_MAX_RESULTS_PER_STEP` | Resources shown per step | `3` | hidden |
| `CAREEROS_RESOURCE_CACHE_TTL_HOURS` | How long found resources are reused | `168` (7 days) | hidden |
| `CAREEROS_RESOURCE_REQUEST_TIMEOUT_SECONDS` | Max wait for YouTube/web search | `4` | hidden |
| `CAREEROS_RESOURCE_ALTERNATE_LIMIT_PER_STEP_PER_DAY` | "Find another" presses per step per day | `3` | on Render |
| `CAREEROS_RESOURCE_ALTERNATE_COOLDOWN_SECONDS` | Wait between "Find another" presses | `12` | on Render |

### Sign-in and accounts
| Variable | What it does | Default | Where |
|---|---|---|---|
| `CAREEROS_ALLOW_GUEST_ACCESS` | Allow use without an account | `true` | on Render (`false`) |
| `CAREEROS_EMAIL_TEST_LOGIN_EMAILS` | Beta testers allowed to use the access code (remove at launch, step 4) | empty | on Render |
| `CAREEROS_EMAIL_TEST_ACCESS_CODE` 🔒 | The beta access code (remove at launch) | none | on Render |
| `CAREEROS_EMAIL_CODE_LOGIN_ENABLED` | Turns on emailed 6-digit sign-in codes (step 4) | `false` | add at step 4 |
| `CAREEROS_EMAIL_SENDER` | `resend` in production (`log` prints codes, local only) | `log` | add at step 4 |
| `CAREEROS_EMAIL_FROM` | Sender, e.g. `CareerOS <sign-in@your-domain>` | empty | add at step 4 |
| `CAREEROS_RESEND_API_KEY` 🔒 | Resend sending key | none | add at step 4 |
| `CAREEROS_GOOGLE_WEB_CLIENT_ID` / `_IOS_` / `_ANDROID_` | Google sign-in client IDs (step 5) | empty (no Google button) | on Render |
| `CAREEROS_APPLE_CLIENT_IDS` | Apple sign-in client IDs (native) | empty | on Render |
| `CAREEROS_MANUAL_PREMIUM_EMAILS` | Accounts given Premium by hand | empty | on Render |
| `CAREEROS_AUTH_ANONYMOUS_LIMIT_PER_15_MINUTES` | Guest sessions per client (IP + browser) per 15 min | `120` | on Render |
| `CAREEROS_AUTH_IDENTITY_LIMIT_PER_15_MINUTES` | Sign-in attempts per client per 15 min | `20` | on Render |
| `CAREEROS_AUTH_DELETION_LIMIT_PER_15_MINUTES` | Account-deletion attempts per client per 15 min | `5` | on Render |

