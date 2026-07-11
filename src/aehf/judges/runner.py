import asyncio

from aehf.core.case import EvalCase, Suite
from aehf.core.results import CaseResult, SuiteResult, Verdict
from aehf.core.transcript import Transcript
from aehf.judges.base import Judge


async def _bounded_judge_suite(judge:Judge,case:EvalCase, transcript: Transcript,sem: asyncio.Semaphore) -> Verdict:
    async with sem:
        return await judge.score(case,transcript)


async def judge_suite(judge : Judge, suite: Suite, suite_result : SuiteResult, concurrency:int = 5) -> SuiteResult:

    sem = asyncio.Semaphore(concurrency)

    case_results : list[CaseResult] = suite_result.results
    cases : list[EvalCase] = suite.eval
    transcripts : dict[str,Transcript] ={ c.transcript.id:c.transcript  for c in case_results}

    missing = [case.id for case in cases if case.id not in transcripts]
    if missing:
        raise KeyError(f"missing transcript(s) for case id(s): {', '.join(missing)}")

    tasks = [_bounded_judge_suite(judge, case, transcripts[case.id], sem) for case in cases]
    verdict : list[Verdict] = await asyncio.gather(*tasks) 

    judged = [cr.model_copy(update={"verdicts": [verdict[i]]}) for i, cr in enumerate(case_results)]
    
    suite_result = suite_result.model_copy(update = {"results" : judged})
    return suite_result




