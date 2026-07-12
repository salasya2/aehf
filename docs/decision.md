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

8. Design choice sync vs async — judge scoring
**Context:**  We have two judges one which runs without API on CPU(`AssertionJudge`), the other uses API (`LLMJudge`).
**Decision:** Chose async for score method 
**Why:** The real driver is uniformity: the runner and the calibration loop call await judge.score(...) without knowing or branching on which judge they hold. The cost async imposes on the CPU-only judge is trivial; the cost sync imposes on the API-bound judge is real (serialized calls). So I make the whole protocol async — same reasoning as ToolProvider.execute, which I made async even though the mock doesn't need it.
**con:** Async is infectious — once score is async, everything up the call stack is async too. You're accepting that spread in exchange for a uniform interface.
**Rejected:** Rejected the sync for the score method in judge protocol.

9. Who Runs Judge
**Decision:** A seperate class to run the judges.
**Why:** Some we need to rerun judges, putting it into run suite will cause running the agent again which is expensive.
**Rejected:** Calling Judge in run_suite

10. n-sampling lives in the CLI, not run_suite
**Decision:** `run` loops `run_suite`/`judge_suite` n times; the runner still produces one CaseResult per case.
**Why:** Threading `n` into run_suite would put n copies of each case id into a single SuiteResult, and judge_suite joins transcripts by case id in a dict — duplicate ids silently collapse. Keeping n at the CLI keeps the one-result-per-case contract that judge_suite's join and the CLI table depend on.
**Rejected:** an `n_samples` parameter inside run_suite — breaks the id-keyed join downstream.

11. Exact binomial McNemar, not chi-square
**Decision:** McNemar's test uses the exact binomial form over discordant pairs, not the chi-square approximation.
**Why:** The suite is small (18 cases -> often <10 discordant pairs), exactly where the chi-square approximation is unreliable. The exact test is also simpler in stdlib (`math.comb`), ~6 lines. Limitation: `compare` runs on single stored runs, so McNemar is n=1; the n=5 story lives in the aggregate table's pass rates + Wilson CIs.
**Rejected:** chi-square McNemar — inaccurate at small discordant counts.

12. Errors the agent can act on return strings; errors only the operator can fix raise
**Decision:** MockToolProvider returns an error string for an unknown tool; ReplayToolProvider and the LLM judge raise on unrecoverable states. The regression store raises RunNotFoundError.
**Why:** An unknown-tool call is agent behaviour worth evaluating (the agent can read the error and recover). A replay miss, a missing store key, or a malformed judge verdict are harness misconfiguration the model cannot fix — fail loud, don't corrupt the data with a fake verdict.
**Rejected:** silent fallbacks (e.g. replay-miss -> live call) — turns deterministic/free into paid/flaky without warning.

13. `cast` is a lie to the type checker at trust boundaries (bug post-mortem)
**Decision:** Validate the shape of API/JSON responses at runtime; never rely on `cast` to make them safe.
**Why:** `cast(dict, block.input)` type-checked green and passed every stub test, but a live Sonnet judge omitted the required `passed` field on an ambiguous case (it over-reasoned; stop_reason was tool_use, NOT truncation). `cast` does nothing at runtime, so the missing key surfaced as a cryptic KeyError deep in a 180-call batch. Fixed with a bounded 3x retry (LLM tool calls are stochastic; a fresh sample usually complies) plus a diagnostic error naming stop_reason and the partial dict.
**Rejected:** trusting the "required" schema field to guarantee presence — forced tool_choice guarantees the tool is called, not that every field is populated.

14. Use the judge you calibrated
**Decision:** The Haiku vs Sonnet experiment judges with the Haiku v1 judge (the one measured at kappa 0.894), not a swapped-in stronger model.
**Why:** Calibration earns trust in a *specific* instrument. Judging the experiment with an uncalibrated Sonnet judge would throw that away — and Sonnet is exactly the model that triggered the omitted-field bug. Holding the calibrated Haiku judge constant across both agent runs is both more rigorous and more robust.
**Rejected:** judging with the strongest available model (Sonnet) — uncalibrated, and behaviourally flakier on this task.

15. temperature is deprecated on Claude 5 — do not send it
**Decision:** The LLM judge does not pass `temperature`.
**Why:** The Claude 5 family (e.g. claude-sonnet-5) rejects `temperature` with an invalid_request_error. The kappa-0.894 run never sent it and was fine, so judge determinism relies on the model default, not a temperature knob.
**Rejected:** `temperature=0` for determinism — rejected by the API on current models.
 
