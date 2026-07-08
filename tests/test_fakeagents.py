import asyncio

import pytest

from aehf.adapters.fake import FakeAgent
from aehf.core.case import EvalCase
from tests.slowagent import SlowAgent

case = EvalCase(id = "2", task_prompt = "hi", tools = [],success_criteria = {"acc":90},max_steps = 1,timeout_seconds  = 10,token_budget = 10,tool_fixtures = {'search' : "hekko"},)

async def test_fakeagent() -> None:
    fakeAgent = FakeAgent({})

    with pytest.raises(KeyError):
        await fakeAgent.run(case)
    

async def test_slowagent() -> None:
    agent = SlowAgent({})

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(agent.run(case),timeout = 0.05)
    



