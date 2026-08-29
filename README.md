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

Generation runs behind a provider-independent boundary. The default deterministic
provider keeps local development and CI reliable. The opt-in OpenAI provider uses
the same strict schema, a separate critic pass, deterministic structural checks,
and one bounded repair attempt. Only roadmaps that pass the quality contract are
persisted. Resource retrieval and verification are the next core slice; models
produce search queries but never final resource URLs.

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

The default `fixture` provider requires no API credentials. To exercise live
generation, copy `.env.example` to `.env`, set `CAREEROS_AI_PROVIDER=openai`, and
set `CAREEROS_OPENAI_API_KEY` locally. Never commit the key. The configured model
defaults to `gpt-5.6-terra` and can be changed with `CAREEROS_AI_MODEL`.

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
