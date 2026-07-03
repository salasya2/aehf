from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Termination(Enum):
    finished = 1
    max_steps = 2
    timeout = 3
    crashed= 4

class ToolCall(BaseModel):
    toolname: str
    arguments: list[str]
    result: str
    error_flag: str
    latency: int

class Step(BaseModel):

    model_output:str
    tool_calls: list[ToolCall] | None=None
    token_usage: float= Field(..., description ="Token Usage")

class Transcript(BaseModel):
    id: int
    ordered_steps: list[Step]
    final_answer: str
    total_tokens: int
    wall_clock_time: datetime = Field(default_factory=datetime.now)
    termination_reason: Termination
