"""The one test allowed to touch the network.

Skipped unless ANTHROPIC_API_KEY is set, so CI stays free and offline.
Run locally with:  pytest tests/test_live_anthropic.py -v
"""
import os

import pytest
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from aehf.adapters.anthropic import AnthropicAdapter
from aehf.core.case import EvalCase, ToolSpec
from aehf.core.transcript import Termination
from aehf.tools.mock import mock_provider_factory

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="live test needs ANTHROPIC_API_KEY",
)

CASE = EvalCase(
    id="live-1",
    task_prompt="Use the search tool to find the population of France, then state it.",
    tools=[
        ToolSpec(
            name="search",
            description="Search the web for a fact.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
    ],
    success_criteria={"answer_regex": "68"},
    max_steps=5,
    timeout_seconds=60,
    token_budget=5000,
    tool_fixtures={"search": "France's population is approximately 68 million (2024)."},
)



