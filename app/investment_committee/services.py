"""Service wrapper for running the investment-committee agent safely."""

from __future__ import annotations

import asyncio

from app.investment_committee.config import CommitteeRuntimeConfig
from app.investment_committee.context import CommitteeRunContext
from app.investment_committee.definitions import build_investment_committee_agent
from app.investment_committee.exceptions import (
    CommitteeModelFailureError,
    CommitteeTimeoutError,
    InvalidCommitteeStructuredOutputError,
    MissingCommitteeInputError,
)
from app.investment_committee.input_builders import build_committee_model_input
from app.investment_committee.models import InvestmentCommitteeInput, InvestmentCommitteeOutput
from app.investment_committee.sanitization import serialize_committee_model_input
from app.investment_committee.sdk import CommitteeRunnerProtocol, OpenAICommitteeRunner
from app.investment_committee.tracing import (
    build_committee_run_config,
    configure_committee_tracing,
)


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
                return await asyncio.wait_for(
                    self._runner.run(
                        agent=agent,
                        agent_input=serialized_input,
                        context=context,
                        run_config=run_config,
                        output_type=InvestmentCommitteeOutput,
                    ),
                    timeout=self._config.timeout_seconds,
                )
            except InvalidCommitteeStructuredOutputError:
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
