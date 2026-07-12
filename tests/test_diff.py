import pytest

from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Termination, Transcript
from aehf.regression.diff import diff_runs


def case_result(case_id: str, passed: bool | None) -> CaseResult:
    # passed=None -> no verdicts (crashed before judging); convention: fail
    t = Transcript(
        id=case_id, ordered_steps=[], final_answer="x", total_tokens=1,
        duration_seconds=0.1, termination_reason=Termination.finished,
    )
    verdicts = [] if passed is None else [
        Verdict(passed=passed, score=1.0, reasoning="r", judge_name="j", version="1")
    ]
    return CaseResult(case_id=case_id, transcript=t, verdicts=verdicts, run_metadata={})


def run(outcomes: dict[str, bool | None], run_id: str) -> SuiteResult:
    return SuiteResult(
        suite_name="s",
        results=[case_result(cid, p) for cid, p in outcomes.items()],
        run_id=run_id,
    )


def test_newly_failing_lists_the_regressed_case_id() -> None:
    base = run({"a": True, "b": True}, "base")
    head = run({"a": True, "b": False}, "head")   # b regressed
    d = diff_runs(base, head)
    assert d.newly_failing == ["b"]
    assert d.newly_passing == []
    assert d.unchanged_pass == 1  # a


def test_newly_passing_lists_the_improved_case_id() -> None:
    base = run({"a": False}, "base")
    head = run({"a": True}, "head")   # a improved
    d = diff_runs(base, head)
    assert d.newly_passing == ["a"]
    assert d.newly_failing == []


def test_no_changes_both_lists_empty() -> None:
    base = run({"a": True, "b": False}, "base")
    head = run({"a": True, "b": False}, "head")
    d = diff_runs(base, head)
    assert d.newly_failing == []
    assert d.newly_passing == []
    assert d.unchanged_pass == 1
    assert d.unchanged_fail == 1


def test_comparison_is_populated() -> None:
    # DiffResult must embed the McNemar comparison, not drop it
    base = run({"a": True}, "base")
    head = run({"a": True}, "head")
    d = diff_runs(base, head)
    assert d.comparison.n_cases == 1


def test_empty_verdicts_count_as_fail() -> None:
    # a crashed-before-judging rep in head is a regression, not an IndexError
    base = run({"a": True}, "base")
    head = run({"a": None}, "head")
    d = diff_runs(base, head)
    assert d.newly_failing == ["a"]


def test_mismatched_case_sets_raise() -> None:
    base = run({"a": True, "b": True}, "base")
    head = run({"a": True}, "head")
    with pytest.raises(ValueError):
        diff_runs(base, head)
