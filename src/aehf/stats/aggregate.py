from pydantic import BaseModel

from aehf.core.results import CaseResult, SuiteResult, case_passed
from aehf.stats.sampling import wilson_interval


class CaseStats(BaseModel):
    case_id : str
    n : int
    passes :int
    pass_rate: float
    ci_low :float
    ci_high: float
    flaky:bool

def aggregate(runs: list[SuiteResult]) -> list[CaseStats]:
    if not runs:
        raise ValueError("aggregate needs at least one run")

    # every run must cover the same cases, each exactly once — a partial
    # results file would silently skew that case's n and CI
    expected = {c.case_id for c in runs[0].results}
    for sr in runs:
        ids = [c.case_id for c in sr.results]
        if set(ids) != expected or len(ids) != len(expected):
            missing = expected - set(ids)
            extra = set(ids) - expected
            raise ValueError(
                f"run {sr.run_id!r} case set mismatch: missing={sorted(missing)} extra={sorted(extra)}"
            )

    case_results : dict[str,list[CaseResult]]= {c.case_id: [] for c in runs[0].results}

    for sr in runs:
        for c in sr.results:
            case_results[c.case_id].append(c)
    result : list[CaseStats] = []
    for case_id in case_results.keys():
        samples = case_results[case_id]
        n = len(samples)
        passes = sum(case_passed(c) for c in samples)
        
        pass_rate = passes/n
        ci_low,ci_high = wilson_interval(passes,n)
        flaky = 0 < passes < n

        result.append(CaseStats(case_id = case_id,n = n, passes = passes,pass_rate=pass_rate,ci_low = ci_low,ci_high = ci_high,flaky = flaky))
    return result

