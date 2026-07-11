import pytest

from aehf.core.case import EvalCase, SuccessCriteria, Suite
from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Step, Termination, Transcript
from aehf.judges.assertionjudge import AssertionJudge
from aehf.judges.runner import judge_suite


def make_case(case_id: str, answer_regex: str) -> EvalCase:
    return EvalCase(
        id=case_id,
        task_prompt="q",
        tools=[],
        success_criteria=SuccessCriteria(answer_regex=answer_regex),
        max_steps=5,
        timeout_seconds=30,
        token_budget=1000,
    )


def make_result(case_id: str, final_answer: str) -> CaseResult:
    transcript = Transcript(
        id=case_id,
        ordered_steps=[Step(model_output=final_answer, tool_calls=None, token_usage=10)],
        final_answer=final_answer,
        total_tokens=10,
        duration_seconds=0.1,
        termination_reason=Termination.finished,
    )
    return CaseResult(case_id=case_id, transcript=transcript, verdicts=[], run_metadata={})


# case "a" should pass (answer matches its regex), case "b" should fail
SUITE = Suite(name="s", eval=[make_case("a", "^yes$"), make_case("b", "^no$")])


def fresh_suite_result() -> SuiteResult:
    return SuiteResult(
        suite_name="s",
        results=[make_result("a", "yes"), make_result("b", "maybe")],
        run_id="r1",
    )


async def test_judge_suite_fills_verdicts() -> None:
    judged = await judge_suite(AssertionJudge(), SUITE, fresh_suite_result())
    assert len(judged.results) == 2
    for result in judged.results:
        assert len(result.verdicts) == 1
        # model_copy(update=...) does not validate: this catches a bare
        # Verdict (or anything else) stuffed into the list field
        assert isinstance(result.verdicts[0], Verdict)


async def test_judge_suite_does_not_mutate_input() -> None:
    original = fresh_suite_result()
    judged = await judge_suite(AssertionJudge(), SUITE, original)
    for result in original.results:
        assert result.verdicts == []
    for result in judged.results:
        assert len(result.verdicts) == 1


async def test_verdicts_land_on_the_right_case() -> None:
    judged = await judge_suite(AssertionJudge(), SUITE, fresh_suite_result())
    by_id = {r.case_id: r for r in judged.results}
    assert by_id["a"].verdicts[0].passed
    assert not by_id["b"].verdicts[0].passed


async def test_missing_transcript_for_case_raises() -> None:
    # suite has cases a and b, but results only cover a: harness misconfig.
    # ponytail: raw KeyError today; upgrade to a named error carrying the
    # case id if operators need friendlier output
    partial = SuiteResult(suite_name="s", results=[make_result("a", "yes")], run_id="r1")
    with pytest.raises(KeyError):
        await judge_suite(AssertionJudge(), SUITE, partial)


async def test_rejudging_replaces_not_appends() -> None:
    once = await judge_suite(AssertionJudge(), SUITE, fresh_suite_result())
    twice = await judge_suite(AssertionJudge(), SUITE, once)
    for result in twice.results:
        assert len(result.verdicts) == 1
