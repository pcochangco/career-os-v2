# CareerOS handover brief

_Originally written 2026-11-16 as the onboarding brief for a new working session. Sections 1, 9 and 12 updated 2026-11-19 after the user-journey production pass (PRs #6–#17)._

You are taking over CareerOS, an ongoing production project — not a fresh build. Read this whole brief, then inspect the repository before doing anything. Do not start coding until I give you a task; first confirm the repo state and run the baseline checks (section 11), then report back briefly.

Never print, commit, or ask me to paste API keys, database URLs, access codes, or OAuth secrets. This brief lists variable NAMES only. If you need a credential, tell me where to set it — don't ask for its value in chat.

GitHub is the truth for current code. This brief is the truth for intent and decisions.

---

## 1. Repository & deployment (current state, 2026-11-19)

| Item | Value |
|---|---|
| GitHub repo | `pcochangco/career-os-v2`, branch `main` |
| Latest commit | see `git log`; journey pass ended at `54904aa` (PR #17) |
| Production URL | https://career-os-41i5.onrender.com |
| Web host | Render free Docker web service `career-os` (serves API + exported frontend from one container) |
| Database | **Supabase Postgres** (via the Session pooler, IPv4). Set in Render env var `CAREEROS_DATABASE_URL`. |
| Health endpoint | `/api/v1/health` (must return 200) |
| Deploys | Render GitHub app installed 2026-11-19; auto-deploy runs after CI passes on `main`. Before that, every deploy was triggered by hand. |

**What changed recently (not yet reflected in the repo docs):**
- Render's free PostgreSQL expired and was **deleted with no backup** — all previous data (beta test data only) is gone.
- Production now points at a new Supabase project. Alembic migrations ran fresh on container startup and the app works again. The owner's beta account was recreated.
- Render cannot reach Supabase's direct connection (IPv6-only). The **Session pooler** URI (`postgres.<ref>@...pooler.supabase.com:5432`) must be used while hosted on Render. Do not switch it to the transaction pooler for the container.
- The Docker CMD runs `python -m app.cli.migrate` (an `alembic upgrade head` wrapper) before uvicorn, so a DB connection failure still takes the whole site down. Since PR #15 it starts anyway (with a warning) when the DB is at a revision the image doesn't know, after an ~18 min outage on 2026-11-18 where a restarted older image crash-looped. Keep migrations additive (expand now, drop columns in a later release).
- Planned: possibly move hosting to **Vercel** (frontend static + FastAPI as Python functions) with Supabase. Not started. Known work if we do it: (a) `backend/app/core/rate_limit.py` is an in-memory limiter assuming one process — must move to Postgres for serverless; (b) migrations must move out of container startup into a separate step (e.g. GitHub Action); (c) serverless should use Supabase's transaction pooler with psycopg prepared statements disabled; (d) roadmap generation (generate → critic → repair, 60s per AI call) may exceed function time limits — tune timeouts, rely on deterministic fallback; (e) Vercel Hobby is non-commercial use only. Cloudflare's free plan was ruled out for the backend (no free container runtime for this stack).

**Owner setup still to do** (domain, Resend, custom domain, Google, backups, AI provider): one checklist in `docs/LAUNCH_SETUP.md`, deliberately left until the end.

## 2. Tech stack
- Frontend: Expo / React Native / TypeScript, exported as a static web app (`pnpm`)
- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL (`uv`, `pytest`, `ruff`)
- AI: Groq via an OpenAI-compatible provider interface; model `openai/gpt-oss-120b`, fallback enabled

## 3. What CareerOS is
A topic-agnostic, mobile-first roadmap app: user goal → adaptive discovery → personalized roadmap → practical steps, evidence, progress, daily practice. Must support career, learning, business, creative, language and other goals — not only technical ones. Should feel polished and useful, not like a generic AI syllabus generator.

## 4. Product decisions (do not change without owner approval)
- Saved goals require sign-in. Do not restore guest data merging.
- Free users can create 2 goals total (not 2 active).
- Premium → Free downgrade keeps full access to Premium-created roadmaps. Never lock old work.
- No user-facing "regenerate roadmap" button.
- Every AI-spending action needs a clear reason, server-side limits, monitoring, graceful fallback, no surprise recurring use.
- Progress, evidence, resource feedback, daily practice must NOT trigger AI calls.
- Don't force roadmaps into a fixed shape.
- No public billing/subscriptions for now.
- Don't call CareerOS publicly launched until authentication is stable.

## 5. Roadmap intelligence
- AI personalizes, sequences, skips, emphasizes, and turns learning into proof work; it must not invent a whole curriculum blindly each time.
- Canonical curriculum backbones exist for: Python/backend engineering, Applied AI/automation, Data engineering. Broad role-level guardrails, not vendor- or user-specific (Applied AI must NOT be tailored to the owner's AWS/Databricks/PySpark/MLflow example).
- All other goals stay fully adaptive. Curriculum matching uses a confidence threshold ("Learn Python for data analysis" must not become the backend roadmap).
- Prerequisite graph validation must stay enforced.

## 6. AI pipeline & cost controls (implemented)
- generate → structural quality check → critic → one repair attempt → deterministic fallback.
- AI usage events recorded in the DB (operation, provider/model, tokens, timing, failures).
- Per-user and global quotas (DB-backed) for goal intent, discovery, roadmap generation; on exhaustion, fall back deterministically.
- Offline eval cases cover technical, nontechnical, language, business, creative, beginner, experienced, prompt-injection.
- Live eval requires `--confirm-live`, defaults to one case, is capped. Don't run it against production casually.

## 7. Authentication
- **Google OAuth: blocked.** Project `careeros-production-508315` is under a Terms of Service review; appeal pending. Do NOT create a new Google project/client to work around it. After resolution, add Authorized JavaScript Origin `https://career-os-41i5.onrender.com` (or the new host if we move).
- **Apple sign-in:** not active for web.
- **Temporary email beta sign-in (deployed):** `POST /api/v1/auth/email-test-sign-in`. NOT real email verification — never describe it as such. Exact-allowlisted email + temporary access code in env vars, rate limited, constant-time comparison. Enabled only when both `CAREEROS_EMAIL_TEST_LOGIN_EMAILS` and `CAREEROS_EMAIL_TEST_ACCESS_CODE` are set. Frontend shows "Email sign-in for beta testing" only when backend config reports `email_test: true`. The owner's beta email is also Premium via the scoped tester allowlist. Rotate/remove the code when testing ends. Don't expand into public email login.
- **Email-code sign-in (built, switched off):** `POST /api/v1/auth/email-code/request` then `/verify`. 6-digit code, hashed at rest, 10-minute expiry, single use, 5 wrong attempts lock it, a new request replaces the old code, 5 requests per email per 15 min. Same response whether or not the account exists. Signs in the account that already owns the email (so the beta account carries over). Works on web and native. To turn on in production: verify a domain in Resend, then set `CAREEROS_EMAIL_CODE_LOGIN_ENABLED=true`, `CAREEROS_EMAIL_SENDER=resend`, `CAREEROS_EMAIL_FROM="CareerOS <sign-in@your-domain>"`, `CAREEROS_RESEND_API_KEY`. The `log` sender is refused in production. Locally, compose enables it with codes in `docker compose logs api`. Retire the beta access code once it's live.

## 8. Environment (names/locations only)
| What | Where |
|---|---|
| Production env vars (`CAREEROS_DATABASE_URL`, Groq key, auth vars) | Render → `career-os` → Environment |
| Database | Supabase project (Session pooler connection) |
| Google OAuth client | Google Cloud project `careeros-production-508315` |
| Code | GitHub `pcochangco/career-os-v2` |

## 9. Known gaps / open issues
- ~~`.env.example` and `backend/.env.example` are missing `CAREEROS_EMAIL_TEST_LOGIN_EMAILS` and `CAREEROS_EMAIL_TEST_ACCESS_CODE`.~~ Fixed (2026-11-17), along with `CAREEROS_MANUAL_PREMIUM_EMAILS`.
- ~~Docs/README still describe Render PostgreSQL.~~ Fixed (2026-11-17): README, `docs/TECHNICAL.md` and `render.yaml` now describe Supabase + the Session pooler; the Blueprint no longer declares a Render database.
- No database backups exist. Not urgent while Supabase holds only test data; set up before real users (Supabase Pro daily backups, or a nightly `pg_dump` GitHub Action).
- The repo does not track a `uv.lock`; `uv sync` creates `backend/uv.lock` — don't commit it unless the owner decides to pin dependencies.
- Google sign-in unavailable; real email verification not implemented. The native app has no beta email sign-in form (web only).
- Groq free tier hits token-length limits and 429s, so production often serves the deterministic fallback roadmap.
- Leaving the public landing page remounts the signed-in shell, so Goals fetches its list once more after sign-in (extra request, no visible delay). Fix with the auth layout.
- Existing roadmaps keep stored titles like "Your path to …"; new fallback roadmaps say "Your roadmap to …".

## 10. Next steps (priority order)
1. ~~Repo hygiene~~ Done (PR #8).
2. Test the live core path with email beta sign-in (owner does the sign-in; agent helps review results).
3. Submit/track the Google Cloud appeal (owner; don't work around it).
4. Tag `v0.1-beta` once live testing passes.
5. Decide hosting (stay on Render web + Supabase, or move to Vercel) and plan the migration.
6. Domain + Resend → replace temporary access-code login with real email verification.
7. ~~UI/mobile polish~~ Done in the journey pass (section 12). Roadmap-quality work still waits on stable auth.

## 11. Working conventions
- Inspect relevant files and behavior before editing. Targeted changes; don't rewrite working architecture.
- Alembic migrations for any schema change. Preserve user data. Never run destructive DB or Git commands unless the owner explicitly asks.
- Work on a feature branch; don't push to `main` or open PRs unless asked.

Backend checks:
```bash
uv sync --project backend --extra dev
backend/.venv/bin/pytest backend/tests -q
backend/.venv/bin/ruff check backend/app backend/tests
```
Frontend checks:
```bash
pnpm install --frozen-lockfile
pnpm --dir frontend typecheck
pnpm frontend:export
```
Baseline at `54904aa`: 178 backend tests pass, Ruff clean, typecheck and web export pass (web bundle ~1.3 MB).

Deploy only after all checks pass. After a Render deploy, the owner verifies: deploy is live, `/api/v1/health` returns 200, no fresh errors in Render logs.

Communication: concise and practical — what changed, why, what was tested, what the owner should test next.

## 12. User-journey decisions (2026-11-18 production pass)
Owner-approved; don't change without asking.
- **Premium:** no fake upgrade button. Every plan limit says Premium can't be bought yet and offers "Ask about Premium" (mailto `EXPO_PUBLIC_SUPPORT_EMAIL`, a Docker build arg; hidden when unset).
- **Fallback roadmap copy** is built from the learner's discovery answers and must never echo model instructions. Short goal titles get "Reach this goal: …" framing to pass validation.
- **One roadmap generation in flight per goal**, enforced by a partial unique index; a second request gets 409 and the client polls. Abandoned attempts expire after 8 minutes.
- **Session expiry:** any 401 with a token signs out centrally and shows "Your session ended" on the sign-in screen.
- **Typed-but-unsaved text** (discovery answers, step notes, evidence link) is kept as a device draft; step work autosaves after 1.2s.
- **Evidence link** per step, validated as http(s).
- **Settings:** shows who is signed in and the plan; "Download my data" exports everything as JSON (no AI metadata); delete account is red and confirmed.
- **Analytics:** first-party `product_events` table, whitelisted enum/boolean properties only, never free text; deleted with the account. Funnel: `python -m app.cli.funnel --days 30` in the Render shell.
- **Vocabulary:** roadmap (not path/journey), milestone (not phase/stage), step (not mission), daily practice (not mini win/prompt). Taglines may say "path".
- **Accessibility floor:** lucide icons, not text glyphs; labels ≥12px; tap targets ≥44px; visible `:focus-visible` ring on web.
- **Loading:** skeletons in the screen's layout; cold-start hint after 5s. A returning user's account and goal list load in parallel and `/auth/config` is skipped when signed in.
- **Day-2 return:** with 2+ goals, Goals leads with "Pick up where you left off" (`GoalRead.current_step_title`, `last_activity_at`). With one goal, opening the app lands on its roadmap.
