import asyncio
import os
from enum import Enum
from pathlib import Path

import typer
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from aehf.adapters.anthropic import AnthropicAdapter
from aehf.adapters.base import Agent
from aehf.core.loader import SuiteLoadError, load_suite
from aehf.core.runner import run_suite
from aehf.core.transcript import Termination
from aehf.tools.base import ToolProviderFactory
from aehf.tools.mock import mock_provider_factory
from aehf.tools.replay import record_provider_factory, replay_provider_factory

app = typer.Typer()


class AgentChoice(Enum):
    anthropic = "anthropic"
class ToolChoice(Enum):
    mock = "mock"
    record = "record"
    replay = "replay"

def build_agent(agent: AgentChoice, tools : ToolChoice, recordings_dir:Path, model : str, max_tokens:int) -> Agent: 
    
    if tools == ToolChoice.mock:
        factory : ToolProviderFactory = mock_provider_factory
    elif tools  == ToolChoice.record:
        factory  = record_provider_factory(recordings_dir,mock_provider_factory)
    elif tools == ToolChoice.replay:
        factory = replay_provider_factory(recordings_dir)
    else:
        raise ValueError(f"unknown tools choice {tools}")

    if agent == AgentChoice.anthropic:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ANTHROPIC_API_KEY not set")
            raise typer.Exit(2)
        client = AsyncAnthropic(api_key = api_key)
        return AnthropicAdapter(client = client,provider_factory = factory,model = model, max_tokens = max_tokens)
    raise ValueError(f"unknown agent choice {agent}")
    
    
@app.command()
def run(path: Path, agent : AgentChoice, tools: ToolChoice,  concurrency: int = 5, max_tokens : int = 1024, recordings_dir : Path = Path("output/"), model : str = "claude-haiku-4-5-20251001") ->None:
    load_dotenv()
    adapter = build_agent(agent,tools,recordings_dir,model,max_tokens)

    try:
        suite = load_suite(path)
    except (SuiteLoadError, FileNotFoundError) as e:
        print(e)
        raise typer.Exit(2)

    suite_result = asyncio.run(run_suite(adapter,suite,concurrency))
    
    failed = [r for r in suite_result.results if r.transcript.termination_reason != Termination.finished]
    print(f"{len(suite_result.results)} cases: {len(suite_result.results) - len(failed)} completed, {len(failed)} failed") 
    print(f"{'id':<12} {'reason':<16} {'steps':>5} {'tokens':>7} {'secs':>6}")
    for r in suite_result.results:
        t = r.transcript
        
        print(f"{r.case_id:<12} {t.termination_reason.value:<16} {len(t.ordered_steps):>5} {t.total_tokens:>7} {t.duration_seconds:>6.2f}")
    if failed:
        raise typer.Exit(1)
if __name__== "__main__":
    app()
