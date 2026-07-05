import asyncio
import time
import traceback
from datetime import timedelta
from typing import Any
from uuid import uuid4

from aehf.adapters.base import Agent
from aehf.core.case import EvalCase, Suite
from aehf.core.results import CaseResult, SuiteResult
from aehf.core.transcript import Termination, Transcript


async def run_case(agent: Agent, case:EvalCase) -> CaseResult:
    run_metadata : dict[str,Any] = {}
    start_time = time.monotonic()
    try:
        transcript = await asyncio.wait_for(agent.run(case),timeout = case.timeout_seconds.total_seconds())
        if transcript.total_tokens >case.token_budget:
            transcript = transcript.model_copy(update ={"duration_seconds":timedelta(seconds = time.monotonic()-start_time) ,"termination_reason" : Termination.budget_exceeded})

        if len(transcript.ordered_steps) > case.max_steps:
            transcript = transcript.model_copy(update ={"duration_seconds": timedelta(seconds = time.monotonic()-start_time), "termination_reason" :Termination.max_steps})
    except TimeoutError:
        transcript = Transcript(id = "-1",ordered_steps = [], final_answer ="",total_tokens= -1,duration_seconds = timedelta(seconds = time.monotonic()-start_time),termination_reason = Termination.timeout)
    except Exception as exc:
        transcript = Transcript(id = "-1",ordered_steps = [], final_answer ="",total_tokens= -1,duration_seconds = timedelta(seconds = time.monotonic() - start_time),termination_reason = Termination.crashed)
        run_metadata['error_type'] = type(exc).__name__
        run_metadata['error_message'] = str(exc)
        run_metadata['error_traceback'] = traceback.format_exc()

    case_result = CaseResult(case_id = case.id,transcript = transcript, verdicts = [], run_metadata = run_metadata) 
    return case_result

async def _run_case_bounded(agent:Agent, case:EvalCase, sem:asyncio.Semaphore) -> CaseResult:
    async with sem:
        return await run_case(agent,case)
async def run_suite(agent:Agent, suite:Suite, max_concurrency :int = 5) -> SuiteResult:
    sem = asyncio.Semaphore(max_concurrency)
    
    tasks = [_run_case_bounded(agent,c,sem) for c in suite.eval]
    result = await asyncio.gather(*tasks)
    
    suiteresult = SuiteResult(suite_name = suite.name, results = result,run_id = uuid4().hex[:8])
    return suiteresult
    


