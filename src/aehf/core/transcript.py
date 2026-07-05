from datetime import timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Termination(Enum):
    finished = 1
    max_steps = 2
    timeout = 3
    crashed= 4

class ToolCall(BaseModel):
    toolname: str
    arguments: dict[str,Any]
    result: str
    error_flag: str | None =None
    latency: float

class Step(BaseModel):

    model_output:str
    tool_calls: list[ToolCall] | None=None
    token_usage: int= Field(..., description ="Token Usage")

class Transcript(BaseModel):
    id: int
    ordered_steps: list[Step]
    final_answer: str
    total_tokens: int
    duration_seconds: timedelta 
    termination_reason: Termination
