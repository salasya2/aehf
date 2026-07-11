from pathlib import Path

import pytest

from aehf.core.case import EvalCase, SuccessCriteria, ToolSpec
from aehf.tools.mock import MockToolProvider, mock_provider_factory
from aehf.tools.replay import (
    ReplayMissError,
    ReplayToolProvider,
    record_provider_factory,
    replay_provider_factory,
)

EVALCASE = EvalCase(
    id="1",
    task_prompt="What is 2*3?",
    tools=[
        ToolSpec(
            name="calculator",
            description="Evaluates arithmetic expressions",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        )
    ],
    success_criteria=SuccessCriteria(answer_regex = "6",required_tools = ["calculator"],forbidden_tools = []),
    max_steps=5,
    timeout_seconds=20,
    token_budget=1000,
    tool_fixtures={"search": "hekko"},
)


async def test_record_delegates_and_persists(tmp_path: Path) -> None:
    provider = record_provider_factory(tmp_path, mock_provider_factory)(EVALCASE)
    result = await provider.execute("search", {"q": "france"})
    assert result == "hekko"
    assert (tmp_path / "1.json").exists()


async def test_replay_round_trip(tmp_path: Path) -> None:
    recorder = record_provider_factory(tmp_path, mock_provider_factory)(EVALCASE)
    await recorder.execute("search", {"q": "france"})

    replayer = replay_provider_factory(tmp_path)(EVALCASE)
    assert await replayer.execute("search", {"q": "france"}) == "hekko"


async def test_key_is_canonical(tmp_path: Path) -> None:
    # same args in a different order must hit the same recording
    recorder = record_provider_factory(tmp_path, mock_provider_factory)(EVALCASE)
    await recorder.execute("search", {"a": 1, "b": 2})

    replayer = replay_provider_factory(tmp_path)(EVALCASE)
    assert await replayer.execute("search", {"b": 2, "a": 1}) == "hekko"


async def test_replay_miss_raises(tmp_path: Path) -> None:
    recorder = record_provider_factory(tmp_path, mock_provider_factory)(EVALCASE)
    await recorder.execute("search", {"q": "france"})

    replayer = replay_provider_factory(tmp_path)(EVALCASE)
    with pytest.raises(ReplayMissError):
        await replayer.execute("search", {"q": "germany"})  # different args = miss


def test_missing_recording_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        replay_provider_factory(tmp_path / "nowhere")(EVALCASE)


def test_invalid_mode_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ReplayToolProvider(tmp_path / "1.json", mode="reply")


def test_record_without_inner_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ReplayToolProvider(tmp_path / "1.json", mode="record")


def test_replay_with_inner_raises(tmp_path: Path) -> None:
    (tmp_path / "1.json").write_text("{}")
    with pytest.raises(ValueError):
        ReplayToolProvider(tmp_path / "1.json", mode="replay", inner=MockToolProvider({}))
