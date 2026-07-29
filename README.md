# RealEstateAnalyzer

`RealEstateAnalyzer` is the first milestone of an AI-assisted real estate investment analysis platform.

This repository currently contains the property listing ingestion and extraction service only. The service accepts a listing URL, validates it safely, detects the provider, fetches the listing page with SSRF protections, and extracts normalized structured property data for supported providers.

## Current milestone

This codebase currently implements:

- FastAPI application scaffold
- Provider adapter architecture
- URL validation and SSRF protections
- Static HTTP page fetching with redirect, timeout, and size limits
- Blocked-page and CAPTCHA detection
- Zillow adapter
- Realtor.com adapter
- Redfin adapter
- Fixture-based parsing tests

Not implemented yet:

- Financial analysis
- Authentication
- Frontend UI
- Database persistence
- AI agent orchestration
- Playwright fallback wiring into the endpoint
- Docker and compose setup

## Project structure

```text
app/
├── api/
├── models/
├── providers/
├── services/
└── utils/

tests/
├── fixtures/
└── ...
```

## Requirements

- Python 3.12
- `uv`

## Local setup

Install dependencies:

```bash
uv sync --dev
```

Run the API locally:

```bash
uv run uvicorn app.main:app --reload
```

The app will start on `http://127.0.0.1:8000`.

## Useful commands

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check .
```

Run mypy:

```bash
uv run mypy app
```

## Supported providers

- Zillow
- Realtor.com
- Redfin

## Notes

- Provider parsing is tested against stored HTML fixtures rather than live site requests.
- Structured data is preferred before any visible HTML fallback.
- The API surface is in progress and will expand in Phase 4.
