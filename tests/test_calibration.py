from pathlib import Path

import pytest

from aehf.core.case import EvalCase, SuccessCriteria, Suite
from aehf.core.results import CaseResult, SuiteResult
from aehf.core.transcript import Step, Termination, Transcript
from aehf.core.transcript import Termination as _Term
from aehf.core.transcript import Transcript as _T
from aehf.judges.calibration import (
    LabeledTranscript,
    LabelLoadError,
    cohen_kappa,
    export_unlabeled,
    load_labeled,
    save_labeled,
)


def make_labeled(case_id: str, human_label: bool) -> LabeledTranscript:
    case = EvalCase(
        id=case_id,
        task_prompt="q",
        tools=[],
        success_criteria=SuccessCriteria(rubric="answer is 6"),
        max_steps=5,
        timeout_seconds=30,
        token_budget=1000,
    )
    transcript = Transcript(
        id=case_id,
        ordered_steps=[Step(model_output="6", tool_calls=None, token_usage=10)],
        final_answer="6",
        total_tokens=10,
        duration_seconds=0.1,
        termination_reason=Termination.finished,
    )
    return LabeledTranscript(case=case, transcript=transcript, human_label=human_label, note="ok")


def test_labeled_round_trip(tmp_path: Path) -> None:
    records = [make_labeled("a", True), make_labeled("b", False)]
    path = tmp_path / "labels.jsonl"
    save_labeled(records, path)
    assert load_labeled(path) == records


def test_load_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    save_labeled([make_labeled("a", True)], path)
    # editors add trailing newlines; a stray blank line must not crash loading
    path.write_text(path.read_text() + "\n\n")
    assert len(load_labeled(path)) == 1


def test_malformed_line_raises_with_line_number(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    good = make_labeled("a", True).model_dump_json()
    path.write_text(good + "\n" + "{not valid json\n")
    with pytest.raises(LabelLoadError) as exc:
        load_labeled(path)
    assert "line 2" in str(exc.value)


def test_perfect_agreement_is_one() -> None:
    judge = [True, False, True, False]
    human = [True, False, True, False]
    assert cohen_kappa(judge, human) == pytest.approx(1.0)


def test_perfect_disagreement_is_minus_one() -> None:
    judge = [True, False]
    human = [False, True]
    assert cohen_kappa(judge, human) == pytest.approx(-1.0)


def test_hand_computed_table() -> None:
    # 2x2 table: a=20 (both pass), b=5 (judge pass/human fail),
    #            c=10 (judge fail/human pass), d=15 (both fail), n=50
    # p_o = 35/50 = 0.7
    # p_e = (25*30 + 25*20) / 2500 = (750 + 500)/2500 = 0.5
    # kappa = (0.7 - 0.5) / (1 - 0.5) = 0.4
    judge = [True] * 20 + [True] * 5 + [False] * 10 + [False] * 15
    human = [True] * 20 + [False] * 5 + [True] * 10 + [False] * 15
    assert cohen_kappa(judge, human) == pytest.approx(0.4, abs=1e-4)


def test_always_pass_judge_scores_zero_despite_high_agreement() -> None:
    # THE reason kappa exists: a judge that blindly says "pass" agrees with
    # the human 90% of the time here, but kappa correctly scores it 0 —
    # no better than chance given the base rates
    judge = [True] * 100
    human = [True] * 90 + [False] * 10
    raw_agreement = sum(j == h for j, h in zip(judge, human)) / 100
    assert raw_agreement == 0.9
    assert cohen_kappa(judge, human) == pytest.approx(0.0)


def test_both_raters_constant_and_agreeing() -> None:
    # p_e == 1 makes the formula 0/0. Pinned behavior: perfect agreement
    # between constant raters is 1.0, not a ZeroDivisionError.
    assert cohen_kappa([True, True, True], [True, True, True]) == pytest.approx(1.0)


def test_mismatched_lengths_raise() -> None:
    with pytest.raises(ValueError):
        cohen_kappa([True, False], [True])


def test_empty_raises() -> None:
    with pytest.raises(ValueError):
        cohen_kappa([], [])


def test_export_crashed_case_defaults_to_fail(tmp_path: Path) -> None:
    # a case that crashed before judging has no verdicts; export must not
    # IndexError on verdicts[0] — it provisionally labels it fail
    case = EvalCase(
        id="a", task_prompt="q", tools=[],
        success_criteria=SuccessCriteria(rubric="x"),
        max_steps=5, timeout_seconds=30, token_budget=1000,
    )
    transcript = _T(
        id="a", ordered_steps=[], final_answer="", total_tokens=-1,
        duration_seconds=0.1, termination_reason=_Term.crashed,
    )
    sr = SuiteResult(
        suite_name="s",
        results=[CaseResult(case_id="a", transcript=transcript, verdicts=[], run_metadata={})],
        run_id="r1",
    )
    records = export_unlabeled(Suite(name="s", eval=[case]), sr)
    assert len(records) == 1
    assert records[0].human_label is False
