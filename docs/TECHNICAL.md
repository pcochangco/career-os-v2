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

### Resource

Canonical retrieved resource metadata and verification status.

### RoadmapStepResource

Ordered relationship between a verified resource and a roadmap step.

### StepProgress

User-owned completion state for a step. Completion is explicit and timestamped.

### StepNote and StepEvidence

Private notes and user-selected proof such as links or stored artifacts.

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
- `/api/v1/roadmap-steps/{step_id}/progress`
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

The backend selects either a deterministic fixture provider or an OpenAI
provider through environment configuration. Both return schema `1.0` objects
through the same typed interface. Provider text is never persisted directly:
Pydantic rejects unexpected structure, deterministic checks enforce domain
invariants, and an independent critic can trigger one bounded repair attempt.

Roadmap versions retain the exact normalized generation input, assumptions,
provider and model identifiers, prompt version, response identifiers, quality
report, token totals, and generation duration. Explicit step dependencies are
stored as relationships in addition to the ordered path. Resource queries are
stored for the upcoming retrieval slice; model-generated URLs are rejected.

## Scaling path

The MVP uses one API deployment and one PostgreSQL database. Prepare for growth
through stateless API instances, indexed ownership queries, pagination, bounded
AI requests, idempotent generation commands, and observable provider usage.

Add a queue and generation worker only when request duration, retries, or mobile
background behavior requires it. Add caches, read replicas, or service splits
only in response to measured bottlenecks.

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

### Sprint 1 identity boundary

The first vertical slice creates an anonymous bearer session automatically. The
raw opaque token is returned once, stored by the web client, and only its SHA-256
digest is persisted. Every goal and roadmap query is scoped to the session's
user. This removes sign-up friction without weakening server-side ownership.

Before public beta, anonymous users can upgrade to a verified account without
changing ownership IDs. Native persistent secure-token storage and session
revocation UI are added with the mobile release boundary.

## Implemented vertical slice

The first implemented slice is deliberately narrow:

1. Create an authenticated goal.
2. Complete adaptive discovery.
3. Generate a structured, quality-checked roadmap through a replaceable provider.
4. Review and accept it.
5. Open the accepted roadmap in a mobile-first vertical path.

The live provider boundary is implemented but opt-in; deterministic generation
remains the default for local development and CI. Progress, evidence, showcases,
resource verification, and notifications follow in later vertical slices.

This slice is implemented through the `/api/v1/auth`, `/api/v1/goals`, and
`/api/v1/roadmaps` resource families. Both providers use the same persistence and
response contracts.
