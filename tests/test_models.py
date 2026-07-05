from datetime import timedelta

from pydantic import BaseModel

from aehf.core.case import EvalCase, Suite, ToolSpec
from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Step, Termination, ToolCall, Transcript


def roundtrip(model: BaseModel) -> None:
    restored = type(model).model_validate_json(model.model_dump_json())
    assert restored == model


TOOLCALL = ToolCall(
    toolname="calculator",
    arguments={"expression": "2*3", "precision": 2},
    result="6",
    error_flag=None,
    latency=203.5,
)

TRANSCRIPT = Transcript(
    id=1,
    ordered_steps=[
        Step(model_output="calling calculator", tool_calls=[TOOLCALL], token_usage=75),
        Step(model_output="the answer is 6", tool_calls=None, token_usage=25),
    ],
    final_answer="6",
    total_tokens=100,
    duration_seconds=timedelta(seconds=12.5),
    termination_reason=Termination.finished,
)

EVALCASE = EvalCase(
    id=1,
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
    success_criteria={"answer_regex": "6"},
    max_steps=5,
    timeout_seconds=timedelta(seconds=30),
    token_budget=1000,
)

VERDICT = Verdict(
    passed=True,
    score=0.9,
    reasoning="Final answer matches expected value",
    judge_name="assertion",
    version="1",
)


def test_transcript_models_roundtrip() -> None:
    roundtrip(TOOLCALL)
    roundtrip(TRANSCRIPT)


def test_case_models_roundtrip() -> None:
    roundtrip(EVALCASE)
    roundtrip(Suite(name="demo", eval=[EVALCASE]))


def test_results_models_roundtrip() -> None:
    result = CaseResult(
        case_id=1,
        transcript=TRANSCRIPT,
        verdicts=[VERDICT],
        run_metadata={"model": "claude-haiku-4-5", "git_sha": "abc123"},
    )
    roundtrip(result)
    roundtrip(SuiteResult(suite_name="demo", results=[result], run_id="run-001"))
