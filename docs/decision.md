1. .gitignore

**Decision:** Renaming virtual env to .venv
**Why**: I have created aehf virtual env but also named my dir inside the src as aehf. This resulted in base dir code not being committed to git and was not checked by ruff and mypy.
**Rejected**:  aehf venv confuses the gitignore with the actual dir

2. storing timestamp vs duration
**Decision:** `duration_seconds: float` instead of `wall_clock_time: datetime`.
**Why:** Runner needs elapsed time to enforce budgets; when the run happened belongs to CaseResult metadata, not the transcript. Also using timedelta resulted in several inconsistencies like timedelta(10) refers to 10 days instead of 10 seconds. So to keep everything consistent, I went ahead with float.
**Rejected:** datetime field — conflates "when" with "how long".


3. Using Protocol instead of ABC 
**Decision**: using Protocol instead of ABC
**Why**: With ABC, every class must import aehf package and have to inherit the required classes. Their Code is coupled to the package. 
But with protocol the classes don't have to inherit, they just have to implement with matching function name. A matching function name in someone else's code having no idea about our package will still pass the check.
Eg:- Base agent is defined in base.py and fakeagent  satisfies the Agent without inheritance or registration. 

**Rejected**: ABC — code coupled to the package and inheritance hierarchy.

