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

If you want to run the OpenAI-backed agent workflows locally, either export:

```bash
export OPENAI_API_KEY=your_key_here
```

or place it in:

```text
secrets/openai_api_key.txt
```

That file should contain only the raw API key on one line.

The default environment variables are listed in [.env.example](/Users/bhaskar/Downloads/RealEstateAnalyzer/.env.example).

### Recommended local workflow

Use two terminal sessions:

1. A server terminal where you export environment variables and run `uvicorn`
2. A request terminal where you run `curl`, `jq`, and direct API tests

If you restart the server after changing environment variables, you do not need to rerun the earlier API steps as long as you still have the saved JSON files from those steps.

## Run the API

Start the server:

```bash
uv run uvicorn app.main:app --reload
```

If you want to run the OpenAI-backed workflows locally, it is safest to export the variables in the same terminal where you start `uvicorn`:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_AGENT_MODEL=gpt-5-mini
export OPENAI_COMMITTEE_MODEL=gpt-5-mini
export OPENAI_AGENT_TIMEOUT_SECONDS=90
export OPENAI_AGENT_WORKFLOW_TIMEOUT_SECONDS=180
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
POST /api/v1/research/package
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
4. Optionally send the verified property to `POST /api/v1/research/package` for deterministic research aggregation.
5. Send the verified property, extraction, research package, and underwriting result to `POST /api/v1/agent-research/run` for evidence-backed specialist-agent outputs.
6. Send the verified property, underwriting result, and unified agent research package to `POST /api/v1/investment-committee/analyze` for a structured committee recommendation.

The Swagger docs are the easiest place to inspect the exact request and response schemas for each step.

## End-to-end example

The sequence below saves each step to disk so later steps can reuse it even if you restart the server.

### Step 1: extract a listing

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.zillow.com/homedetails/1620-Sunnybrook-Dr-Irving-TX-75061/27118489_zpid/"}' \
  > extract.json
```

### Step 2: verify extracted fields

```bash
jq '{
  extraction: .,
  confirmed_fields: [
    "full_address",
    "asking_price",
    "bedrooms",
    "bathrooms",
    "year_built",
    "property_type"
  ],
  corrections: {}
}' extract.json > verify-request.json

curl -s -X POST http://127.0.0.1:8000/api/v1/properties/verify \
  -H "Content-Type: application/json" \
  -d @verify-request.json \
  > verify.json
```

Add known missing values through `corrections` if you have them, for example `square_feet` or `annual_property_tax`.

### Step 3: run deterministic underwriting

```bash
cat > analysis-request.json <<'EOF'
{
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
      "final_value": null,
      "status": "missing",
      "source": null,
      "confidence": null,
      "user_modified": false
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
    "purchase_price": 444000,
    "preset": "standard",
    "financing": {
      "type": "conventional",
      "down_payment_percent": 20,
      "interest_rate_percent": 6.5,
      "loan_term_years": 30
    },
    "acquisition": {
      "closing_cost_percent": 3,
      "repairs": 5000,
      "initial_reserves": 5000
    },
    "income": {
      "monthly_rent": 2200,
      "vacancy_percent": 5
    },
    "expenses": {
      "annual_property_taxes": 0,
      "annual_insurance": 1800,
      "annual_hoa": 0,
      "management_percent": 8,
      "maintenance_percent": 5,
      "capex_percent": 5
    },
    "targets": {
      "monthly_cash_flow": 0,
      "dscr": 1.0
    }
  }
}
EOF

curl -s -X POST http://127.0.0.1:8000/api/v1/analyses/run \
  -H "Content-Type: application/json" \
  -d @analysis-request.json \
  > analysis.json
```

The assumptions above are an example only. Replace rent, taxes, HOA, insurance, and repair values with better local inputs when you have them.

### Step 4: build the deterministic research package

```bash
jq '{ property: .property, bypass_cache: false }' verify.json > research-request.json

curl -s -X POST http://127.0.0.1:8000/api/v1/research/package \
  -H "Content-Type: application/json" \
  -d @research-request.json \
  > research.json
```

If no research providers are configured, this step may still return `success: true` with warnings and null domain results.

### Step 5: run agent research

```bash
jq -n \
  --slurpfile verify verify.json \
  --slurpfile extract extract.json \
  --slurpfile analysis analysis.json \
  --slurpfile research research.json \
  '{
    verified_property: $verify[0].property,
    listing_extraction: $extract[0],
    research_package: $research[0].package,
    underwriting_result: $analysis[0].analysis,
    analysis_id: "sunnybrook-demo",
    bypass_research_cache: false
  }' > agent-research-request.json

curl -s -X POST http://127.0.0.1:8000/api/v1/agent-research/run \
  -H "Content-Type: application/json" \
  -d @agent-research-request.json \
  > agent-research.json
```

### Step 6: run the investment committee workflow

```bash
jq -n \
  --slurpfile verify verify.json \
  --slurpfile analysisReq analysis-request.json \
  --slurpfile analysis analysis.json \
  --slurpfile agent agent-research.json \
  '{
    property: $verify[0].property,
    assumptions: $analysisReq[0].assumptions,
    underwriting: $analysis[0].analysis,
    agent_research: $agent[0].package,
    analysis_id: "sunnybrook-demo"
  }' > committee-request.json

curl -s -X POST http://127.0.0.1:8000/api/v1/investment-committee/analyze \
  -H "Content-Type: application/json" \
  -d @committee-request.json \
  > committee.json
```

## Troubleshooting

### Shell line continuation

When using multiline `curl` commands in `zsh`, the trailing `\` must be the very last character on the line. This is correct:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/listings/extract \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

If you put a space after `\`, the shell may break the command in confusing ways.

### OPENAI_API_KEY looks empty

If a direct OpenAI API test says the key is empty, confirm it in the same terminal session where you are running the command:

```bash
echo "KEY=[$OPENAI_API_KEY]"
printenv OPENAI_API_KEY
```

If it is empty, export it again in that same terminal:

```bash
export OPENAI_API_KEY=your_key_here
```

### OpenAI key and server terminal

The terminal that starts `uvicorn` must already have `OPENAI_API_KEY` exported if you want `POST /api/v1/agent-research/run` or `POST /api/v1/investment-committee/analyze` to work.

### Agent research timeouts

If `agent-research` times out locally, increase the OpenAI workflow timeouts before starting the server:

```bash
export OPENAI_AGENT_TIMEOUT_SECONDS=90
export OPENAI_AGENT_WORKFLOW_TIMEOUT_SECONDS=180
uv run uvicorn app.main:app --reload
```

### Partial success from agent research

`POST /api/v1/agent-research/run` can return `success: true` with warnings and partial outputs. For example, if deterministic research providers are not configured, `listing_analysis` may succeed while `public_records_analysis`, `comparable_analysis`, `neighborhood_analysis`, and `risk_analysis` remain `null`.

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
