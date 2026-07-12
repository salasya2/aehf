from aehf.regression.diff import DiffResult
from aehf.reporting.markdown import render_markdown
from aehf.stats.compare import ComparisonResult


def make_diff(
    newly_failing: list[str],
    newly_passing: list[str],
    p_value: float,
    unchanged_pass: int = 10,
    unchanged_fail: int = 5,
) -> DiffResult:
    comparison = ComparisonResult(
        n_cases=unchanged_pass + unchanged_fail + len(newly_failing) + len(newly_passing),
        a_passed=unchanged_pass + len(newly_failing),
        b_passed=unchanged_pass + len(newly_passing),
        both_pass=unchanged_pass,
        both_fail=unchanged_fail,
        a_only=len(newly_failing),
        b_only=len(newly_passing),
        p_value=p_value,
    )
    return DiffResult(
        newly_failing=newly_failing,
        newly_passing=newly_passing,
        unchanged_pass=unchanged_pass,
        unchanged_fail=unchanged_fail,
        comparison=comparison,
    )


def test_significant_regression_shows_regression_header() -> None:
    md = render_markdown(make_diff(["hard-hedged-13", "med-partial-09"], [], p_value=0.01))
    assert "Regression Detected" in md
    assert "No significant" not in md
    assert "hard-hedged-13" in md


def test_failures_but_not_significant_is_not_flagged_regression() -> None:
    # newly failing exists, but McNemar says it's noise -> not a regression
    md = render_markdown(make_diff(["one-case"], [], p_value=0.4))
    assert "No significant" in md


def test_no_changes_returns_early_without_table() -> None:
    md = render_markdown(make_diff([], [], p_value=1.0))
    assert "|" not in md  # no table rendered when nothing changed


def test_table_has_blank_line_before_it() -> None:
    # GitHub won't render a table glued to the paragraph above it
    md = render_markdown(make_diff(["c1"], [], p_value=0.01))
    assert "\n\n|" in md


def test_failing_and_passing_land_in_the_right_rows() -> None:
    md = render_markdown(make_diff(["fail-case"], ["pass-case"], p_value=0.03))
    lines = md.splitlines()
    fail_line = next(line for line in lines if "fail-case" in line)
    pass_line = next(line for line in lines if "pass-case" in line)
    assert "✅→❌" in fail_line
    assert "❌→✅" in pass_line
