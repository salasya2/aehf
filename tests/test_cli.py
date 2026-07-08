# tests/test_cli.py
import pytest
from typer.testing import CliRunner

from aehf.cli import app

runner = CliRunner()


def test_run_malformed_exits_two() -> None:
    result = runner.invoke(app, ["./tests/malformed.yaml", "anthropic", "mock"])
    assert result.exit_code == 2
    assert "malformed.yaml" in result.output


def test_run_missing_file_exits_two() -> None:
    result = runner.invoke(app, ["./tests/demo.yaml", "anthropic", "mock"])
    assert result.exit_code == 2


def test_bad_tools_choice_exits_two() -> None:
    result = runner.invoke(app, ["./tests/happy.yaml", "anthropic", "mcpk"])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_missing_api_key_exits_two(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # load_dotenv would refill the key from .env; neutralize it
    monkeypatch.setattr("aehf.cli.load_dotenv", lambda *a, **k: None)
    result = runner.invoke(app, ["./tests/happy.yaml", "anthropic", "mock"])
    assert result.exit_code == 2
    assert "ANTHROPIC_API_KEY" in result.output
