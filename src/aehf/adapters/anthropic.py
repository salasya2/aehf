import time

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolParam, ToolResultBlockParam

from aehf.core.case import EvalCase
from aehf.core.transcript import Step, Termination, ToolCall, Transcript
from aehf.tools.base import ToolProviderFactory


class AnthropicAdapter:

    def __init__(self, client: AsyncAnthropic, provider_factory: ToolProviderFactory, model: str, max_tokens: int) -> None:
        self.client = client
        self.provider_factory = provider_factory
        self.model = model
        self.max_tokens = max_tokens

    async def run(self, case: EvalCase) -> Transcript:
        toolprovider = self.provider_factory(case)
        tool_spec: list[ToolParam] = [
            ToolParam(name=t.name, description=t.description or "", input_schema=t.parameters)
            for t in case.tools
        ]
        messages: list[MessageParam] = [{"role": "user", "content": case.task_prompt}]
        steps: list[Step] = []
        total_tokens = 0
        final_text = ""
        start_time = time.monotonic()

        while True:
            # enforce budgets before spending, not after
            if len(steps) >= case.max_steps:
                termination_reason = Termination.max_steps
                break
            if total_tokens >= case.token_budget:
                termination_reason = Termination.budget_exceeded
                break

            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                tools=tool_spec,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})
            # input tokens count every turn: each call re-reads the whole conversation
            step_tokens = response.usage.input_tokens + response.usage.output_tokens
            total_tokens += step_tokens

            step_text = ""
            toolcalls: list[ToolCall] = []
            tool_results: list[ToolResultBlockParam] = []
            for block in response.content:
                if block.type == "text":
                    step_text = block.text
                elif block.type == "tool_use":
                    tool_start_time = time.monotonic()
                    result = await toolprovider.execute(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                    toolcalls.append(ToolCall(
                        toolname=block.name,
                        arguments=block.input,
                        result=result,
                        latency=time.monotonic() - tool_start_time,
                    ))

            steps.append(Step(model_output=step_text, tool_calls=toolcalls, token_usage=step_tokens))
            if step_text:
                final_text = step_text
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                termination_reason = Termination.finished
                break
            if response.stop_reason == "refusal":
                termination_reason = Termination.refused
                break
            if response.stop_reason != "tool_use":
                # max_tokens, pause_turn, or anything the API adds later: stop, don't spin
                termination_reason = Termination.unexpected_stop
                break

        return Transcript(
            id=case.id,
            ordered_steps=steps,
            final_answer=final_text,
            total_tokens=total_tokens,
            duration_seconds=time.monotonic() - start_time,
            termination_reason=termination_reason,
        )
