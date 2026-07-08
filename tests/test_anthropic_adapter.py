import asyncio
from types import SimpleNamespace
from typing import Any

from aehf.adapters.anthropic import AnthropicAdapter
from aehf.core.case import EvalCase
from aehf.core.transcript import Termination, Transcript
from aehf.tools.mock import mock_provider_factory


def make_case(**overrides: Any) -> EvalCase:
    fields: dict[str, Any] = {
        "id": "c1",
        "task_prompt": "what is the population of France?",
        "tools": [],
        "success_criteria": {},
        "max_steps": 5,
        "timeout_seconds": 30,
        "token_budget": 1000,
        "tool_fixtures": {"search": "68 million"},
    }
    fields.update(overrides)
    return EvalCase(**fields)


def text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def tool_block(name: str, args: dict[str, Any], block_id: str = "toolu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, input=args, id=block_id)


def response(blocks: list[SimpleNamespace], stop_reason: str, input_tokens: int = 10, output_tokens: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        content=blocks,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class StubClient:
    """Stands in for AsyncAnthropic: pops scripted responses off a list."""

    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = list(responses)
        self.calls = 0
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        return self._responses.pop(0)


def run_adapter(responses: list[SimpleNamespace], case: EvalCase) -> tuple[Transcript, StubClient]:
    client = StubClient(responses)
    adapter = AnthropicAdapter(client=client, provider_factory=mock_provider_factory, model="stub", max_tokens=100)  # type: ignore[arg-type]
    return asyncio.run(adapter.run(case)), client


def test_tool_use_with_no_text_block() -> None:
    # regression: a pure tool_use response used to leave model_output unbound
    transcript, _ = run_adapter(
        [
            response([tool_block("search", {"q": "france"})], "tool_use"),
            response([text_block("68 million")], "end_turn"),
        ],
        make_case(),
    )
    assert transcript.termination_reason == Termination.finished
    assert len(transcript.ordered_steps) == 2
    assert transcript.ordered_steps[0].model_output == ""
    tool_calls = transcript.ordered_steps[0].tool_calls
    assert tool_calls is not None
    assert tool_calls[0].arguments == {"q": "france"}
    assert tool_calls[0].result == "68 million"
    assert transcript.final_answer == "68 million"


def test_token_math_counts_input_every_turn() -> None:
    transcript, _ = run_adapter(
        [
            response([tool_block("search", {})], "tool_use", input_tokens=10, output_tokens=5),
            response([text_block("done")], "end_turn", input_tokens=20, output_tokens=5),
        ],
        make_case(),
    )
    assert transcript.total_tokens == 40
    assert transcript.ordered_steps[0].token_usage == 15
    assert transcript.ordered_steps[1].token_usage == 25


def test_unexpected_stop_reason_terminates() -> None:
    # regression: max_tokens (or any unknown stop_reason) used to loop forever
    transcript, client = run_adapter(
        [response([text_block("truncated answer")], "max_tokens")],
        make_case(),
    )
    assert transcript.termination_reason == Termination.unexpected_stop
    assert transcript.final_answer == "truncated answer"
    assert client.calls == 1


def test_refusal_is_refused_not_crashed() -> None:
    transcript, _ = run_adapter(
        [response([text_block("I can't help with that")], "refusal")],
        make_case(),
    )
    assert transcript.termination_reason == Termination.refused


def test_max_steps_enforced_before_api_call() -> None:
    transcript, client = run_adapter(
        [response([tool_block("search", {})], "tool_use")],
        make_case(max_steps=1),
    )
    assert transcript.termination_reason == Termination.max_steps
    assert client.calls == 1  # exactly max_steps calls, never max_steps + 1


def test_token_budget_enforced_before_api_call() -> None:
    transcript, client = run_adapter(
        [response([tool_block("search", {})], "tool_use", input_tokens=100, output_tokens=50)],
        make_case(token_budget=100),
    )
    assert transcript.termination_reason == Termination.budget_exceeded
    assert client.calls == 1
