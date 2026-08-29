#!/usr/bin/env sh
set -eu

(cd backend && python -m pytest -q)
(cd backend && python -m ruff check .)
pnpm frontend:typecheck
pnpm frontend:export
