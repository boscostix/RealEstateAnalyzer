# RealEstateAnalyzer

`RealEstateAnalyzer` is a FastAPI application for real-estate listing extraction, property verification, deterministic underwriting, research aggregation, agent-research synthesis, and investment-committee reporting.

It also includes a Next.js demo frontend in `frontend/` that walks through the full analyst workflow from listing submission to rerun analysis history.

Milestone 6 adds a persisted demo workflow on top of the earlier in-memory APIs:

- Properties are stored with stable IDs.
- Verified property snapshots are versioned.
- Analyses are stored with immutable property and assumptions snapshots.
- Analysis history and rerun lineage survive FastAPI restarts.
- Alembic migrations manage the local database schema.

## What the demo supports

- Create a property record for frontend use.
- Patch verified property values without mutating completed analysis snapshots.
- Start a persisted analysis and poll by stable `analysis_id`.
- Return lightweight running metadata while a job is in progress.
- Return full underwriting, research, agent, and committee output after completion.
- List lightweight analysis history for a property.
- Rerun a prior analysis with optional assumptions overrides.

## Current persistence model

- Database: SQLite by default via `DATABASE_URL=sqlite:///./real_estate.db`
- ORM: SQLAlchemy
- Migrations: Alembic
- Background execution: in-process asyncio tasks

### Important limitation

Completed properties, completed analyses, analysis history, and rerun lineage are durable because they are written to the database.

In-progress background jobs are not durable. If the FastAPI process stops while an analysis is `pending` or `running`, the database record remains, but that in-process task will not resume automatically after restart. This is intentional for the local demo and should be replaced with a durable worker/queue before production use.

## Project layout

```text
app/
├── agent_research/     # Specialist-agent workflow and evidence handling
├── api/                # FastAPI routes, including persisted property/analysis APIs
├── calculations/       # Deterministic underwriting math
├── db/                 # SQLAlchemy models, repositories, snapshots, Alembic-facing session helpers
├── investment_committee/
├── models/
├── providers/
├── services/           # Property persistence, analysis execution, research orchestration
└── logging.py          # Request IDs and application logging

alembic/                # Database migrations
tests/                  # Regression, API, repository, migration, and workflow coverage
```

## Requirements

- Python 3.12
- `uv`
- Docker Desktop for container validation

## Local setup

Install dependencies:

```bash
uv sync --dev
```

Install the Playwright browser used by the listing fetcher:

```bash
uv run playwright install chromium
```

Copy the environment template if you want a local `.env`:

```bash
cp .env.example .env
```

Useful variables:

- `DATABASE_URL`: defaults to `sqlite:///./real_estate.db`
- `LOG_LEVEL`: application logging level
- `OPENAI_API_KEY`: required only for live OpenAI-backed agent and committee runs
- `HASDATA_API_KEY`: optional provider extraction key for Zillow and Redfin

Secrets can also be supplied through:

- `secrets/openai_api_key.txt`
- `secrets/hasdata_api_key.txt`

## Database setup

Run migrations before starting the API:

```bash
uv run alembic upgrade head
```

The default SQLite file is created in the repository root. To inspect the active database URL in code, see [app/db/session.py](/Users/bhaskar/Downloads/RealEstateAnalyzer/app/db/session.py:11).

## Run the API

```bash
uv run uvicorn app.main:app --reload
```

Docs:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Run the frontend demo

The frontend lives in `frontend/` and talks to the persisted Milestone 6 APIs.

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend expects the FastAPI server to be running locally. By default it targets `http://127.0.0.1:8000`.

Frontend validation commands:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

### Frontend demo workflow

1. Open the landing page and paste a Zillow or Redfin listing URL.
2. Review the extraction preview and persist the property.
3. Verify or fill in property values on the verification page.
4. Set assumptions and start the analysis.
5. Poll the analysis progress page until the report opens.
6. Review the completed report and open prior versions from property history.
7. Start a rerun with optional assumption overrides.

### Demo fixture

`frontend/src/lib/demo-fixtures.ts` contains a stable property, analysis history, and completed analysis payload used by frontend tests and demo-oriented UI validation. It does not contain secrets.

## Persisted demo workflow

This is the simplest frontend-oriented flow for the Milestone 6 demo.

### 1. Create a property

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/properties \
  -H "Content-Type: application/json" \
  -d @property-create.json
```

`property-create.json` should contain:

```json
{
  "property": {
    "provider": "zillow",
    "source_url": "https://www.zillow.com/example",
    "full_address": "123 Main St, Dallas, TX 75001"
  },
  "verified_property": {
    "source_url": "https://www.zillow.com/example",
    "provider": "zillow",
    "full_address": {
      "extracted_value": "123 Main St, Dallas, TX 75001",
      "final_value": "123 Main St, Dallas, TX 75001",
      "status": "verified",
      "source": "hasdata_api",
      "confidence": "0.90",
      "user_modified": false
    }
  }
}
```

The response returns a stable property ID plus summary fields.

### 2. Patch verified property values if needed

```bash
curl -s -X PATCH http://127.0.0.1:8000/api/v1/properties/$PROPERTY_ID \
  -H "Content-Type: application/json" \
  -d @property-patch.json
```

Use this when the frontend verification flow changes values such as rent, taxes, or asking price. Existing completed analysis snapshots remain unchanged.

### 3. Start an analysis

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/properties/$PROPERTY_ID/analyses \
  -H "Content-Type: application/json" \
  -d @analysis-create.json
```

`analysis-create.json` should contain assumptions and may include an optional decision context:

```json
{
  "assumptions": {
    "financing": {
      "interest_rate_percent": "6.75"
    }
  }
}
```

The response returns a stable `analysis_id`, persisted snapshots, and the incremented version.

### 4. Poll the analysis

```bash
curl -s http://127.0.0.1:8000/api/v1/analyses/$ANALYSIS_ID
```

While running, the response includes:

- `status`
- `current_stage`
- lightweight `execution` metadata

After completion, the response also includes:

- `property_snapshot`
- `assumptions`
- `underwriting`
- `research`
- `agent_research`
- `investment_committee`

If execution fails, the response includes safe failure details such as `failure_stage`, `error_code`, and `error_message`.

### 5. Render the completed report

The frontend should render the completed report from `GET /api/v1/analyses/{analysis_id}` after `status` becomes `completed`.

### 6. Load analysis history

```bash
curl -s http://127.0.0.1:8000/api/v1/properties/$PROPERTY_ID/analyses
```

This returns lightweight history summaries only. The property detail endpoint intentionally does not return the full historical analysis payloads.

### 7. Rerun with updated assumptions

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/analyses/$ANALYSIS_ID/rerun \
  -H "Content-Type: application/json" \
  -d '{"assumption_overrides":{"financing":{"interest_rate_percent":"7.10"}}}'
```

Reruns:

- keep the source analysis immutable
- create a new version
- record `parent_analysis_id`
- use a fresh immutable property snapshot from the current verified property state

## Persisted API endpoints

Frontend-oriented persistence endpoints:

```text
POST  /api/v1/properties
GET   /api/v1/properties/{property_id}
PATCH /api/v1/properties/{property_id}
POST  /api/v1/properties/{property_id}/analyses
GET   /api/v1/analyses/{analysis_id}
GET   /api/v1/properties/{property_id}/analyses
POST  /api/v1/analyses/{analysis_id}/rerun
```

Earlier Milestones 1 through 5 endpoints are still available:

```text
POST /api/v1/listings/extract
POST /api/v1/properties/verify
POST /api/v1/analyses/run
POST /api/v1/research/package
POST /api/v1/agent-research/run
POST /api/v1/investment-committee/analyze
```

## Schema and indexing notes

Current persistence metadata includes:

- property snapshot schema version
- verified property schema version
- analysis snapshot schema version
- report schema version

Indexes currently support the demo’s main lookup paths:

- property provider lookups
- property address lookups
- property creation ordering
- analysis status lookup
- analysis lookup by property
- analysis history lookup by `(property_id, created_at)`

## Common commands

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run mypy:

```bash
uv run mypy app tests
```

Run migrations:

```bash
uv run alembic upgrade head
```

## Docker

The Docker image now runs Alembic automatically before starting Uvicorn.

Build and run:

```bash
docker compose up --build
```

Docker defaults:

- container database path: `/app/data/real_estate.db`
- compose volume: `./data:/app/data`
- secrets volume: `./secrets:/app/secrets:ro`

This means completed property and analysis data survive container restarts as long as the mounted `./data` directory is preserved.

## Testing coverage for Milestone 6

Milestone 6 coverage now includes:

- repository tests
- property API tests
- analysis execution service tests
- analysis API tests
- rerun tests
- end-to-end persisted workflow tests
- migration tests
- failure-path tests
- restart-persistence tests
- index smoke tests

## Structured logging

Application logs include request-level and analysis-level events such as:

- property create/get/patch completion
- analysis create/get/list/rerun completion
- analysis scheduling
- analysis stage transitions
- analysis completion
- analysis failure metadata

The current logger is configured in [app/logging.py](/Users/bhaskar/Downloads/RealEstateAnalyzer/app/logging.py:1).

## Production follow-ups beyond the demo

- Replace the in-process task runner with a durable queue/worker.
- Move from SQLite to PostgreSQL for concurrent multi-user use.
- Add auth, authorization, and user scoping.
- Add durable retry and dead-letter handling for failed jobs.
