import asyncio
from pathlib import Path

from aehf.adapters.fake import FakeAgent
from aehf.core.case import EvalCase, SuccessCriteria
from aehf.core.loader import load_suite
from aehf.core.runner import run_suite
from aehf.core.transcript import Termination

case = EvalCase(id = "2", task_prompt = "hi", tools = [],success_criteria = SuccessCriteria(answer_regex = "5", required_tools = ["calculator"],forbidden_tools = []),max_steps = 1,timeout_seconds  = 0.05,token_budget = 10,tool_fixtures = {'search' : "hekko"})

# def test_happy() -> None:
#     suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

#     transcripts = demo_transcripts(suite)
#     agent = FakeAgent(transcripts)

#     suiteresult = asyncio.run(run_suite(agent,suite,5))
#     assert suiteresult.results[0].transcript.id == "1"


# def test_tokens_exceeded() -> None:
#     suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

#     transcripts = demo_transcripts(suite)
#     transcripts["1"] = transcripts["1"].model_copy(update = {"total_tokens": 30000})
#     agent = FakeAgent(transcripts)

#     suiteresult = asyncio.run(run_suite(agent,suite,5))
#     assert suiteresult.results[0].transcript.termination_reason == Termination.budget_exceeded 


def test_missing_id() -> None:

    suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

    agent = FakeAgent({})

    suiteresult = asyncio.run(run_suite(agent,suite,5))
    assert suiteresult.results[0].transcript.termination_reason == Termination.crashed

# async def test_slowagent() -> None:
#     suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

#     transcripts = demo_transcripts(suite)
#     transcripts["1"] = transcripts["1"].model_copy(update = {"total_tokens": 10,"duration_seconds" : 20})
#     agent = SlowAgent(transcripts)

#     caseres = await run_case(agent,case)
#     assert caseres.transcript.termination_reason == Termination.timeout

# def test_max_steps()->None:
#     suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

#     transcripts = demo_transcripts(suite)
#     transcripts["1"] = transcripts["1"].model_copy(update = {"ordered_steps": [Step(model_output="x", tool_calls=None, token_usage=10),Step(model_output="x", tool_calls=None, token_usage=10),Step(model_output="x", tool_calls=None, token_usage=10),Step(model_output="x", tool_calls=None, token_usage=10),Step(model_output="x", tool_calls=None, token_usage=10),Step(model_output="x", tool_calls=None, token_usage=10)]})
#     agent = FakeAgent(transcripts)

#     suiteresult = asyncio.run(run_suite(agent,suite,5))
#     assert suiteresult.results[0].transcript.termination_reason == Termination.max_steps 

# def test_concurrency() -> None:
#     suite = load_suite(Path(__file__).resolve().parents[1] / "examples" / "demo.yaml")

#     transcripts = demo_transcripts(suite)
#     agent = TrackingAgent(transcripts,2)

#     asyncio.run(run_suite(agent,suite,2))

#     assert agent.peak <= 2



