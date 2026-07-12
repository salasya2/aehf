from pydantic import BaseModel

from aehf.core.results import SuiteResult, case_passed
from aehf.stats.compare import ComparisonResult, compare_result


class DiffResult(BaseModel):
    newly_failing : list[str]
    newly_passing : list[str]
    unchanged_pass : int
    unchanged_fail : int
    comparison : ComparisonResult

def is_regression(diff: DiffResult) -> bool:
    verdict = "significant" if diff.comparison.p_value < 0.05 else "not significant"
    if verdict == "significant" and len(diff.newly_failing) > 0:
        return True
    return False

def diff_runs(base: SuiteResult, head: SuiteResult) -> DiffResult:
    base_by_id = {r.case_id: r for r in base.results}
    head_by_id = {r.case_id: r for r in head.results} 

    if len(base_by_id) != len(head_by_id) or base_by_id.keys() != head_by_id.keys():

        raise ValueError(f"Cases in {base.run_id} don't match that of {head.run_id}")
    unchanged_pass, unchanged_fail = 0,0
    newly_failing,newly_passing = [],[]
    
    for case_id in base_by_id:
        b = case_passed(base_by_id[case_id])
        h = case_passed(head_by_id[case_id])
        if b and h: 
            unchanged_pass += 1
        elif b and not h: 
            newly_failing.append(case_id)
        elif h and not b: 
            newly_passing.append(case_id)
        else: 
            unchanged_fail += 1
        
    comparison = compare_result(base,head)
    return DiffResult(newly_failing = newly_failing, newly_passing =newly_passing, unchanged_pass = unchanged_pass, unchanged_fail = unchanged_fail,comparison = comparison)
        
    
