import pytest

from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Termination, Transcript
from aehf.stats.aggregate import CaseStats, aggregate
from aehf.stats.sampling import wilson_interval

# --- wilson_interval ----------------------------------------------------------

def test_wilson_known_value_8_of_10() -> None:
    lo, hi = wilson_interval(8, 10)
    assert lo == pytest.approx(0.490, abs=1e-3)
    assert hi == pytest.approx(0.943, abs=1e-3)


def test_wilson_perfect_score_is_not_certainty() -> None:
   
    lo, hi = wilson_interval(3, 3)
    assert lo == pytest.approx(0.438, abs=1e-3)
    assert hi == pytest.approx(1.0, abs=1e-3)


def test_wilson_zero_successes() -> None:
    lo, hi = wilson_interval(0, 5)
    assert lo == pytest.approx(0.0, abs=1e-9)
    assert hi == pytest.approx(0.434, abs=1e-3)


def test_wilson_zero_n_raises() -> None:
    with pytest.raises(ValueError):
        wilson_interval(0, 0)




# --- aggregate ----------------------------------------------------------------

def make_case_result(case_id: str, passed: bool | None) -> CaseResult:
    """passed=None -> no verdicts (a rep that crashed before judging)."""
    transcript = Transcript(
        id=case_id,
        ordered_steps=[],
        final_answer="x",
        total_tokens=10,
        duration_seconds=0.1,
        termination_reason=Termination.finished if passed is not None else Termination.crashed,
    )
    verdicts = [] if passed is None else [
        Verdict(passed=passed, score=1.0 if passed else 0.0, reasoning="r", judge_name="AssertionJudge", version="1")
    ]
    return CaseResult(case_id=case_id, transcript=transcript, verdicts=verdicts, run_metadata={})


def make_run(run_id: str, outcomes: dict[str, bool | None]) -> SuiteResult:
    return SuiteResult(
        suite_name="s",
        results=[make_case_result(cid, p) for cid, p in outcomes.items()],
        run_id=run_id,
    )


def stats_by_id(runs: list[SuiteResult]) -> dict[str, CaseStats]:
    return {s.case_id: s for s in aggregate(runs)}


def test_aggregate_all_pass_is_stable() -> None:
    runs = [make_run(f"r{i}", {"a": True}) for i in range(3)]
    s = stats_by_id(runs)["a"]
    assert s.n == 3
    assert s.passes == 3
    assert s.pass_rate == 1.0
    assert not s.flaky
    assert s.ci_low == pytest.approx(0.438, abs=1e-3)  # ties to the wilson 3/3 vector


def test_aggregate_mixed_is_flaky() -> None:
    runs = [make_run("r1", {"a": True}), make_run("r2", {"a": False}), make_run("r3", {"a": False})]
    s = stats_by_id(runs)["a"]
    assert s.passes == 1
    assert s.flaky


def test_aggregate_groups_by_case() -> None:
    runs = [make_run("r1", {"a": True, "b": False}), make_run("r2", {"a": True, "b": True})]
    by_id = stats_by_id(runs)
    assert by_id["a"].passes == 2
    assert by_id["b"].passes == 1
    assert by_id["b"].flaky


def test_aggregate_empty_verdicts_counts_as_fail() -> None:
    # a rep that crashed before judging is an OUTCOME (fail), not missing
    # data: it stays in n and counts as a fail
    runs = [make_run("r1", {"a": True}), make_run("r2", {"a": None})]
    s = stats_by_id(runs)["a"]
    assert s.n == 2
    assert s.passes == 1
    assert s.flaky


def test_aggregate_mismatched_case_sets_raise() -> None:
    # run 2 silently dropped case b: that would skew b's n and CI without
    # warning — harness misconfiguration, fail loud
    runs = [make_run("r1", {"a": True, "b": True}), make_run("r2", {"a": True})]
    with pytest.raises(ValueError):
        aggregate(runs)


# --- mcnemar / compare_result ---------------------------------------------------

from aehf.stats.compare import compare_result, mcnemar_test  # noqa: E402


def test_mcnemar_known_value() -> None:
    # b=8, c=2: p = 2*(C(10,8)+C(10,9)+C(10,10))/1024 = 112/1024 exactly
    assert mcnemar_test(8, 2) == pytest.approx(0.109375)


def test_mcnemar_balanced_discordance_is_one() -> None:
    # b == c is the least evidence of difference possible: p must be
    # exactly 1.0, not >1 (two-sided doubling requires a clamp)
    assert mcnemar_test(5, 5) == pytest.approx(1.0)


def test_mcnemar_no_discordant_pairs_is_one() -> None:
    # the two conditions never disagreed: no evidence of difference
    assert mcnemar_test(0, 0) == pytest.approx(1.0)


def test_mcnemar_lopsided_is_significant() -> None:
    assert mcnemar_test(15, 1) < 0.05


def test_mcnemar_negative_raises() -> None:
    with pytest.raises(ValueError):
        mcnemar_test(-1, 3)


def test_compare_counts_and_pairing() -> None:
    # a passes {x, y, z}, fails {w}; b passes {x, w}, fails {y, z}
    # -> both_pass=1 (x), both_fail=0, a_only=2 (y,z), b_only=1 (w)
    a = make_run("ra", {"x": True, "y": True, "z": True, "w": False})
    b = make_run("rb", {"x": True, "y": False, "z": False, "w": True})
    r = compare_result(a, b)
    assert r.n_cases == 4
    assert r.a_passed == 3
    assert r.b_passed == 2
    assert r.both_pass == 1
    assert r.both_fail == 0
    assert r.a_only == 2
    assert r.b_only == 1
    assert r.p_value == pytest.approx(mcnemar_test(2, 1))


def test_compare_missing_verdicts_count_as_fail() -> None:
    # a crashed-before-judging rep is a fail, same convention as aggregate
    a = make_run("ra", {"x": None})
    b = make_run("rb", {"x": True})
    r = compare_result(a, b)
    assert r.b_only == 1
    assert r.a_passed == 0


def test_compare_mismatched_case_sets_raise() -> None:
    a = make_run("ra", {"x": True, "y": True})
    b = make_run("rb", {"x": True})
    with pytest.raises(ValueError):
        compare_result(a, b)
