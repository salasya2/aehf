
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Termination(Enum):
    finished = "finished"
    max_steps = "max_steps"
    timeout = "timeout"
    crashed= "crashed"
    refused = "refused"
    unexpected_stop = "unexpected_stop"
    budget_exceeded = "budget_exceeded"
    budget_and_steps_exceeded = "budget_and_steps_exceeded"

class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)
    toolname: str
    arguments: dict[str,Any]
    result: str
    error_flag: str | None =None
    latency: float

class Step(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_output:str
    tool_calls: list[ToolCall] | None=None
    token_usage: int= Field(..., description ="Token Usage")

class Transcript(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    ordered_steps: list[Step]
    final_answer: str
    total_tokens: int
    duration_seconds: float 
    termination_reason: Termination
