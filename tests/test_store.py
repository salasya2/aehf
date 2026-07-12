from pathlib import Path

import pytest

from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Termination, Transcript
from aehf.regression.store import RunNotFoundError, list_runs, load_run, save_run


def make_result(run_id: str = "r1") -> SuiteResult:
    t = Transcript(
        id="a", ordered_steps=[], final_answer="x", total_tokens=1,
        duration_seconds=0.1, termination_reason=Termination.finished,
    )
    v = [Verdict(passed=True, score=1.0, reasoning="r", judge_name="j", version="1")]
    return SuiteResult(
        suite_name="s",
        results=[CaseResult(case_id="a", transcript=t, verdicts=v, run_metadata={})],
        run_id=run_id,
    )


def test_save_load_round_trip(tmp_path : Path) -> None:
    original = make_result()
    save_run(tmp_path, "abc123", "claude-haiku-4-5", "v2", original)
    loaded = load_run(tmp_path, "abc123", "claude-haiku-4-5", "v2")
    assert loaded == original


def test_load_missing_run_raises(tmp_path:Path) -> None:
    with pytest.raises(RunNotFoundError):
        load_run(tmp_path, "nope", "claude-haiku-4-5", "v1")


def test_list_runs_round_trips_realistic_ids(tmp_path:Path) -> None:
    
    save_run(tmp_path, "abc123", "claude-haiku-4-5", "v2", make_result())
    save_run(tmp_path, "def456", "claude-sonnet-5", "v1", make_result())
    assert list_runs(tmp_path) == [
        ("abc123", "claude-haiku-4-5", "v2"),
        ("def456", "claude-sonnet-5", "v1"),
    ]


def test_list_runs_empty_store_is_empty_list(tmp_path : Path) -> None:
    assert list_runs(tmp_path / "does-not-exist") == []
