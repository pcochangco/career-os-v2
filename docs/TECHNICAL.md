# CareerOS Technical Architecture

## Architecture principles

- Begin as a modular monolith.
- Keep the frontend universal across web, Android, and iOS.
- Keep domain behavior behind typed backend APIs.
- Treat AI and retrieved content as untrusted input.
- Preserve user ownership at every data boundary.
- Add infrastructure only when measured demand requires it.

## Initial stack

### Client

- Expo and React Native
- Expo Router
- TypeScript
- TanStack Query for server state
- Generated API types from OpenAPI

The first release target is web. Android and iOS use the same route structure,
backend contracts, and shared components, with platform-specific behavior only
where necessary.

### Backend

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- PostgreSQL

The backend is a stateless API process organized by domain module. A separate
worker or queue is deferred until roadmap generation latency or reliability
demonstrates the need.

## Initial domain modules

- `auth` — identity and authenticated ownership
- `users` — profile and preferences
- `goals` — goal lifecycle and discovery state
- `roadmaps` — versions, milestones, steps, prerequisites, and acceptance
- `resources` — retrieved and verified resource metadata
- `progress` — completion, notes, and evidence
- `showcases` — private composition and public sharing
- `ai` — provider-independent generation and validation boundary

There is no Today, daily-plan, calendar, availability, or rebalance module.

## Minimum persistence model

### User

Identity and profile settings.

### Goal

User-owned intent, desired outcome, discovery status, and lifecycle.

### GoalDiscoveryAnswer

Versioned answers and explicit assumptions used to generate a roadmap.

### RoadmapVersion

Immutable generated draft or accepted roadmap snapshot with schema, prompt,
model, and generation provenance.

### RoadmapMilestone

Ordered milestone within a roadmap version.

### RoadmapStep

Ordered learn, practice, or prove step with objective and completion condition.

### RoadmapStepDependency

Explicit dependency between steps in the same roadmap version.

### RoadmapStepResource

Verified resource metadata snapshot attached to one exact roadmap step. The
snapshot records provider, type, source, URL, relevance context, and verification
time so reopening the step does not repeat retrieval or silently change links.

### RoadmapStepProgress

User-owned completion state for a step. Completion is explicit and timestamped.

### RoadmapStepWork

Private notes, an output summary, and an optional validated web link attached to
one user and one exact roadmap step. This record is independent of completion so
work can be saved before completion and preserved if the step is reopened.

### GoalShowcase

User-controlled presentation assembled from selected progress and evidence. It
is private by default and has an optional revocable public identifier.

## Important invariants

- Every user-owned row is access-controlled through the authenticated user.
- A goal has at most one active accepted roadmap version.
- Roadmap versions are preserved rather than overwritten.
- Milestones, steps, and dependencies cannot cross roadmap versions.
- Completed progress remains attached to the exact accepted step version.
- Progress comes only from explicit completed steps.
- Private notes and evidence never enter a public showcase by default.
- Public identifiers are unguessable and revocable.
- Provider output cannot be persisted as accepted domain data until validated.

## API shape

Initial resource families:

- `/api/v1/auth`
- `/api/v1/goals`
- `/api/v1/goals/{goal_id}/discovery`
- `/api/v1/goals/{goal_id}/roadmaps`
- `/api/v1/roadmaps/{roadmap_id}`
- `/api/v1/roadmap-steps/{step_id}`
- `/api/v1/roadmap-steps/{step_id}/work`
- `/api/v1/roadmap-steps/{step_id}/progress`
- `/api/v1/roadmap-steps/{step_id}/resources/resolve`
- `/api/v1/goals/{goal_id}/showcase`
- `/public/showcases/{public_id}`

Exact endpoints are introduced only with the vertical slice that consumes them.

## Roadmap generation boundary

The application-level generation service coordinates:

1. Authorized goal and discovery input
2. Provider-independent structured generation
3. Resource retrieval and verification
4. Quality critique and bounded repair
5. Schema and domain validation
6. Draft roadmap persistence

Live providers are replaceable. Automated tests use deterministic fixtures.

### Implemented AI boundary

The backend selects either a deterministic fixture provider or a configurable
OpenAI-compatible provider. Provider identity, base URL, model, response-format
capability, optional reasoning effort, and key are independent environment settings.
Strict JSON Schema and JSON Object modes both return schema `1.0` objects through
the same typed interface. Provider text is never persisted directly: Pydantic rejects
unexpected structure, deterministic checks enforce domain invariants, and an
independent critic can trigger one bounded repair attempt.

Roadmap versions retain the exact normalized generation input, assumptions,
provider and model identifiers, prompt version, response identifiers, quality
report, token totals, and generation duration. Explicit step dependencies are
stored as relationships in addition to the ordered path. Resource queries are
stored with each step; model-generated URLs are rejected.

The app builds roadmaps in the background: `POST /goals/{id}/roadmaps/generation` claims the
goal's single in-flight slot and the usage quota, returns `202` at once, and runs generation
after the response with its own database session. `GET /goals/{id}/roadmaps/generation`
returns `idle`, `running` (with `stage`, `done`, `total`, e.g. "Writing milestone 3 of 7"),
`ready` (with the roadmap id and whether it's a draft or accepted), or `failed`. The waiting
screen polls it every 2.5 seconds, so closing the tab or losing signal doesn't waste the run.
Progress is stored on the generation attempt (migration `20261121_0020`). The older
synchronous `POST /goals/{id}/roadmaps` still works and shares the same code.

Live roadmaps are generated in stages by default (`CAREEROS_AI_GENERATION_STRATEGY=staged`)
so no single answer hits a free-tier output cap: an outline call lists every milestone and
step (key, kind, title, one-line objective), which is checked and reviewed and repaired once
if needed; then one call per milestone writes that milestone's full step details
(`CAREEROS_AI_EXPAND_MAX_COMPLETION_TOKENS`, default 2500), alternating between the main and
repair models because each has its own tokens-per-minute budget. Step-level problems found
in the assembled roadmap regenerate only their milestone. All calls share
`CAREEROS_AI_GENERATION_TIME_BUDGET_SECONDS` (default 240); within it, rate limits (429) are
waited out using the provider's `retry-after`. Running out of budget falls back to the
deterministic roadmap. `single` keeps the one-call path for models with large output limits.
Try a strategy with real calls: `uv run python evals/run_live.py --limit 1 --confirm-live
[--strategy staged|single]` (needs `CAREEROS_AI_API_KEY` in your local `.env`).

The roadmap prompt's design guidance is a skill folder:
`backend/app/ai/skills/<name>/SKILL.md` (a `---` header with `name` and
`description`, then plain instructions) plus optional `references/*.md`. The app
contract (untrusted input, no URLs, no schedules, effort labels, step keys) stays in
code and wraps the skill, so a swapped skill cannot drop it. To try another skill,
add its folder in a PR and set `CAREEROS_ROADMAP_SKILL=<name>`; a missing or
malformed skill fails at startup. Each roadmap's `prompt_version` records the skill
name and a content hash (for example `roadmap-schema-1.0-compatible-11+roadmap-mentor@1a2b3c4d`).
Skills load only from the repository, never from a URL.

Production `auto` mode activates the configured provider only when the generic
backend secret is present. A provider or quality failure switches the entire request
to the deterministic quality-checked provider; partial live-provider drafts are
never mixed with the fallback. Health metadata exposes the active mode, provider,
and model without exposing the secret or endpoint credentials.

### Implemented resource boundary

The current accepted step resolves its stored queries through replaceable
providers. Wikipedia's read-only Action API supplies topic-specific articles,
and a curated provider verifies selected learning videos through YouTube oEmbed.
The resolver permits only known HTTPS content hosts, rejects incomplete or
duplicate metadata, caps results, and stores the accepted snapshot. Locked or
upcoming steps cannot retrieve resources early. Automated tests replace outbound
providers with deterministic fixtures and never require public network access.

## Scaling path

The MVP uses one API deployment and one PostgreSQL database. Prepare for growth
through stateless API instances, indexed ownership queries, pagination, bounded
AI requests, idempotent generation commands, and observable provider usage.

Add a queue and generation worker only when request duration, retries, or mobile
background behavior requires it. Add caches, read replicas, or service splits
only in response to measured bottlenecks.

## MVP deployment

The web MVP is packaged as one multi-stage Docker image. The build stage exports
the Expo frontend; the runtime stage serves those files and `/api/v1` from the
same FastAPI process. Unknown browser routes fall back to the application shell,
while unknown API routes retain proper `404` responses. Native applications
continue to call the same API through a configured absolute URL.

The Render Blueprint provisions a Singapore web service that runs migrations
before application startup, checks `/api/v1/health`, and deploys only after
GitHub checks pass. The database is Supabase Postgres, reached through the
Session pooler (IPv4) because Render cannot reach Supabase's IPv6-only direct
connection. The transaction pooler is not used for the container. Migrations run
in the container command through `python -m app.cli.migrate` (an `alembic
upgrade head` wrapper), so a database connection failure takes the whole site
offline. If the database is already at a revision the image doesn't know (a
newer deploy migrated, then Render restarted an older image), the wrapper logs
a warning and starts anyway instead of crash-looping; this relies on
migrations staying additive (expand first, remove columns in a later release). The original free Render database
expired and was deleted without a backup; Supabase backups (or a scheduled
`pg_dump`) must be configured before data needs to persist.

Public AI safeguards use a durable attempt ledger with both per-user and global
hourly ceilings. Attempts are counted before the provider call, including failed
requests and new anonymous sessions. The preview remains deterministic until the
configured provider key is stored as a backend secret; `auto` mode then enables live
generation with deterministic failover. Before a wider beta, add usage budgets,
request tracing, and asynchronous generation if measured latency requires it.

## Security baseline

- Validate authentication and ownership server-side.
- Encrypt transport and secrets.
- Keep provider keys on the backend.
- Validate uploaded file type and size.
- Sanitize public showcase content.
- Apply rate and cost limits to generation endpoints.
- Treat retrieved pages as data, never trusted instructions.
- Do not send private notes or evidence to an AI provider without an explicit
  feature need and clear user understanding.

### Required-account identity boundary

The public start screen creates no user and persists no goal. A visitor may type a
goal in component memory, but CareerOS sends it to the API only after verified Apple
or Google sign-in. Direct provider sign-in creates or opens the provider identity's
saved user and issues a random opaque CareerOS bearer token. Only the token's SHA-256
digest is persisted, and every goal and roadmap query is scoped to that user.

Returning sign-in opens only the identity's saved account. CareerOS never merges
browser-local or anonymous data into an existing saved account. The anonymous session
endpoint remains available only for local development and automated tests behind
`CAREEROS_ALLOW_GUEST_ACCESS`; production sets the flag to `false`.

The backend validates provider ID-token signatures, issuer, audience, expiry, and
subject against configured client IDs. Provider tokens are never stored. Identity
provider linking and logout rotate or revoke the opaque CareerOS session, and account deletion
cascades through user-owned data. Provider client IDs remain environment configuration;
the public UI shows an explicit setup state until the relevant provider is configured.

Native iOS and Android builds use EAS profiles in `frontend/eas.json`. The iOS
client enables the Apple capability through Expo's Apple Authentication plugin.
Google sign-in uses Android Credential Manager and the native Google iOS SDK
through the Nitro Google Sign-In config plugin. Both clients send only the
provider-issued ID token to `/api/v1/auth/sign-in/{provider}`. Saved users can attach
a second provider through `/api/v1/auth/link/{provider}`.
The production API URL and the Google iOS client ID are supplied to EAS at build
time; OAuth client IDs are public identifiers, while provider secrets are neither
required nor accepted by the app.

## Implemented vertical slices

The first implemented slice is deliberately narrow:

1. Create an authenticated goal.
2. Complete adaptive discovery.
3. Generate a structured, quality-checked roadmap through a replaceable provider.
4. Review and accept it.
5. Open the accepted roadmap in a mobile-first vertical path.
6. Record explicit step completion.
7. Enforce prerequisites and advance to the next unblocked step.
8. Derive roadmap and goal progress from completed accepted-roadmap steps.
9. Save one private learning record independently of completion.
10. Require explicit confirmation of the step's completion condition.
11. Retrieve, verify, cache, and display resources for only the current step.
12. Store authenticated beta issue reports with a user-facing reference and no report text in application logs.

The live provider boundary is implemented but opt-in; deterministic generation
remains the default for local development and CI. Showcases and notifications
follow in later vertical slices.

These slices are implemented through the `/api/v1/auth`, `/api/v1/goals`,
`/api/v1/roadmaps`, `/api/v1/roadmap-steps/{step_id}/work`,
`/api/v1/roadmap-steps/{step_id}/progress`, and
`/api/v1/roadmap-steps/{step_id}/resources/resolve` resource families. Both
roadmap providers use the same persistence and response contracts.

## Product funnel analytics

CareerOS measures its core journey with first-party, privacy-safe events in the
`product_events` table. There is no client tracking script, no cookies and no third party.
Events are written on the server inside the same transaction as the action they describe.

| Event | When | Properties |
|---|---|---|
| `signup_completed` | A new account is created at sign-in | `method`: apple/google/email |
| `goal_created` | A goal is saved | `first`: bool |
| `goal_limit_reached` | A Free account tries to exceed its goal limit | none |
| `discovery_completed` | Discovery is ready for generation | `all_skipped`: bool |
| `roadmap_generated` | A draft roadmap is saved | `source`: succeeded/fallback/quota_fallback/preview |
| `roadmap_accepted` | A draft is accepted | none |
| `step_completed` | A step is completed | `first_ever`: bool |
| `practice_logged` | Daily practice is logged | none |
| `active_day` | The app loads the account (at most once per user per UTC day) | none |

Rules: only the names and values above are accepted (`app/services/analytics.py` drops
anything else); never store goal titles, answers, notes, emails or other free text; rows
cascade-delete with the account.

Read the funnel (distinct people, by sign-up window) from the API container:

```bash
python -m app.cli.funnel --days 30
```
