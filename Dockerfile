FROM node:22.13-alpine AS frontend-build

WORKDIR /workspace

RUN npm install --global pnpm@11.19.0

COPY package.json pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN pnpm install --no-frozen-lockfile

COPY frontend ./frontend
# EXPO_PUBLIC_* values are inlined into the static web bundle at build time. Render passes
# service environment variables to Docker builds as build arguments, so declare them here.
ARG EXPO_PUBLIC_SUPPORT_EMAIL=""
ENV EXPO_PUBLIC_SUPPORT_EMAIL=${EXPO_PUBLIC_SUPPORT_EMAIL}
RUN pnpm frontend:export


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CAREEROS_STATIC_DIRECTORY=/app/static

WORKDIR /app

RUN addgroup --system careeros && adduser --system --ingroup careeros careeros

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY --from=frontend-build /workspace/frontend/dist ./static

RUN pip install --no-cache-dir .

USER careeros

EXPOSE 8000

# Migrations run at start. app.cli.migrate skips (with a warning) when the database is already
# ahead of this build, so a restarted older image can still boot after a newer deploy migrated.
CMD ["sh", "-c", "python -m app.cli.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
