1. .gitignore

**Decision:** Renaming virtual env to .venv
**Why**: I have created aehf virtual env but also named my dir inside the src as aehf. This resulted in base dir code not being committed to git and was not checked by ruff and mypy.
**Rejected**:  aehf venv confuses the gitignore with the actual dir

2. storing timestamp vs duration
**Decision:** `duration_seconds: float` instead of `wall_clock_time: datetime`.
**Why:** Runner needs elapsed time to enforce budgets; when the run happened
belongs to CaseResult metadata, not the transcript.
**Rejected:** datetime field — conflates "when" with "how long".