# aehf — agent evaluation harness framework

A framework-agnostic harness for evaluating tool-using LLM agents: run a suite
of cases, judge the transcripts, and get **statistically honest** pass rates and
regression checks — not a single flaky number.

The point of aehf is not just to score agents, but to **validate the judge doing
the scoring first**, then use that trusted judge to make claims you can defend.

## Headline finding

On 90 hand-labeled agent transcripts:

| Judge          | Raw agreement | Cohen's kappa |
|----------------|---------------|---------------|
| AssertionJudge | 97%           | **0.000**     |
| LLMJudge (v1)  | 97%           | **0.894**     |

Both judges agree with the human ~97% of the time, yet one is worthless and one
is excellent. Raw agreement doesn't correct for chance given the base rates;
**Cohen's kappa does.** The assertion judge passes essentially everything, so its
97% is meaningless (kappa 0); the calibrated LLM judge reaches "almost perfect"
agreement. This gap is the whole reason the harness measures kappa before
trusting any downstream number. (Details and caveats: `docs/calibration.md`.)

## Architecture — everything is a protocol

The eval core is decoupled from any provider by three Python `Protocol`s. The
runner, judges, and stats know only the interfaces:

```
                        EvalCase (YAML)
                              |
                              v
   +-------------------------------------------------+
   |  runner  --> Agent.run(case) -> Transcript      |   Agent protocol
   |                   |    (AnthropicAdapter,        |   (bring your own:
   |                   |     FakeAgent, ...)          |    LangChain, raw, ...)
   |                   v                              |
   |           ToolProvider.execute()                |   ToolProvider protocol
   |           (mock / record / replay)              |
   |                   |                              |
   |                   v                              |
   |           Judge.score(case, transcript)         |   Judge protocol
   |           (AssertionJudge, LLMJudge) -> Verdict  |
   +-------------------------------------------------+
                              |
              +---------------+----------------+
              v               v                v
        stats (Wilson,   calibration        regression
        McNemar, n=k)    (kappa vs human)   (store, diff, CI gate)
```

The agent under test is a black box behind `Agent`; aehf evaluates whatever
implements `run(case) -> Transcript`. The shipped `AnthropicAdapter` is a
reference implementation, not the framework.

## What's inside

- **Runner** — async, budget/timeout-enforced, captures agent crashes as failed
  cases (never harness crashes), bounded concurrency.
- **Tools** — mock fixtures, plus record/replay for deterministic offline reruns.
- **Judges** — programmatic assertions and a versioned LLM judge with structured
  (forced-tool) verdicts; calibrated against human labels with Cohen's kappa.
- **Stats** — n-sample execution, per-case Wilson confidence intervals, flakiness
  flags, and McNemar's exact paired test for model/prompt comparison.
- **Regression** — results store keyed by (git SHA, model, judge version),
  `aehf diff`, a markdown scorecard, and a PR-gate GitHub Action.

## Install

```bash
pip install -e ".[dev]"        # editable, with dev tooling
```

Set `ANTHROPIC_API_KEY` (a `.env` file is loaded automatically) for anything that
runs a live model. The test suite runs **green without a key** — CI is free and
offline.

## Quickstart

```bash
# run a suite with mock tools, assertion judge (no API cost for the judge)
aehf run examples/calibration_suite.yaml anthropic mock --judgechoice assertion

# n-sampled run: per-case pass rate + Wilson CI + flakiness
aehf run examples/calibration_suite.yaml anthropic mock --n-samples 5

# calibrate a judge against human labels -> Cohen's kappa + disagreements
aehf calibrate labels/labels_filled.jsonl llm --prompt-version v1

# compare two saved runs with McNemar's test
aehf compare runA.json runB.json

# regression diff between two stored runs (CI gate)
aehf diff <base-sha> <head-sha> --store .aehf
```

Full command list: `run`, `calibrate`, `export-labels`, `label`, `compare`,
`diff`.

## Two findings, in one narrative

1. **Judge calibration** — assertions kappa=0.00 -> LLM judge kappa=0.894 (n=90).
   The instrument is validated.
2. **Model comparison** — using that validated judge, Haiku and Sonnet were
   **statistically indistinguishable** on the suite (15/18 vs 14/18, McNemar
   p=1.0). The apparent edge is noise; a single-run comparison would have misled.
   (`docs/calibration.md`.)

Both come with honest caveats stated in the docs (single annotator; a saturated
suite that can't discriminate the two models). Reporting the null result honestly
is the point — see `docs/decision.md` for every design choice and rejected
alternative.

## Scope (v0.1)

- Ships an Anthropic reference adapter and judge. The `Agent`/`Judge`/`ToolProvider`
  protocols make other providers drop-in; a second provider is the planned
  demonstration of the framework-agnostic claim.
- The CI eval gate compares **committed** baseline runs (golden-file style),
  because replay pins tool results but not the model. See `docs/eval-gate.md`.
- Tested: 115 tests, `mypy --strict` clean, ruff clean.
