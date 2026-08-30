FROM node:22.13-alpine AS frontend-build

WORKDIR /workspace

RUN corepack enable && corepack prepare pnpm@11.19.0 --activate

COPY package.json pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/package.json
RUN pnpm install --no-frozen-lockfile

COPY frontend ./frontend
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

CMD ["sh", "-c", "python -m alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
