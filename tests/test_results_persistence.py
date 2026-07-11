import json
from pathlib import Path

from aehf.core.results import (
    CaseResult,
    SuiteResult,
    Verdict,
    load_suite_result,
    save_suite_result,
)
from aehf.core.transcript import Step, Termination, ToolCall, Transcript


def make_suite_result() -> SuiteResult:
    # deliberately exercises every model in the tree: nested tool calls,
    # an enum, a verdict, and run_metadata
    transcript = Transcript(
        id="a",
        ordered_steps=[
            Step(
                model_output="using the calculator",
                tool_calls=[ToolCall(toolname="calculator", arguments={"expression": "2*3"}, result="6", latency=0.5)],
                token_usage=50,
            ),
            Step(model_output="the answer is 6", tool_calls=None, token_usage=20),
        ],
        final_answer="6",
        total_tokens=70,
        duration_seconds=1.25,
        termination_reason=Termination.finished,
    )
    verdict = Verdict(passed=True, score=1.0, reasoning="answer matched", judge_name="AssertionJudge", version="1")
    crashed = Transcript(
        id="b",
        ordered_steps=[],
        final_answer="",
        total_tokens=-1,
        duration_seconds=0.1,
        termination_reason=Termination.crashed,
    )
    return SuiteResult(
        suite_name="demo",
        results=[
            CaseResult(case_id="a", transcript=transcript, verdicts=[verdict], run_metadata={}),
            CaseResult(case_id="b", transcript=crashed, verdicts=[], run_metadata={"error_type": "RuntimeError"}),
        ],
        run_id="r1",
    )


def test_round_trip(tmp_path: Path) -> None:
    original = make_suite_result()
    path = tmp_path / "results.json"
    save_suite_result(original, path)
    loaded = load_suite_result(path)
    assert loaded == original  # pydantic models compare by value, whole tree


def test_file_is_plain_json_with_readable_enum(tmp_path: Path) -> None:
    # the file is an interface: humans diff it, future tools parse it.
    # pin that termination_reason serializes as its string value, not
    # an opaque repr — if this fails, revisit how Termination serializes
    path = tmp_path / "results.json"
    save_suite_result(make_suite_result(), path)
    data = json.loads(path.read_text())
    assert data["results"][1]["transcript"]["termination_reason"] == "crashed"
