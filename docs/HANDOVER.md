# CareerOS handover brief

_Originally written 2026-11-16 as the onboarding brief for a new working session. Section 9 is updated as gaps are closed._

You are taking over CareerOS, an ongoing production project — not a fresh build. Read this whole brief, then inspect the repository before doing anything. Do not start coding until I give you a task; first confirm the repo state and run the baseline checks (section 11), then report back briefly.

Never print, commit, or ask me to paste API keys, database URLs, access codes, or OAuth secrets. This brief lists variable NAMES only. If you need a credential, tell me where to set it — don't ask for its value in chat.

GitHub is the truth for current code. This brief is the truth for intent and decisions.

---

## 1. Repository & deployment (current state, 2026-11-16)

| Item | Value |
|---|---|
| GitHub repo | `pcochangco/career-os-v2`, branch `main` |
| Latest commit | `d968238` — `feat(auth): add scoped email test sign-in` |
| Production URL | https://career-os-41i5.onrender.com |
| Web host | Render free Docker web service `career-os` (serves API + exported frontend from one container) |
| Database | **Supabase Postgres** (via the Session pooler, IPv4). Set in Render env var `CAREEROS_DATABASE_URL`. |
| Health endpoint | `/api/v1/health` (must return 200) |

**What changed recently (not yet reflected in the repo docs):**
- Render's free PostgreSQL expired and was **deleted with no backup** — all previous data (beta test data only) is gone.
- Production now points at a new Supabase project. Alembic migrations ran fresh on container startup and the app works again. The owner's beta account was recreated.
- Render cannot reach Supabase's direct connection (IPv6-only). The **Session pooler** URI (`postgres.<ref>@...pooler.supabase.com:5432`) must be used while hosted on Render. Do not switch it to the transaction pooler for the container.
- The Docker CMD runs `alembic upgrade head` before uvicorn, so any DB connection failure takes the whole site (frontend included) down.
- Planned: possibly move hosting to **Vercel** (frontend static + FastAPI as Python functions) with Supabase. Not started. Known work if we do it: (a) `backend/app/core/rate_limit.py` is an in-memory limiter assuming one process — must move to Postgres for serverless; (b) migrations must move out of container startup into a separate step (e.g. GitHub Action); (c) serverless should use Supabase's transaction pooler with psycopg prepared statements disabled; (d) roadmap generation (generate → critic → repair, 60s per AI call) may exceed function time limits — tune timeouts, rely on deterministic fallback; (e) Vercel Hobby is non-commercial use only. Cloudflare's free plan was ruled out for the backend (no free container runtime for this stack).

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
- **Planned replacement:** passwordless email verification via a real sender (e.g. Resend) with a verified CareerOS domain, using expiring single-use codes or magic links.

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
- No database backups exist. Recommend enabling/understanding Supabase backups or a scheduled `pg_dump` so the data-loss incident can't repeat.
- The repo does not track a `uv.lock`; `uv sync` creates `backend/uv.lock` — don't commit it unless the owner decides to pin dependencies.
- Google sign-in unavailable; real email verification not implemented.

## 10. Next steps (priority order)
1. Repo hygiene: fix `.env.example` gaps and update docs for Supabase; commit this brief as `docs/HANDOVER.md`.
2. Test the live core path with email beta sign-in (owner does the sign-in; agent helps review results).
3. Submit/track the Google Cloud appeal (owner; don't work around it).
4. Tag `v0.1-beta` once live testing passes.
5. Decide hosting (stay on Render web + Supabase, or move to Vercel) and plan the migration.
6. Domain + Resend → replace temporary access-code login with real email verification.
7. Only after auth is stable: UI/mobile polish and roadmap-quality work.

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
Baseline at `d968238`: 125 backend tests pass, Ruff clean, typecheck and web export pass.

Deploy only after all checks pass. After a Render deploy, the owner verifies: deploy is live, `/api/v1/health` returns 200, no fresh errors in Render logs.

Communication: concise and practical — what changed, why, what was tested, what the owner should test next.
