from pydantic import BaseModel

from aehf.core.transcript import Transcript


class Verdict(BaseModel):
    passed : bool
    score: float | None = None
    reasoning: str
    judge_name: str
    version: str

class CaseResult(BaseModel):
    case_id : int
    transcript : Transcript
    verdicts: list[Verdict]
    run_metadata: dict[str,str]

class SuiteResult(BaseModel):
    suite_name: str
    results: list[CaseResult]
    run_id: str