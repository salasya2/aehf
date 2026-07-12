# tests/test_cli.py
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aehf.cli import app
from aehf.core.case import EvalCase, SuccessCriteria
from aehf.core.transcript import Step, Termination, Transcript
from aehf.judges.calibration import LabeledTranscript, save_labeled

runner = CliRunner()


# --- run command -------------------------------------------------------------
# NOTE: with more than one @app.command(), typer requires the subcommand name
# as the first arg ("run"/"calibrate"). Without it you test command parsing,
# not the command.

def test_run_malformed_exits_two() -> None:
    result = runner.invoke(app, ["run", "./tests/malformed.yaml", "anthropic", "mock"])
    assert result.exit_code == 2
    assert "malformed.yaml" in result.output


def test_run_missing_file_exits_two() -> None:
    result = runner.invoke(app, ["run", "./tests/demo.yaml", "anthropic", "mock"])
    assert result.exit_code == 2


def test_bad_tools_choice_exits_two() -> None:
    result = runner.invoke(app, ["run", "./tests/happy.yaml", "anthropic", "mcpk"])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_missing_api_key_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # load_dotenv would refill the key from .env; neutralize it
    monkeypatch.setattr("aehf.cli.load_dotenv", lambda *a, **k: None)
    result = runner.invoke(app, ["run", "./tests/happy.yaml", "anthropic", "mock"])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output


# --- calibrate command -------------------------------------------------------
# uses the assertion judge exclusively: fully offline, deterministic, no key.

def make_labeled(final_answer: str, human_label: bool) -> LabeledTranscript:
    case = EvalCase(
        id="c",
        task_prompt="What is 2*3?",
        tools=[],
        success_criteria=SuccessCriteria(answer_regex="^6$"),
        max_steps=5,
        timeout_seconds=30,
        token_budget=1000,
    )
    transcript = Transcript(
        id="c",
        ordered_steps=[Step(model_output=final_answer, tool_calls=None, token_usage=10)],
        final_answer=final_answer,
        total_tokens=10,
        duration_seconds=0.1,
        termination_reason=Termination.finished,
    )
    return LabeledTranscript(case=case, transcript=transcript, human_label=human_label)


def test_calibrate_reports_kappa(tmp_path: Path) -> None:
    # judge agrees with the human on both: "6" passes & labeled pass,
    # "7" fails & labeled fail -> perfect agreement
    path = tmp_path / "labels.jsonl"
    save_labeled([make_labeled("6", True), make_labeled("7", False)], path)
    result = runner.invoke(app, ["calibrate", str(path), "assertion"])
    assert result.exit_code == 0
    assert "cohen kappa" in result.output
    assert "records : 2" in result.output


def test_calibrate_dumps_disagreements(tmp_path: Path) -> None:
    # judge passes "6" (regex matches) but this record is labeled FAIL:
    # a forced disagreement the dump must surface by case id
    path = tmp_path / "labels.jsonl"
    record = make_labeled("6", human_label=False)
    save_labeled([record.model_copy(update={"case": record.case.model_copy(update={"id": "disputed-1"})})], path)
    result = runner.invoke(app, ["calibrate", str(path), "assertion"])
    assert result.exit_code == 0
    assert "DISAGREEMENTS (1)" in result.output
    assert "disputed-1" in result.output
    assert "human=FAIL judge=PASS" in result.output


def test_calibrate_missing_file_exits_two() -> None:
    result = runner.invoke(app, ["calibrate", "./tests/nope.jsonl", "assertion"])
    assert result.exit_code == 2


def test_calibrate_malformed_file_exits_two(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{not valid json\n")
    result = runner.invoke(app, ["calibrate", str(path), "assertion"])
    assert result.exit_code == 2


def test_calibrate_empty_file_exits_two(tmp_path: Path) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    result = runner.invoke(app, ["calibrate", str(path), "assertion"])
    assert result.exit_code == 2


# --- compare command ---------------------------------------------------------
from aehf.core.results import (  # noqa: E402
    CaseResult,
    SuiteResult,
    Verdict,
    save_suite_result,
)


def _run_file(tmp_path: Path, name: str, outcomes: dict[str, bool]) -> Path:
    results = []
    for cid, passed in outcomes.items():
        t = Transcript(
            id=cid, ordered_steps=[], final_answer="x", total_tokens=1,
            duration_seconds=0.1, termination_reason=Termination.finished,
        )
        v = [Verdict(passed=passed, score=1.0, reasoning="r", judge_name="j", version="1")]
        results.append(CaseResult(case_id=cid, transcript=t, verdicts=v, run_metadata={}))
    path = tmp_path / name
    save_suite_result(SuiteResult(suite_name="s", results=results, run_id=name), path)
    return path


def test_compare_not_significant(tmp_path: Path) -> None:
    # only 3 cases differ, evenly -> p high -> not significant
    a = _run_file(tmp_path, "a.json", {"x": True, "y": True, "z": False})
    b = _run_file(tmp_path, "b.json", {"x": True, "y": False, "z": True})
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 0
    assert "not significant" in result.output


def test_compare_significant(tmp_path: Path) -> None:
    # A passes all 12, B fails all 12 -> b=12, c=0 -> p tiny -> significant.
    # guards against the verdict string being hardcoded to "not significant"
    cases = {f"c{i}": True for i in range(12)}
    a = _run_file(tmp_path, "a.json", cases)
    b = _run_file(tmp_path, "b.json", {k: False for k in cases})
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 0
    assert "significant" in result.output
    assert "not significant" not in result.output


def test_compare_mismatched_cases_exits_two(tmp_path: Path) -> None:
    a = _run_file(tmp_path, "a.json", {"x": True})
    b = _run_file(tmp_path, "b.json", {"y": True})
    result = runner.invoke(app, ["compare", str(a), str(b)])
    assert result.exit_code == 2


# --- run --n-samples (stubbed adapter, offline) ------------------------------

def test_run_n_samples_prints_aggregate_table(monkeypatch: pytest.MonkeyPatch) -> None:
    # stub the adapter so no API is hit; the mock tool judge (assertion) runs
    # for real over the tiny happy.yaml suite. exercises the n>1 aggregate path
    # that previously crashed on a chained format spec.
    async def fake_run(self: object, case: EvalCase) -> Transcript:
        return Transcript(
            id=case.id, ordered_steps=[Step(model_output="6", tool_calls=None, token_usage=1)],
            final_answer="6", total_tokens=1, duration_seconds=0.1,
            termination_reason=Termination.finished,
        )
    monkeypatch.setattr("aehf.adapters.anthropic.AnthropicAdapter.run", fake_run)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key")
    result = runner.invoke(app, ["run", "./tests/happy.yaml", "anthropic", "mock", "--n-samples", "3"])
    assert result.exit_code == 0, result.output
    assert "flaky" in result.output  # the aggregate-table header rendered
    assert "95% CI" in result.output


def test_run_store_writes_to_store_layout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def fake_run(self: object, case: EvalCase) -> Transcript:
        return Transcript(
            id=case.id, ordered_steps=[Step(model_output="6", tool_calls=None, token_usage=1)],
            final_answer="6", total_tokens=1, duration_seconds=0.1,
            termination_reason=Termination.finished,
        )
    monkeypatch.setattr("aehf.adapters.anthropic.AnthropicAdapter.run", fake_run)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "stub-key")
    monkeypatch.setenv("GITHUB_SHA", "deadbeef")  # pin the sha so the path is known
    store = tmp_path / "store"
    result = runner.invoke(app, [
        "run", "./tests/happy.yaml", "anthropic", "mock",
        "--store", str(store), "--model", "m", "--prompt-version", "v1",
    ])
    assert result.exit_code == 0, result.output
    # the run is loadable back through the store's own key scheme
    from aehf.regression.store import load_run
    loaded = load_run(store, "deadbeef", "m", "v1")
    assert loaded.results  # a real SuiteResult round-tripped


# --- diff command ------------------------------------------------------------
from aehf.regression.store import save_run  # noqa: E402


def _store_run(store: Path, sha: str, outcomes: dict[str, bool]) -> None:
    results = []
    for cid, passed in outcomes.items():
        t = Transcript(
            id=cid, ordered_steps=[], final_answer="x", total_tokens=1,
            duration_seconds=0.1, termination_reason=Termination.finished,
        )
        v = [Verdict(passed=passed, score=1.0, reasoning="r", judge_name="j", version="1")]
        results.append(CaseResult(case_id=cid, transcript=t, verdicts=v, run_metadata={}))
    sr = SuiteResult(suite_name="s", results=results, run_id=sha)
    save_run(store, sha, "m", "v1", sr)


def test_diff_significant_regression_exits_one(tmp_path: Path) -> None:
    # base passes 12, head fails all 12 -> 12 newly failing, p tiny -> exit 1
    cases = {f"c{i}": True for i in range(12)}
    _store_run(tmp_path, "base", cases)
    _store_run(tmp_path, "head", {k: False for k in cases})
    result = runner.invoke(app, ["diff", "base", "head", "--store", str(tmp_path), "--model", "m"])
    assert result.exit_code == 1
    assert "c0" in result.output  # a regressed case is named in the printed scorecard


def test_diff_no_significant_change_exits_zero(tmp_path: Path) -> None:
    # only one case flips each way -> not significant -> exit 0
    _store_run(tmp_path, "base", {"x": True, "y": True, "z": False})
    _store_run(tmp_path, "head", {"x": True, "y": False, "z": True})
    result = runner.invoke(app, ["diff", "base", "head", "--store", str(tmp_path), "--model", "m"])
    assert result.exit_code == 0


def test_diff_writes_scorecard_file(tmp_path: Path) -> None:
    _store_run(tmp_path, "base", {"x": True})
    _store_run(tmp_path, "head", {"x": True})
    out = tmp_path / "scorecard.md"
    result = runner.invoke(app, ["diff", "base", "head", "--store", str(tmp_path), "--model", "m", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_diff_missing_run_exits_two(tmp_path: Path) -> None:
    _store_run(tmp_path, "base", {"x": True})
    # head never stored
    result = runner.invoke(app, ["diff", "base", "head", "--store", str(tmp_path), "--model", "m"])
    assert result.exit_code == 2


def test_diff_mismatched_case_sets_exits_two(tmp_path: Path) -> None:
    _store_run(tmp_path, "base", {"x": True, "y": True})
    _store_run(tmp_path, "head", {"x": True})  # missing y
    result = runner.invoke(app, ["diff", "base", "head", "--store", str(tmp_path), "--model", "m"])
    assert result.exit_code == 2


# --- label command (interactive, driven via stdin) ---------------------------
from aehf.judges.calibration import LabeledTranscript, load_labeled  # noqa: E402


def _labeled(case_id: str, human_label: bool, note: str) -> LabeledTranscript:
    case = EvalCase(
        id=case_id, task_prompt="q", tools=[],
        success_criteria=SuccessCriteria(rubric="answer is 6"),
        max_steps=5, timeout_seconds=30, token_budget=1000,
    )
    t = Transcript(
        id=case_id, ordered_steps=[Step(model_output="6", tool_calls=None, token_usage=1)],
        final_answer="6", total_tokens=1, duration_seconds=0.1,
        termination_reason=Termination.finished,
    )
    return LabeledTranscript(case=case, transcript=t, human_label=human_label, note=note)


def test_label_updates_records(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    save_labeled([_labeled("a", True, "provisional:assertion"),
                  _labeled("b", True, "provisional:assertion")], path)
    # rec a -> fail with note "wrong"; rec b -> pass with note "correct"
    result = runner.invoke(app, ["label", str(path)], input="f\nwrong\np\ncorrect\n")
    assert result.exit_code == 0
    records = load_labeled(path)
    assert records[0].human_label is False and records[0].note == "wrong"
    assert records[1].human_label is True and records[1].note == "correct"


def test_label_quit_preserves_earlier_edits(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    save_labeled([_labeled("a", True, "provisional:assertion"),
                  _labeled("b", True, "provisional:assertion")], path)
    # label a, then quit before b -> a saved, b untouched
    result = runner.invoke(app, ["label", str(path)], input="f\nwrong\nq\n")
    assert result.exit_code == 0
    records = load_labeled(path)
    assert records[0].human_label is False and records[0].note == "wrong"
    assert records[1].note == "provisional:assertion"  # b never reached


def test_label_skip_leaves_record_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    save_labeled([_labeled("a", True, "provisional:assertion")], path)
    result = runner.invoke(app, ["label", str(path)], input="s\n")
    assert result.exit_code == 0
    assert load_labeled(path)[0].note == "provisional:assertion"
