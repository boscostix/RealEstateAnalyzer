"""Service wrapper for running the investment-committee agent safely."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from app.investment_committee.config import CommitteeRuntimeConfig
from app.investment_committee.context import CommitteeRunContext
from app.investment_committee.definitions import build_investment_committee_agent
from app.investment_committee.exceptions import (
    CommitteeModelFailureError,
    CommitteeTimeoutError,
    InvalidCommitteeStructuredOutputError,
    InvestmentCommitteeError,
    MissingCommitteeInputError,
)
from app.investment_committee.input_builders import build_committee_model_input
from app.investment_committee.models import (
    CommitteeExecutionMetadata,
    CommitteeUsageMetadata,
    InvestmentCommitteeAnalysisResult,
    InvestmentCommitteeInput,
    InvestmentCommitteeOutput,
)
from app.investment_committee.sanitization import serialize_committee_model_input
from app.investment_committee.sdk import CommitteeRunnerProtocol, OpenAICommitteeRunner
from app.investment_committee.tracing import (
    build_committee_run_config,
    configure_committee_tracing,
)
from app.investment_committee.validation import validate_and_enforce_output
from app.investment_committee.versioning import (
    COMMITTEE_INPUT_FORMAT_VERSION,
    COMMITTEE_PROMPT_VERSION,
    CONFIDENCE_POLICY_VERSION,
    OFFER_RANGE_POLICY_VERSION,
    RECOMMENDATION_POLICY_VERSION,
)
from app.investment_committee.versioning_runtime import build_committee_agent_version


class InvestmentCommitteeService:
    """Bounded wrapper around one investment-committee agent run."""

    def __init__(
        self,
        *,
        runner: CommitteeRunnerProtocol | None = None,
        config: CommitteeRuntimeConfig | None = None,
    ) -> None:
        self._runner = runner or OpenAICommitteeRunner()
        self._config = config or CommitteeRuntimeConfig.from_env()

    async def analyze(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeOutput:
        if not request_id:
            raise MissingCommitteeInputError(message="request_id is required for committee runs.")

        configure_committee_tracing(self._config)
        prepared_input = build_committee_model_input(committee_input)
        serialized_input = serialize_committee_model_input(prepared_input)
        context = CommitteeRunContext(
            request_id=request_id,
            analysis_id=analysis_id,
            committee_config=self._config,
        )
        run_config = build_committee_run_config(
            self._config,
            request_id=request_id,
            analysis_id=analysis_id,
        )
        agent = build_investment_committee_agent(self._config.model)

        attempts = self._config.retry_attempts + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                output = await asyncio.wait_for(
                    self._runner.run(
                        agent=agent,
                        agent_input=serialized_input,
                        context=context,
                        run_config=run_config,
                        output_type=InvestmentCommitteeOutput,
                    ),
                    timeout=self._config.timeout_seconds,
                )
                return validate_and_enforce_output(
                    output,
                    prepared_input=prepared_input,
                )
            except InvalidCommitteeStructuredOutputError:
                raise
            except InvestmentCommitteeError:
                raise
            except TimeoutError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise CommitteeTimeoutError() from exc
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise CommitteeModelFailureError(message=str(exc)) from exc

        raise CommitteeModelFailureError(
            message="Investment committee run failed without a terminal error."
        ) from last_error

    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeAnalysisResult:
        if not request_id:
            raise MissingCommitteeInputError(message="request_id is required for committee runs.")

        configure_committee_tracing(self._config)
        prepared_input = build_committee_model_input(committee_input)
        serialized_input = serialize_committee_model_input(prepared_input)
        context = CommitteeRunContext(
            request_id=request_id,
            analysis_id=analysis_id,
            committee_config=self._config,
        )
        run_config = build_committee_run_config(
            self._config,
            request_id=request_id,
            analysis_id=analysis_id,
        )
        agent = build_investment_committee_agent(self._config.model)
        started_at = datetime.now(UTC)
        started_perf = time.perf_counter()

        attempts = self._config.retry_attempts + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                artifacts = await asyncio.wait_for(
                    self._runner.run_detailed(
                        agent=agent,
                        agent_input=serialized_input,
                        context=context,
                        run_config=run_config,
                        output_type=InvestmentCommitteeOutput,
                    ),
                    timeout=self._config.timeout_seconds,
                )
                output = validate_and_enforce_output(
                    artifacts.output,
                    prepared_input=prepared_input,
                )
                completed_at = datetime.now(UTC)
                warnings = list(output.warnings)
                return InvestmentCommitteeAnalysisResult(
                    output=output,
                    execution_metadata=CommitteeExecutionMetadata(
                        request_id=request_id,
                        workflow_name=self._config.tracing.workflow_name,
                        agent_version=build_committee_agent_version(),
                        prompt_version=COMMITTEE_PROMPT_VERSION,
                        input_format_version=COMMITTEE_INPUT_FORMAT_VERSION,
                        recommendation_policy_version=RECOMMENDATION_POLICY_VERSION,
                        offer_range_policy_version=OFFER_RANGE_POLICY_VERSION,
                        confidence_policy_version=CONFIDENCE_POLICY_VERSION,
                        model=self._config.model,
                        traced=self._config.tracing.enabled,
                        trace_metadata={
                            key: value
                            for key, value in (run_config.trace_metadata or {}).items()
                            if value is not None
                        },
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=int((time.perf_counter() - started_perf) * 1000),
                        retry_count=attempt,
                        validation_status="passed",
                        warning_count=len(warnings),
                    ),
                    usage_metadata=CommitteeUsageMetadata(
                        requests=artifacts.usage.requests,
                        input_tokens=artifacts.usage.input_tokens,
                        output_tokens=artifacts.usage.output_tokens,
                        total_tokens=artifacts.usage.total_tokens,
                        response_count=artifacts.response_count,
                    ),
                    warnings=warnings,
                )
            except InvalidCommitteeStructuredOutputError:
                raise
            except InvestmentCommitteeError:
                raise
            except TimeoutError as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise CommitteeTimeoutError() from exc
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    raise CommitteeModelFailureError(message=str(exc)) from exc

        raise CommitteeModelFailureError(
            message="Investment committee run failed without a terminal error."
        ) from last_error
