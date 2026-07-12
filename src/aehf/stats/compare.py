
import math

from pydantic import BaseModel

from aehf.core.results import SuiteResult, case_passed


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
    


    
    a_by_id = {r.case_id: r for r in a.results}
    b_by_id = {r.case_id: r for r in b.results} 

    if len(a_by_id) != len(b_by_id) or a_by_id.keys() != b_by_id.keys():

        raise ValueError(f"Cases in {a.run_id} don't match that of {b.run_id}")
    

    for case_id in a_by_id:
        n += 1
        a_pass = case_passed(a_by_id[case_id])
        b_pass = case_passed(b_by_id[case_id])
        a_passed += a_pass
        b_passed += b_pass
        if a_pass and b_pass:
            both_pass += 1
        elif a_pass:
            a_only += 1
        elif b_pass:
            b_only += 1
        else:
            both_fail += 1

    p_value = mcnemar_test(a_only,b_only)

    return ComparisonResult(n_cases = n, a_passed = a_passed, b_passed = b_passed, both_pass = both_pass, both_fail = both_fail, a_only = a_only, b_only = b_only,p_value = p_value)




