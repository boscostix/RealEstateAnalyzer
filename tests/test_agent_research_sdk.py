"""Tests for the mockable OpenAI Agents SDK wrapper."""

from __future__ import annotations

import pytest

from app.agent_research.definitions import build_specialist_agents
from app.agent_research.exceptions import InvalidStructuredAgentOutputError
from app.agent_research.sdk import OpenAIAgentRunner
from app.agent_research.tracing import build_run_config
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import MockRunResult, make_agent_context, make_agent_output


@pytest.mark.asyncio
async def test_openai_agent_runner_uses_runner_run(monkeypatch: pytest.MonkeyPatch) -> None:
    context = make_agent_context()
    agents = build_specialist_agents(context.agent_config.model)
    expected_output = make_agent_output()

    async def fake_run(*args: object, **kwargs: object) -> MockRunResult:
        assert args[0] is agents[AgentName.LISTING]
        assert args[1] == "Summarize the listing."
        assert kwargs["context"] is context
        return MockRunResult(expected_output)

    from agents import Runner

    monkeypatch.setattr(Runner, "run", fake_run)

    runner = OpenAIAgentRunner()
    result = await runner.run(
        agent=agents[AgentName.LISTING],
        agent_input="Summarize the listing.",
        context=context,
        run_config=build_run_config(context.agent_config, request_id=context.request_id),
        output_type=type(expected_output),
    )

    assert result == expected_output


@pytest.mark.asyncio
async def test_openai_agent_runner_raises_structured_output_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = make_agent_context()
    agents = build_specialist_agents(context.agent_config.model)

    async def fake_run(*args: object, **kwargs: object) -> MockRunResult:
        return MockRunResult({"not": "structured"})

    from agents import Runner

    monkeypatch.setattr(Runner, "run", fake_run)

    runner = OpenAIAgentRunner()
    with pytest.raises(InvalidStructuredAgentOutputError):
        await runner.run(
            agent=agents[AgentName.LISTING],
            agent_input="Summarize the listing.",
            context=context,
            run_config=build_run_config(context.agent_config, request_id=context.request_id),
            output_type=type(make_agent_output()),
        )
