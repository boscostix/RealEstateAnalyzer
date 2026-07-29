# RealEstateAnalyzer

`RealEstateAnalyzer` is the first milestone of an AI-assisted real estate investment analysis platform.

This repository currently contains the property listing ingestion and extraction service only. The service accepts a listing URL, validates it safely, detects the provider, fetches the listing page with SSRF protections, falls back to Playwright when static HTML is insufficient, and extracts normalized structured property data for supported providers.

## Current milestone

This codebase currently implements:

- FastAPI extraction API
- Provider adapter architecture
- URL validation and SSRF protections
- Static HTTP page fetching with redirect, timeout, and size limits
- Playwright fallback for JavaScript-rendered pages
- Blocked-page and CAPTCHA detection
- Request ID middleware and structured application logging
- Zillow adapter
- Realtor.com adapter
- Redfin adapter
- Fixture-based parsing tests
- API integration tests
- Dockerfile and docker-compose setup

Not implemented yet:

- Financial analysis
- Authentication
- Frontend UI
- Database persistence
- AI agent orchestration
- Deployment beyond local Docker support

## Project structure

```text
app/
├── api/                # FastAPI routes and dependency wiring
├── models/             # Pydantic request, response, and domain models
├── providers/          # Zillow / Realtor / Redfin adapters
├── services/           # Fetching, fallback, registry, orchestration
├── utils/              # URL and parsing helpers
└── logging.py          # Request-id middleware and logging setup

tests/
├── fixtures/           # Sanitized provider HTML samples
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

Install the Playwright browser used by the fallback fetcher:

```bash
uv run playwright install chromium
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

## API usage

Endpoint:

```text
POST /api/v1/listings/extract
```

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/example"}'
```

Example success shape:

```json
{
  "success": true,
  "provider": "zillow",
  "source_url": "https://www.zillow.com/homedetails/example",
  "property": {
    "source_url": "https://www.zillow.com/homedetails/example",
    "provider": "zillow",
    "address": {
      "street": "8400 Silverado Trl",
      "city": "McKinney",
      "state": "TX",
      "postal_code": "75070",
      "full_address": "8400 Silverado Trl, McKinney, TX 75070"
    }
  },
  "metadata": {
    "extraction_method": "next_data",
    "fields_found": 21,
    "fields_missing": [],
    "warnings": []
  }
}
```

Example error shape:

```json
{
  "success": false,
  "error": {
    "code": "access_blocked",
    "message": "The listing website blocked automated access.",
    "retryable": false
  }
}
```

## Supported providers

- Zillow
- Realtor.com
- Redfin

## Architecture

- `ProviderRegistry` selects the adapter based on the incoming listing URL.
- `ListingService` coordinates provider selection, static HTTP fetch, Playwright fallback, parsing, and response shaping.
- `PageFetcher` handles SSRF protections, redirects, size limits, and blocked-page detection.
- `PlaywrightPageFetcher` is used only when static content is insufficient or provider parsing still lacks enough core fields.
- Provider adapters prefer structured data first:
  - JSON-LD
  - Embedded application JSON
  - Provider-specific page state
  - HTML metadata
  - Visible HTML fallback

## Logging

The API logs:

- Request ID
- Provider
- Domain
- Fetch method
- Fetch duration
- Parsing duration
- Number of fields found
- Warning count
- Error code

Full page HTML, cookies, and sensitive headers are not logged.

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Testing

- Unit and integration tests do not make live requests to listing sites.
- Provider parsing is validated against stored HTML fixtures.
- API tests exercise the route, service layer, fallback path, and structured error handling.

## Current limitations

- Provider parsing is tested against stored HTML fixtures rather than live site requests.
- Fixture coverage currently includes one successful sample per provider plus partial-data scenarios.
- Provider schemas will need continued maintenance as listing sites evolve.
- This milestone does not persist listings or perform downstream investment analysis.

## How to add another provider

1. Add a new provider adapter under `app/providers/`.
2. Implement `can_handle()` and `extract()` against the shared `ListingProvider` interface.
3. Register the provider in `ProviderRegistry.default()`.
4. Add sanitized fixture HTML under `tests/fixtures/`.
5. Add provider parsing tests and, when useful, API integration coverage.
