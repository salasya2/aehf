
import math

from pydantic import BaseModel

from aehf.core.results import SuiteResult


def mcnemar_test(b : int, c:int) -> float:
    n_d = b + c
    
    if b < 0 or c < 0:
        raise ValueError(f"Invalid values b : {b} , c : {c} for Mcnemar Test" )
    p = 2 * sum(math.comb(n_d, k) for k in range(max(b, c), n_d + 1)) / 2**n_d

    return min(float(p), 1.0)


class ComparisonResult(BaseModel):
    n_cases : int
    a_passed : int
    b_passed : int
    both_pass : int
    both_fail : int
    a_only: int
    b_only: int
    p_value : float

def compare_result(a: SuiteResult, b: SuiteResult) -> ComparisonResult:
    
    n = 0
    a_passed = 0
    b_passed = 0
    both_pass = 0
    both_fail = 0
    a_only = 0
    b_only = 0
    p_value = 0.0


    
    a_by_id = {r.case_id: r for r in a.results}
    b_by_id = {r.case_id: r for r in b.results} 

    if len(a_by_id) != len(b_by_id) or a_by_id.keys() != b_by_id.keys():

        raise ValueError(f"Cases in {a.run_id} don't match that of {b.run_id}")
    

    for id in a_by_id.keys():
        n+=1
        a_case = a_by_id[id]
        b_case = b_by_id[id]
        if not a_case.verdicts and not b_case.verdicts:
            both_fail+=1
                
        elif not a_case.verdicts:
            if not b_case.verdicts[0].passed:
                both_fail+=1
            if b_case.verdicts[0].passed:
                b_passed+=1
                b_only += 1
        elif not b_case.verdicts:
            if not a_case.verdicts[0].passed:
                both_fail+=1
            if a_case.verdicts[0].passed:
                a_passed+=1
                a_only += 1
        elif a_case.verdicts[0].passed and b_case.verdicts[0].passed:
            both_pass += 1
            b_passed += 1
            a_passed += 1
        elif b_case.verdicts[0].passed:
            b_passed+=1
            b_only += 1
        elif a_case.verdicts[0].passed:
            a_passed += 1
            a_only += 1
        else:
            both_fail += 1

    p_value = mcnemar_test(a_only,b_only)

    return ComparisonResult(n_cases = n, a_passed = a_passed, b_passed = b_passed, both_pass = both_pass, both_fail = both_fail, a_only = a_only, b_only = b_only,p_value = p_value)




