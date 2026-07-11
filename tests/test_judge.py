from aehf.core.case import EvalCase, SuccessCriteria, ToolSpec
from aehf.core.transcript import Step, Termination, ToolCall, Transcript
from aehf.judges.assertionjudge import AssertionJudge

case = EvalCase(
    id="1",
    task_prompt="What is 2*3?",
    tools=[
        ToolSpec(
            name="calculator",
            description="Evaluates arithmetic expressions",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        )
    ],
    success_criteria=SuccessCriteria(answer_regex="6", required_tools=["calculator"], forbidden_tools=["search"]),
    max_steps=5,
    timeout_seconds=20,
    token_budget=1000,
    tool_fixtures={"search": "hekko"},
)


def make_transcript(final_answer: str, tool_calls: list[ToolCall] | None) -> Transcript:
    return Transcript(
        id="1",
        ordered_steps=[
            Step(model_output="working...", tool_calls=tool_calls, token_usage=75),
            Step(model_output=f"the answer is {final_answer}", tool_calls=None, token_usage=25),
        ],
        final_answer=final_answer,
        total_tokens=100,
        duration_seconds=12.5,
        termination_reason=Termination.finished,
    )


def make_call(toolname: str) -> ToolCall:
    return ToolCall(toolname=toolname, arguments={"abt": "any"}, result="6", latency=2.0)


async def test_all_criteria_met() -> None:
    verdict = await AssertionJudge().score(case, make_transcript("6", [make_call("calculator")]))
    assert verdict.passed
    assert verdict.score == 1.0


async def test_no_required_toolcall() -> None:
    verdict = await AssertionJudge().score(case, make_transcript("6", None))
    assert not verdict.passed
    assert verdict.score == 0.0
    assert "required tool(s) not called: calculator" in verdict.reasoning


async def test_forbidden_toolcall() -> None:
    verdict = await AssertionJudge().score(case, make_transcript("6", [make_call("search")]))
    assert not verdict.passed
    assert "forbidden tool(s) called: search" in verdict.reasoning


async def test_forbidden_tool_called_twice_reported_once() -> None:
    verdict = await AssertionJudge().score(case, make_transcript("6", [make_call("search"), make_call("search")]))
    assert verdict.reasoning.count("forbidden tool(s) called") == 1


async def test_wrong_answer() -> None:
    verdict = await AssertionJudge().score(case, make_transcript("7", [make_call("calculator")]))
    assert not verdict.passed
    assert "answer did not match" in verdict.reasoning


async def test_no_criteria_passes() -> None:
    empty_case = case.model_copy(update={"success_criteria": SuccessCriteria()})
    verdict = await AssertionJudge().score(empty_case, make_transcript("anything", None))
    assert verdict.passed
    assert verdict.reasoning == "no criteria specified"


def test_invalid_regex_rejected_at_model_time() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SuccessCriteria(answer_regex="[")
