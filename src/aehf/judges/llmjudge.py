from typing import Any, cast

from anthropic import AsyncAnthropic
from anthropic.types import ToolParam

from aehf.core.case import EvalCase
from aehf.core.results import Verdict
from aehf.core.transcript import Transcript

JUDGE_PROMPTS: dict[str, str] = {
    
    "v1": """You are grading a single AI agent transcript against a success criterion.

The agent was given this task:
{task}

Success criterion (the ONLY thing that matters):
{rubric}

Agent transcript:
{transcript}

Grade strictly:
- PASS only if the final answer satisfies the criterion. Partial, hedged, or "almost" answers are FAIL.
- Judge the outcome, not the effort. A long, well-written transcript that misses the criterion is FAIL; a terse one that meets it is PASS.
- Ignore style, politeness, and verbosity entirely.
- If the transcript contradicts its own tool results, FAIL.
- If you cannot find clear evidence that the criterion is met, FAIL.

Record your verdict with the record-verdict tool. In `reasoning`, quote the specific
words from the transcript that decided your verdict. In `confidence`, give 0.0-1.0
for how certain you are.""",
}


VERDICT_TOOL = ToolParam(
    name = "record-verdict",
    description = "Record your evaluation of agent transcript",
    input_schema = {
        "type" : "object",
        "properties" : {
            "passed" : {"type" : "boolean", "description": "Did the transcript satisfy the success criteria?" },
            "reasoning" : {"type" : "string", "description": "Brief Justification citing the specific evidence from the transcript."},
            "confidence" : {"type" : "number", "description" : "0.0 - 1.0, how certain you are"},
        },
        "required" : ["passed","reasoning","confidence"]
    }

)


class LLMJudge:
    def __init__(self ,client : AsyncAnthropic, prompt_version :str,  model:str,max_tokens : int) -> None:
        
        self.client = client
        self.model =model
        self.prompt_version = prompt_version
        if self.prompt_version not in JUDGE_PROMPTS.keys():
            raise ValueError(f"unknown prompt version {self.prompt_version!r}; have {list(JUDGE_PROMPTS)}")
        self.judge_prompt = JUDGE_PROMPTS[prompt_version]
        self.max_tokens = max_tokens

    def render_transcript(self, transcript: Transcript) -> str:
        
        res = ""
        token_usage = 0
        for i,step in enumerate(transcript.ordered_steps):

            res += f"====== Step {i+1} ======\n"
            res += f"Model: {step.model_output}\n"
            token_usage += step.token_usage
            if not step.tool_calls:
                continue
            for i,t in enumerate(step.tool_calls):
                res += f"Tool Call : {t.toolname}({t.arguments})\n"
                res += f"Tool Result :  {t.result}\n"
            
        res += "====== Final Answer ======\n"
        res += f"{transcript.final_answer}\n"
        res += f"Termination : {transcript.termination_reason} | Steps: {len(transcript.ordered_steps)} | Tokens: {token_usage}\n" 
        return res

    async def score(self, case: EvalCase, transcript: Transcript) -> Verdict:
        agent_transcript = self.render_transcript(transcript)
        rubric = case.success_criteria.rubric
        if not rubric:
            raise ValueError("Missing Rubric values")
        prompt = self.judge_prompt.format(task = case.task_prompt,rubric = rubric ,transcript = agent_transcript)

        required = {"passed", "reasoning", "confidence"}
        last = ""
        # the model occasionally over-reasons and omits a required field even
        # though the tool call completed (stop_reason=tool_use, not truncation).
        # a fresh sample usually fixes it — retry a few times before failing so
        # one flaky verdict doesn't crash a whole batch run.
        for _ in range(3):
            response = await self.client.messages.create(
                model = self.model,
                max_tokens = self.max_tokens,
                # NB: temperature is deprecated on the Claude 5 family and rejected
                # by the API — do not pass it.
                tools = [VERDICT_TOOL],
                tool_choice = {"type" : "tool", "name" : "record-verdict"},
                messages = [{"role":"user","content" : prompt}],
            )
            block = next((b for b in response.content if b.type == "tool_use"), None)
            data = cast("dict[str, Any] | None", block.input if block is not None else None)
            if isinstance(data, dict) and required <= data.keys():
                return Verdict(
                    passed=data["passed"],
                    score=data["confidence"],
                    reasoning=data["reasoning"],
                    judge_name="LLMJudge",
                    version=self.prompt_version,
                )
            last = f"stop_reason={response.stop_reason}, got={data!r}"
        raise ValueError(f"LLM judge produced no valid verdict after 3 attempts ({last})")
    

        
