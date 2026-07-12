# Judge calibration — results log

Measures how well each judge agrees with human labels, using Cohen's kappa
(not raw agreement — see below). Ground truth: 90 agent transcripts from
`examples/calibration_suite.yaml`, hand-labeled by a single annotator
(`labels/labels_filled.jsonl`), 73 pass / 17 fail.

## Headline

| Judge          | Prompt | n  | Raw agreement | Cohen's kappa |
|----------------|--------|----|---------------|---------------|
| AssertionJudge | —      | 90 | 87/90 (97%)   | **0.000**     |
| LLMJudge       | v1     | 90 | 87/90 (97%)   | **0.894**     |

Same 97% raw agreement, wildly different kappa. That gap is the whole point of
the exercise.

## Why raw agreement lies

Both judges agree with the human ~97% of the time, yet one is worthless and one
is excellent. Raw agreement doesn't correct for agreement expected by chance
given the base rates; Cohen's kappa does.

**AssertionJudge (kappa 0.000).** It only checks programmatic criteria
(regex on the answer, required/forbidden tools). On this suite that reduces to
"were the required tools called," so it passes essentially everything:

```
              human_pass  human_fail
judge_pass        73          17        <- passes everything, incl. all 17 fails
judge_fail         0           0
```

Its verdict column is constant, so kappa is 0 by construction — provably no
better than chance despite 97% raw agreement. This is the baseline: assertions
cannot judge these tasks.

**LLMJudge v1 (kappa 0.894).** Judges the transcript against a natural-language
rubric. It caught 16 of the 17 real failures:

```
              human_pass  human_fail
judge_pass        71           1
judge_fail         2          16
```

Only 3 disagreements in 90: 1 false-pass, 2 where the judge was stricter than
the human. kappa 0.894 is "almost perfect agreement" (0.81–1.00 band), above the
0.7 target. v1 hit the target on the first prompt — no v2 iteration needed.

## What the LLM judge catches that assertions cannot

The failures assertions blind-passed were exactly the ones needing judgment,
e.g.:

- **partial answers** — agent answered one of two required parts (a regex sees
  the tool was called and passes it).
- **tool-error handling** — the tool returned an error and the agent fabricated
  an answer anyway (assertions see "tool was called" and pass).

## Caveats (state these alongside the number)

- **Single annotator.** One person labeled all 90; there is no inter-annotator
  agreement, so "ground truth" is one human's judgment.
- **Clean-room suite.** Defined rubrics and deterministic mock tools make the
  judge's task easier than messy real-world evaluation, so 0.894 is an
  optimistic bound, not a universal claim.
- **Prompt versions are frozen.** v1 is never edited; a new prompt would be a new
  key in `JUDGE_PROMPTS`, so these numbers stay reproducible.

## Reproduce

```bash
aehf calibrate labels/labels_filled.jsonl assertion          # -> kappa 0.000
aehf calibrate labels/labels_filled.jsonl llm --prompt-version v1   # -> kappa 0.894
```
