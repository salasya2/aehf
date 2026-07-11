import re

from aehf.core.case import EvalCase
from aehf.core.results import Verdict
from aehf.core.transcript import Transcript


class AssertionJudge:

    async def score(self, case : EvalCase, transcript: Transcript) -> Verdict:
        criteria = case.success_criteria
        reasons: list[str] = []
        passed = True

        if criteria.answer_regex is not None:
            if re.search(criteria.answer_regex, transcript.final_answer):
                reasons.append("answer matched")
            else:
                reasons.append("answer did not match")
                passed = False

        called = [tc.toolname for step in transcript.ordered_steps for tc in (step.tool_calls or [])]

        forbidden_hits = sorted({t for t in called if t in criteria.forbidden_tools})
        if forbidden_hits:
            reasons.append(f"forbidden tool(s) called: {', '.join(forbidden_hits)}")
            passed = False

        missing = sorted(t for t in criteria.required_tools if t not in called)
        if missing:
            reasons.append(f"required tool(s) not called: {', '.join(missing)}")
            passed = False
        elif criteria.required_tools:
            reasons.append("all required tools called")

        return Verdict(
            passed=passed,
            score=1.0 if passed else 0.0,
            reasoning="; ".join(reasons) or "no criteria specified",
            judge_name="AssertionJudge",
            version="1",
        )
