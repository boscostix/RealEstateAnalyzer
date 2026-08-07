#!/usr/bin/env sh
set -eu

mkdir -p /app/data
uv run alembic upgrade head
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
