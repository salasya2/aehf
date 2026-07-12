from types import SimpleNamespace
from typing import Any

import pytest

from aehf.core.case import EvalCase, SuccessCriteria
from aehf.core.transcript import Step, Termination, ToolCall, Transcript
from aehf.judges.llmjudge import LLMJudge


def make_case(rubric: str | None = "Answer states 6 and uses the calculator.") -> EvalCase:
    return EvalCase(
        id="1",
        task_prompt="What is 2*3?",
        tools=[],
        success_criteria=SuccessCriteria(rubric=rubric),
        max_steps=5,
        timeout_seconds=30,
        token_budget=1000,
    )


def make_transcript() -> Transcript:
    return Transcript(
        id="1",
        ordered_steps=[
            Step(
                model_output="I'll use the calculator.",
                tool_calls=[ToolCall(toolname="calculator", arguments={"expression": "2*3"}, result="6", latency=0.5)],
                token_usage=50,
            ),
            Step(model_output="The answer is 6.", tool_calls=None, token_usage=20),
        ],
        final_answer="6",
        total_tokens=70,
        duration_seconds=1.0,
        termination_reason=Termination.finished,
    )


def verdict_block(passed: bool, reasoning: str = "cited evidence", confidence: float = 0.9) -> SimpleNamespace:
    return SimpleNamespace(
        type="tool_use",
        id="toolu_1",
        name="record-verdict",
        input={"passed": passed, "reasoning": reasoning, "confidence": confidence},
    )


class StubClient:
    """Stands in for AsyncAnthropic; returns one scripted response and
    records the kwargs of the call so tests can assert on the request."""

    def __init__(self, response_blocks: list[SimpleNamespace]) -> None:
        self._blocks = response_blocks
        self.kwargs: dict[str, Any] = {}
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(content=self._blocks, stop_reason="tool_use")


def make_judge(client: StubClient, prompt_version: str = "v1") -> LLMJudge:
    return LLMJudge(client=client, prompt_version=prompt_version, model="stub", max_tokens=512)  # type: ignore[arg-type]


async def test_pass_verdict_maps() -> None:
    judge = make_judge(StubClient([verdict_block(passed=True, confidence=0.9)]))
    verdict = await judge.score(make_case(), make_transcript())
    assert verdict.passed
    assert verdict.score == 0.9
    assert verdict.reasoning == "cited evidence"
    assert verdict.judge_name == "LLMJudge"
    assert verdict.version == "v1"


async def test_fail_verdict_maps() -> None:
    judge = make_judge(StubClient([verdict_block(passed=False, confidence=0.4)]))
    verdict = await judge.score(make_case(), make_transcript())
    assert not verdict.passed
    assert verdict.score == 0.4


async def test_no_tool_use_block_raises() -> None:
    text_only = SimpleNamespace(type="text", text="I think it passed!")
    judge = make_judge(StubClient([text_only]))
    with pytest.raises(ValueError):
        await judge.score(make_case(), make_transcript())


def test_unknown_prompt_version_raises() -> None:
    with pytest.raises(ValueError):
        make_judge(StubClient([]), prompt_version="v999")


async def test_request_is_well_formed() -> None:
    client = StubClient([verdict_block(passed=True)])
    case = make_case()
    await make_judge(client).score(case, make_transcript())

    # verdict tool is forced, judge can't answer in prose
    assert client.kwargs["tool_choice"]["type"] == "tool"
    # temperature is deprecated on Claude 5 models and must NOT be sent
    assert "temperature" not in client.kwargs
    # the prompt actually contains the task, the rubric, and the transcript
    prompt = client.kwargs["messages"][0]["content"]
    assert case.task_prompt in prompt
    assert case.success_criteria.rubric is not None
    assert case.success_criteria.rubric in prompt
    assert "calculator" in prompt


def test_render_transcript_includes_the_evidence() -> None:
    rendered = make_judge(StubClient([])).render_transcript(make_transcript())
    assert "calculator" in rendered
    assert "2*3" in rendered
    assert "The answer is 6." in rendered
    assert rendered.count("Step") >= 2
    assert "finished" in rendered


async def test_missing_rubric_raises() -> None:

    judge = make_judge(StubClient([verdict_block(passed=True)]))
    with pytest.raises(ValueError):
        await judge.score(make_case(rubric=None), make_transcript())


async def test_truncated_verdict_raises_clear_error() -> None:
    # a max_tokens-truncated tool call parses to a partial dict (here missing
    # 'passed'); must raise a diagnostic, not a cryptic KeyError
    partial = SimpleNamespace(
        type="tool_use", id="toolu_1", name="record-verdict",
        input={"reasoning": "cut off before passed"},  # truncated
    )
    judge = make_judge(StubClient([partial]))
    with pytest.raises(ValueError) as exc:
        await judge.score(make_case(), make_transcript())
    assert "no valid verdict" in str(exc.value)
