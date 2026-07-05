from pydantic import BaseModel, ConfigDict

from aehf.core.transcript import Transcript


class Verdict(BaseModel):
    model_config = ConfigDict(frozen=True)
    passed : bool
    score: float | None = None
    reasoning: str
    judge_name: str
    version: str

class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    case_id : str
    transcript : Transcript
    verdicts: list[Verdict]
    run_metadata: dict[str,str]

class SuiteResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    suite_name: str
    results: list[CaseResult]
    run_id: str