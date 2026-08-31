# CareerOS

CareerOS turns a personal goal into a realistic, personalized roadmap, keeps the
user oriented on the next meaningful step, and builds shareable proof of what
they learned and produced.

The product is intentionally not a daily planner. It does not require schedules,
time commitments, carry-over maintenance, or productivity configuration.

## Core loop

1. Create or select a goal.
2. See the roadmap and current position.
3. Open the current step.
4. Learn, practice, or produce evidence.
5. Complete the step and continue when ready.
6. Build a shareable goal showcase over time.

## Canonical documentation

- [Product](docs/PRODUCT.md)
- [UX](docs/UX.md)
- [AI roadmap specification](docs/AI_ROADMAP_SPEC.md)
- [Technical architecture](docs/TECHNICAL.md)

These four documents are the product source of truth. New features must support
the core loop and must be added to the relevant canonical document before
implementation.

## Planned implementation

- Universal Expo frontend for web, Android, and iOS
- FastAPI modular-monolith backend
- PostgreSQL persistence
- Provider-independent AI roadmap generation

The first release target is the web experience from the universal frontend.
Android and iOS use the same backend, domain contracts, and navigation model.

## Current vertical slice

The implemented product slice covers the complete first-run path:

1. Start an anonymous authenticated session.
2. Create a user-owned goal.
3. Answer five focused discovery questions, one at a time.
4. Generate, quality-check, and review a structured roadmap.
5. Accept the roadmap and open it as a mobile-first vertical path.
6. Complete the current step and advance to the next unblocked step.
7. Return later to the same position with truthful goal progress.
8. Save private notes, an output summary, and an optional evidence link.
9. Confirm the concrete completion condition before progress is recorded.
10. Open verified, cached learning-resource cards for the current step.

Generation runs behind a provider-independent boundary. The default deterministic
provider keeps local development and CI reliable. The opt-in OpenAI-compatible
provider uses the same strict schema, a separate critic pass, deterministic
structural checks, and one bounded repair attempt. Production `live` mode requires
the configured provider to succeed and returns an explicit service error when it does
not; it never presents a deterministic fixture as a live AI result. Only roadmaps
that pass the quality contract are persisted. Models produce resource search queries
but never final URLs. The
resource resolver uses those queries to retrieve topic-specific Wikipedia
articles and selected learning videos through provider APIs, accepts only safe
HTTPS hosts with complete metadata, and caches the verified snapshot per step.

The production container serves the exported Expo web application and FastAPI
from the same origin. This keeps the browser flow simple while preserving the
same `/api/v1` contracts for future native clients.

## Local development

Requirements:

- Node.js 22.13 or newer
- pnpm 11
- Python 3.12
- Docker with Compose for PostgreSQL and the containerized API

Install the client:

```bash
pnpm install
```

Install the backend in a virtual environment:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Start PostgreSQL and the API:

```bash
docker compose up --build
```

The default `fixture` mode requires no API credentials. To exercise live
generation, copy `.env.example` to `.env`, set `CAREEROS_AI_MODE=live`, and set
`CAREEROS_AI_API_KEY` locally. Never commit the key. OpenAI-compatible providers
are selected entirely through `CAREEROS_AI_PROVIDER`, `CAREEROS_AI_BASE_URL`,
`CAREEROS_AI_MODEL`, `CAREEROS_AI_RESPONSE_FORMAT`,
`CAREEROS_AI_MAX_COMPLETION_TOKENS`, and the optional `CAREEROS_AI_REASONING_EFFORT`;
changing between compatible providers does not require application code changes. Use
`json_schema` when the provider reliably supports strict structured outputs, or
`json_object` with the same local Pydantic validation and quality gates for providers
with narrower schema support.

For example, Groq's free developer tier can be configured with:

```dotenv
CAREEROS_AI_MODE=live
CAREEROS_AI_PROVIDER=groq
CAREEROS_AI_BASE_URL=https://api.groq.com/openai/v1
CAREEROS_AI_MODEL=openai/gpt-oss-120b
CAREEROS_AI_RESPONSE_FORMAT=json_object
CAREEROS_AI_REASONING_EFFORT=
CAREEROS_AI_MAX_COMPLETION_TOKENS=8192
CAREEROS_AI_API_KEY=
```

After configuring a local key, compare the live model with the deterministic
baseline without printing roadmap text or prompts:

```bash
cd backend
python evals/run_live.py --limit 2
```

Start the universal client in a separate terminal:

```bash
pnpm frontend:web
```

Run all available foundation checks:

```bash
./scripts/check.sh
```

The backend health endpoint is `GET /api/v1/health`, and local API documentation
is available at `/api/docs`. Representative roadmap evaluations live in
`backend/evals/cases.json` and run as part of the backend test suite without
network access.

## Deployment

`render.yaml` defines the MVP deployment as one Docker web service and one
managed PostgreSQL database in Render's Singapore region. The web service:

- Builds the universal Expo web export and FastAPI into one image.
- Applies Alembic migrations before starting each release.
- Uses `/api/v1/health` for deployment health checks.
- Deploys from `main` only after GitHub CI passes.
- Limits each user to three roadmap generations per hour.
- Caps total public generation attempts across anonymous sessions.
- Reports whether live AI or the deterministic preview is active through health metadata.

Create the Blueprint from this repository to receive an `onrender.com` URL. The
checked-in production configuration uses `live` mode with Groq's OpenAI-compatible
endpoint. Add `CAREEROS_AI_API_KEY` as a secret directly in Render before deploying;
without it, the health endpoint reports a misconfiguration and roadmap generation is
unavailable. Never place the key in this repository, source-controlled Blueprint
values, or application requests.

The free Render database is suitable only for an MVP preview and expires after
30 days. Upgrade the database before storing data that must persist long-term.
