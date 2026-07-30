# RealEstateAnalyzer

`RealEstateAnalyzer` is an early milestone of an AI-assisted real estate investment analysis platform.

This repository currently contains:

- A property listing ingestion and extraction service
- A property verification layer for reviewing extracted fields
- A deterministic underwriting engine for running investment analysis without AI/LLM calls

## Current milestone

This codebase currently implements:

- FastAPI extraction API
- FastAPI verification and analysis APIs
- Provider adapter architecture
- URL validation and SSRF protections
- Static HTTP page fetching with redirect, timeout, and size limits
- Playwright fallback for JavaScript-rendered pages
- Blocked-page and CAPTCHA detection
- Request ID middleware and structured application logging
- Zillow adapter
- Optional HasData-backed Zillow API integration
- Optional HasData-backed Redfin API integration
- Redfin adapter
- Verified property snapshot modeling
- Deterministic underwriting assumptions and outputs
- Scenario analysis
- Stress testing
- Maximum-offer calculations
- Fixture-based parsing tests
- API integration tests
- Dockerfile and docker-compose setup

Not implemented yet:

- Authentication
- Frontend UI
- Database persistence
- AI agent orchestration
- Deployment beyond local Docker support

## Project structure

```text
app/
├── api/                # FastAPI routes and dependency wiring
├── calculations/       # Deterministic underwriting math modules
├── models/             # Pydantic request, response, and domain models
├── presets/            # Named underwriting assumption presets
├── providers/          # Zillow / Redfin adapters
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

If you have a HasData key for Zillow and Redfin property lookups, you can either export it:

```bash
export HASDATA_API_KEY=your_key_here
```

or place it in the local file the app reads by default:

```text
secrets/hasdata_api_key.txt
```

That file should contain only the raw key value on one line.

Install the Playwright browser used by the fallback fetcher:

```bash
uv run playwright install chromium
```

Run the API locally:

```bash
uv run uvicorn app.main:app --reload
```

The app will start on `http://127.0.0.1:8000`.

Interactive docs are available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

If you change the HasData key file or update provider code, restart `uvicorn` so the running app picks up the latest configuration.

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

Extraction endpoint:

```text
POST /api/v1/listings/extract
```

Verification endpoint:

```text
POST /api/v1/properties/verify
```

Analysis endpoint:

```text
POST /api/v1/analyses/run
```

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/example"}'
```

Example Zillow request using the HasData-backed path:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/"}'
```

Example Redfin request using the same HasData-backed key:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.redfin.com/TX/Frisco/11809-Woodland-Way-75035/home/32250941"}'
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

## Verification and underwriting flow

The current Milestone 2 flow is:

1. Extract a property from a supported listing URL with `POST /api/v1/listings/extract`.
2. Send that extraction result to `POST /api/v1/properties/verify`.
3. Optionally provide field corrections and confirmed fields.
4. Send the verified property snapshot plus underwriting assumptions to `POST /api/v1/analyses/run`.

The underwriting engine is fully deterministic. It does not use AI models, live comparable research, or external decisioning.

## New endpoints

`POST /api/v1/properties/verify`

This endpoint converts an extraction result into a verified property snapshot that keeps:

- Extracted value
- Final value
- Verification status
- Source
- Confidence
- Whether the user modified the field

It is intended to support the future “review and correct” workflow before analysis runs.

Example shape:

```json
{
  "extraction": {
    "provider": "zillow",
    "source_url": "https://www.zillow.com/homedetails/example",
    "property": {
      "source_url": "https://www.zillow.com/homedetails/example",
      "provider": "zillow",
      "address": {
        "full_address": "123 Main St, Dallas, TX 75001"
      },
      "asking_price": "300000"
    },
    "metadata": {
      "extraction_method": "hasdata_api",
      "fields_found": 2,
      "fields_missing": [],
      "warnings": []
    },
    "field_provenance": {}
  },
  "corrections": {
    "annual_hoa": "0"
  },
  "confirmed_fields": ["asking_price"]
}
```

`POST /api/v1/analyses/run`

This endpoint runs deterministic underwriting from a verified property snapshot plus user-supplied assumptions.

The analysis currently returns:

- Acquisition breakdown
- Financing results
- Income results
- Operating expenses
- NOI
- Monthly and annual pre-tax cash flow
- Cap rate
- Cash-on-cash return
- DSCR
- Gross rent multiplier
- Operating expense ratio
- Break-even occupancy
- Rent-to-price ratio
- Maximum-offer thresholds
- Three scenarios: `conservative`, `expected`, `optimistic`
- Twelve stress tests
- Warnings when assumptions look risky or incomplete

## Main files for Milestone 2

- `app/api/analysis_routes.py`
  - Adds `POST /api/v1/properties/verify` and `POST /api/v1/analyses/run`
- `app/models/verification.py`
  - Verified snapshot and field status models
- `app/models/assumptions.py`
  - Underwriting input assumptions and presets
- `app/models/underwriting.py`
  - Analysis output models
- `app/services/property_verification_service.py`
  - Builds verified property snapshots from extraction output plus corrections
- `app/services/underwriting_service.py`
  - Main deterministic underwriting orchestration
- `app/calculations/`
  - Reusable financial calculation helpers
- `app/presets/analysis_presets.py`
  - Conservative, standard, aggressive, and custom preset values

## How to run the full current flow

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Extract a listing:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/"}'
```

Verify the extracted property:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/properties/verify \
  -H "Content-Type: application/json" \
  -d '{
    "extraction": {
      "provider": "zillow",
      "source_url": "https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/",
      "property": {
        "source_url": "https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/",
        "provider": "zillow",
        "address": {
          "full_address": "1620 Sunnybrook Dr, Irving, TX 75061"
        },
        "asking_price": "444000",
        "bedrooms": "4",
        "bathrooms": "3",
        "year_built": 1958,
        "property_type": "single_family"
      },
      "metadata": {
        "extraction_method": "hasdata_api",
        "fields_found": 15,
        "fields_missing": ["square_feet", "annual_property_tax", "annual_hoa"],
        "warnings": []
      }
    },
    "confirmed_fields": [
      "full_address",
      "asking_price",
      "bedrooms",
      "bathrooms",
      "year_built",
      "property_type"
    ],
    "corrections": {
      "annual_hoa": "0"
    }
  }'
```

Run deterministic underwriting:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyses/run \
  -H "Content-Type: application/json" \
  -d '{
    "property": {
      "source_url": "https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/",
      "provider": "zillow",
      "full_address": {
        "extracted_value": "1620 Sunnybrook Dr, Irving, TX 75061",
        "final_value": "1620 Sunnybrook Dr, Irving, TX 75061",
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      },
      "asking_price": {
        "extracted_value": "444000",
        "final_value": "444000",
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      },
      "bedrooms": {
        "extracted_value": "4",
        "final_value": "4",
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      },
      "bathrooms": {
        "extracted_value": "3",
        "final_value": "3",
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      },
      "square_feet": {
        "extracted_value": null,
        "final_value": null,
        "status": "missing",
        "source": null,
        "confidence": null,
        "user_modified": false
      },
      "lot_square_feet": {
        "extracted_value": null,
        "final_value": null,
        "status": "missing",
        "source": null,
        "confidence": null,
        "user_modified": false
      },
      "year_built": {
        "extracted_value": 1958,
        "final_value": 1958,
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      },
      "annual_property_tax": {
        "extracted_value": null,
        "final_value": null,
        "status": "missing",
        "source": null,
        "confidence": null,
        "user_modified": false
      },
      "annual_hoa": {
        "extracted_value": null,
        "final_value": "0",
        "status": "corrected",
        "source": null,
        "confidence": null,
        "user_modified": true
      },
      "property_type": {
        "extracted_value": "single_family",
        "final_value": "single_family",
        "status": "verified",
        "source": "hasdata_api",
        "confidence": "0.5",
        "user_modified": false
      }
    },
    "assumptions": {
      "purchase_price": "444000",
      "preset": "standard",
      "financing": {
        "type": "conventional",
        "down_payment_percent": "20",
        "interest_rate_percent": "6.75",
        "loan_term_years": 30,
        "points": "0",
        "additional_lender_fees": "0",
        "monthly_mortgage_insurance": "0"
      },
      "acquisition": {
        "closing_cost_percent": "3",
        "lender_fees": "0",
        "repairs": "5000",
        "initial_reserves": "5000",
        "other_acquisition_costs": "0"
      },
      "income": {
        "monthly_rent": "3200",
        "other_monthly_income": "0",
        "vacancy_percent": "5"
      },
      "expenses": {
        "annual_property_taxes": "8000",
        "annual_insurance": "2500",
        "annual_hoa": "0",
        "management_percent": "8",
        "maintenance_percent": "5",
        "capex_percent": "5",
        "leasing_fee_percent": "50",
        "tenant_turnover_frequency_years": "2",
        "turnover_cost": "1500",
        "owner_paid_utilities_monthly": "0",
        "landscaping_monthly": "50",
        "pest_control_monthly": "0",
        "other_monthly_expenses": "0",
        "other_annual_expenses": "0"
      }
    }
  }'
```

For this example property, the analysis returns a negative monthly cash flow and a DSCR below `1.0`, which is exactly the kind of deterministic screening output this milestone is designed to produce.

The easiest way to explore the exact request and response schemas is still `http://127.0.0.1:8000/docs`.

## Supported providers

- Zillow
- Redfin

## Architecture

- `ProviderRegistry` selects the adapter based on the incoming listing URL.
- `ListingService` coordinates provider selection, static HTTP fetch, Playwright fallback, parsing, and response shaping.
- `PropertyVerificationService` converts extraction output into a verified property snapshot with field status tracking.
- `UnderwritingService` runs deterministic acquisition, financing, income, expense, return, scenario, stress-test, and maximum-offer calculations.
- `ZillowProvider` can bypass page fetching entirely by calling HasData's Zillow Property API when `HASDATA_API_KEY` is configured.
- `RedfinProvider` can bypass page fetching entirely by calling HasData's Redfin Property API when `HASDATA_API_KEY` is configured.
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
- Deterministic underwriting tests cover calculations, verification, scenarios, stress tests, maximum-offer logic, and analysis API responses.

## Current limitations

- Provider parsing is tested against stored HTML fixtures rather than live site requests.
- Fixture coverage currently includes one successful sample per provider plus partial-data scenarios.
- Provider schemas will need continued maintenance as listing sites evolve.
- This milestone does not persist listings.
- The underwriting engine is deterministic only and does not yet include rent-comparable research, public-record enrichment, neighborhood intelligence, risk scoring, or recommendation synthesis.

## Troubleshooting

- If Zillow or Redfin returns CAPTCHA or access-blocked errors through live page fetching, configure `HASDATA_API_KEY` or `HASDATA_API_KEY_FILE` so those providers can use the HasData property endpoints instead.
- If a direct HasData `curl` works but the app still reports an older auth or fetch error, restart the FastAPI server. The most common cause is a stale running `uvicorn` process that has not reloaded the newest code or key configuration.

## How to add another provider

1. Add a new provider adapter under `app/providers/`.
2. Implement `can_handle()` and `extract()` against the shared `ListingProvider` interface.
3. Register the provider in `ProviderRegistry.default()`.
4. Add sanitized fixture HTML under `tests/fixtures/`.
5. Add provider parsing tests and, when useful, API integration coverage.
