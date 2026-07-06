# tests/test_cli.py
from typer.testing import CliRunner

from aehf.cli import app

runner = CliRunner()


def test_run_all_passing_exits_zero() -> None:
    result = runner.invoke(app, ["./tests/happy.yaml"])
    assert result.exit_code == 0
    assert "0 failed" in result.output


def test_run_with_failures_exits_one() -> None:
    result = runner.invoke(app, ["./tests/malformed.yaml"])
    assert result.exit_code == 2        
    assert "malformed.yaml" in result.output

def test_run_missing_file_exits_two() -> None:
    result = runner.invoke(app, ["./tests/demo.yaml"])
    assert result.exit_code == 2         