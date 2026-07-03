from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import timedelta
from aehf.core.transcript import Transcript

class Verdict(BaseModel):
    passed : bool
    score: Optional[float]
    reasoning: str
    judge_name: str
    version: str

class CaseResult(BaseModel):
    case_id : int
    transcript : Transcript
    verdicts: List[Verdict]
    run_metadata: Dict

class SuiteResult(BaseModel):
    suite_name: str
    results: List[CaseResult]
    run_id: str