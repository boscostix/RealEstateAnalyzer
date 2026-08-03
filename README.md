# RealEstateAnalyzer

`RealEstateAnalyzer` is a Python 3.12 FastAPI application for structured real estate listing ingestion, deterministic underwriting, deterministic research collection, evidence-backed agent research packaging, and a policy-constrained investment committee recommendation workflow.

The project is being built in phases. The current repository already includes:

- Listing extraction for Zillow and Redfin
- Property verification with field-level provenance
- Deterministic underwriting and stress testing
- Deterministic research services for public records, comparable properties, and neighborhood data
- Structured specialist-agent analysis on top of verified data and research
- A unified `/api/v1/agent-research/run` endpoint that returns traceable outputs without final investment recommendations
- An `/api/v1/investment-committee/analyze` endpoint that turns deterministic upstream analysis into a structured, evidence-backed committee recommendation

## What the system does today

- Accepts supported listing URLs and normalizes property data
- Lets downstream workflows distinguish extracted, corrected, verified, and missing fields
- Runs deterministic underwriting without LLM math
- Builds normalized research packages with citations, confidence, cache metadata, and provider provenance
- Runs narrow specialist agents over verified inputs and structured research
- Preserves evidence, conflicts, warnings, missing information, and execution metadata in the final agent-research package
- Produces a structured investment committee recommendation without allowing the model to recalculate deterministic metrics

## What is intentionally not included

- User authentication
- Frontend UI
- Database persistence
- Autonomous investment recommendations
- Billing
- Deployment infrastructure beyond local Docker support

## Supported listing providers

- Zillow
- Redfin

## Architecture

```text
app/
├── agent_research/     # Typed tools, specialist agents, orchestration, conflicts, synthesis
├── api/                # FastAPI route modules
├── calculations/       # Deterministic underwriting calculations
├── models/             # Extraction, verification, research, and underwriting models
├── presets/            # Underwriting assumption presets
├── providers/          # Listing providers plus research provider adapters
├── services/           # Fetching, verification, underwriting, research orchestration
├── utils/              # Parsing, validation, SSRF, and shared helpers
└── logging.py          # Request-id middleware and structured application logging

tests/
├── fixtures/           # Sanitized listing, research, and evaluation fixtures
└── ...
```

## Requirements

- Python 3.12
- `uv`
- Docker Desktop if you want to run the container locally

## Local setup

Install dependencies:

```bash
uv sync --dev
```

Install the Playwright browser used by the fallback listing fetcher:

```bash
uv run playwright install chromium
```

If you have a HasData key for Zillow and Redfin property lookups, either export it:

```bash
export HASDATA_API_KEY=your_key_here
```

or place it in:

```text
secrets/hasdata_api_key.txt
```

That file should contain only the raw API key on one line.

If you want to run the OpenAI-backed agent workflow locally, set:

```bash
export OPENAI_API_KEY=your_key_here
```

The default environment variables are listed in [.env.example](/Users/bhaskar/Downloads/RealEstateAnalyzer/.env.example).

## Run the API

Start the server:

```bash
uv run uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

Interactive docs:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

The root path `/` is not a homepage, so `GET /` returning `{"detail":"Not Found"}` is expected.

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
uv run mypy app
```

## API endpoints

Listing extraction:

```text
POST /api/v1/listings/extract
```

Property verification:

```text
POST /api/v1/properties/verify
```

Deterministic underwriting:

```text
POST /api/v1/analyses/run
```

Deterministic research package:

```text
POST /api/v1/research/run
```

Structured agent research:

```text
POST /api/v1/agent-research/run
```

Investment committee analysis:

```text
POST /api/v1/investment-committee/analyze
```

## Example: extract a Zillow listing

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/"}'
```

If a HasData key is configured and accepted, the response returns normalized property data similar to:

```json
{
  "success": true,
  "provider": "zillow",
  "source_url": "https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/",
  "property": {
    "provider": "zillow",
    "source_url": "https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/",
    "address": {
      "full_address": "1620 Sunnybrook Dr, Irving, TX 75061"
    },
    "asking_price": "444000"
  },
  "metadata": {
    "extraction_method": "hasdata_api",
    "fields_found": 15,
    "fields_missing": [],
    "warnings": []
  }
}
```

## End-to-end flow you can run today

1. Call `POST /api/v1/listings/extract` with a Zillow or Redfin URL.
2. Send the extraction result to `POST /api/v1/properties/verify` with any corrected fields.
3. Send the verified property to `POST /api/v1/analyses/run` for deterministic underwriting.
4. Optionally send the verified property plus underwriting result to `POST /api/v1/research/run` for deterministic research aggregation.
5. Send the verified property, extraction, research package, and underwriting result to `POST /api/v1/agent-research/run` for evidence-backed specialist-agent outputs.
6. Send the verified property, underwriting result, and unified agent research package to `POST /api/v1/investment-committee/analyze` for a structured committee recommendation.

The Swagger docs are the easiest place to inspect the exact request and response schemas for each step.

## Agent research workflow

The structured agent workflow is designed to stay narrow and auditable.

It currently includes:

- Listing agent
- Public records agent
- Comparable agent
- Neighborhood agent
- Property risk agent
- Deterministic orchestration, conflict handling, and unified synthesis

It does not generate a final buy/pass recommendation.

The final package preserves:

- Agent-specific outputs
- Evidence references
- Source and citation ownership
- Conflicts and conflict status
- Missing information
- Due-diligence questions
- Usage totals
- Trace metadata
- Warnings and partial-failure status

## Investment committee workflow

The investment committee layer consumes verified property data, deterministic underwriting, and the unified agent-research package.

It returns:

- A structured recommendation label
- A confidence score plus deterministic confidence reasons
- Deterministic offer support boundaries when applicable
- Reasons for and against proceeding
- Missing-information impacts
- Ranked material risks
- Due-diligence checklist items with timing and priority
- What-must-be-true conditions
- Negotiation points tied to valid evidence
- Execution and usage metadata

It does not:

- Recalculate deterministic financial metrics
- Invent offer values, rents, or repair numbers
- Hide conflicts or missing information
- Bypass evidence or recommendation policy rules

## Tracing and hardening

The current agent workflow includes:

- OpenAI tracing integration toggle
- Workflow names and prompt-version reporting
- Agent and tool lifecycle summaries
- Sensitive-data exclusion by default
- Prompt-injection sanitization for untrusted research text
- Evidence validation and source ownership checks
- Fair-housing guardrails for neighborhood outputs
- Regression fixtures for conflict recall, evidence coverage, and missing-data recall

Sensitive research text is sanitized before it reaches the agents, and raw HTML, cookies, and secrets are not passed through typed agent tools.

The investment committee workflow adds:

- Deterministic recommendation downgrades when policy disallows a more aggressive label
- Offer-range validation against existing deterministic values
- Due-diligence and negotiation-point hardening
- Trace metadata with request, analysis, workflow, prompt, and agent version fields
- Sensitive-data exclusion by default in trace metadata
- Fixture-driven evaluations for policy, evidence, conflicts, missing data, confidence, and prompt injection

## Environment variables

Important variables include:

- `HASDATA_API_KEY`
- `HASDATA_API_KEY_FILE`
- `ZILLOW_USE_HASDATA`
- `OPENAI_API_KEY`
- `OPENAI_AGENT_MODEL`
- `OPENAI_AGENT_PROMPT_VERSION`
- `OPENAI_AGENT_MAX_TURNS`
- `OPENAI_AGENT_TIMEOUT_SECONDS`
- `OPENAI_AGENT_WORKFLOW_TIMEOUT_SECONDS`
- `OPENAI_AGENT_MAX_PARALLEL_AGENTS`
- `OPENAI_AGENT_RETRY_ATTEMPTS`
- `OPENAI_AGENT_TRACING_ENABLED`
- `OPENAI_AGENT_WORKFLOW_NAME`
- `OPENAI_AGENT_TRACE_SENSITIVE_DATA`
- `ENABLE_LIVE_AGENT_RESEARCH_TESTS`
- `OPENAI_COMMITTEE_MODEL`
- `OPENAI_COMMITTEE_PROMPT_VERSION`
- `OPENAI_COMMITTEE_MAX_TURNS`
- `OPENAI_COMMITTEE_TIMEOUT_SECONDS`
- `OPENAI_COMMITTEE_RETRY_ATTEMPTS`
- `OPENAI_COMMITTEE_TRACING_ENABLED`
- `OPENAI_COMMITTEE_WORKFLOW_NAME`
- `OPENAI_COMMITTEE_TRACE_SENSITIVE_DATA`
- `ENABLE_LIVE_INVESTMENT_COMMITTEE_TESTS`

See [.env.example](/Users/bhaskar/Downloads/RealEstateAnalyzer/.env.example) for defaults.

## Optional live agent test

Normal tests are fully mocked and do not require live OpenAI calls.

If you want to run the manual live agent integration test, set:

```bash
export ENABLE_LIVE_AGENT_RESEARCH_TESTS=true
export OPENAI_API_KEY=your_key_here
```

Then run:

```bash
uv run pytest tests/test_agent_research_live.py
```

If the flag is not set, the live test is skipped automatically.

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

The API will be available at `http://127.0.0.1:8000`.

The compose file now:

- Mounts `./secrets` into `/app/secrets` as read-only
- Passes through the HasData, OpenAI, tracing, and agent workflow environment variables
- Defaults `HASDATA_API_KEY_FILE` to `/app/secrets/hasdata_api_key.txt` inside the container

To validate the compose configuration without starting containers:

```bash
docker compose config
```

The Docker image installs Chromium for the Playwright fallback path.

## Testing strategy

The repository uses fixture-based and mocked tests for normal development:

- Listing provider parsing tests use sanitized HTML fixtures
- Fetcher tests mock HTTP and Playwright behavior
- Research-provider tests use deterministic fixture data
- Agent tests mock model execution by default
- Evaluation tests cover evidence coverage, conflict recall, missing-data recall, prompt-injection handling, and fair-housing guardrails

Run the full validation suite with:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

## Notes on real-world scraping behavior

Zillow and Redfin often block direct automated browsing. The application therefore supports HasData-backed provider integrations for those sites. When direct page access is blocked, the service returns structured errors instead of trying to bypass CAPTCHA systems.

## Extending the system

To add another listing or research provider:

1. Add a provider implementation under `app/providers/`.
2. Reuse the shared models and provider interfaces instead of introducing provider-specific response shapes.
3. Register the provider in the appropriate registry.
4. Add fixture-based tests under `tests/fixtures/` and `tests/`.
5. Keep provenance, confidence, and structured warnings intact.

## Current status summary

The repository now supports:

- Listing ingestion and extraction
- Property verification
- Deterministic underwriting
- Deterministic research aggregation
- Structured specialist-agent research synthesis
- Traceable evidence and conflict handling
- Mocked regression and hardening coverage
