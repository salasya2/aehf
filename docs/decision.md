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


4. Injecting a provider *factory*, not a provider
**Decision:** `AnthropicAdapter` takes a `ToolProviderFactory` (`Callable[[EvalCase], ToolProvider]`) and calls it once per case, instead of taking a `ToolProvider` instance.
**Why:** The adapter is built once per suite, but the provider's data is per-case (mock fixtures live on the case; replay files are keyed by case id). The dependency varies per-request but is injected per-lifetime, so I inject the recipe, not the instance.
**Rejected:** (a) build the provider inside the adapter — hardwires it to one provider type, defeats the point of the protocol. (b) pass the case into `execute(case, name, args)` — welds EvalCase into the ToolProvider protocol forever, so every future real tool (calculator, file-read) pays for one mock's convenience.

5. Budget enforcement: adapter prevents, runner detects
**Decision:** The adapter checks step/token budgets at the top of each loop iteration (`>=`, before the next API call); the runner keeps a post-hoc check (`>`) as a backstop.
**Why:** Post-hoc detection can't save money — a loop that already blew the budget has already spent it. Pre-flight checks in the adapter stop the spend; the runner's check still catches non-adapter agents that overrun. Two different jobs, so the operators (`>=` vs `>`) intentionally differ.
**Rejected:** enforcing only in the runner — detects overruns after paying for them.

6. Agent errors return strings; harness errors raise
**Decision:** `MockToolProvider` returns an error *string* for an unknown tool; `ReplayToolProvider` *raises* `ReplayMissError` on a cache miss.
**Why:** An unknown-tool call is agent behaviour worth evaluating — a real agent should read the error and recover, so it goes back into the conversation as a tool result. A replay miss is a harness misconfiguration the model cannot fix; feeding it to the model produces a garbage transcript that looks like an agent failure. Fail fast, fail loud, tell the operator to re-record. Never fall back to a live call on a miss — that silently turns deterministic CI into paid, flaky CI.
**Rejected:** raising on unknown tool (turns an agent mistake into a harness crash); record-on-miss as the default (hidden cost + nondeterminism).

7. Replay pins tool results, not the model — known limitation
**Decision:** Recordings key tool responses by `(tool_name, sha256(canonical_json(args)))`; the model itself is still sampled live on replay.
**Why:** Full determinism would require recording model responses too, keyed by conversation state — real engineering, out of scope for v0.1. Consequence: with the deterministic mock as the inner provider, record→replay is byte-identical; with argument-sensitive real tools (Phase 6), model drift can cause replay misses on a healthy suite. Mitigate with temperature=0 and tolerant success criteria.
**Rejected:** recording model responses in v0.1 — too much scope for the milestone.

