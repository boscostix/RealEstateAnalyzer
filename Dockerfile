FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY docker/start-api.sh ./docker/start-api.sh
COPY .env.example ./.env.example

RUN uv run playwright install --with-deps chromium
RUN chmod +x /app/docker/start-api.sh

EXPOSE 8000

CMD ["/app/docker/start-api.sh"]
