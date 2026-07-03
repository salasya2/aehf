from pydantic import BaseModel, Field,field_validator
from typing import Optional, List, Union,Dict
from datetime import datetime
from enum import Enum

class Termination(Enum):
    finished = 1
    max_steps = 2
    timeout = 3
    crashed= 4

class ToolCall(BaseModel):
    toolname: str
    arguments: List[str]
    result: str
    error_flag: str
    latency: int

class Step(BaseModel):

    model_output:str
    tool_calls: Union[List[ToolCall],None]
    token_usage: float= Field(..., description ="Token Usage")

class Transcript(BaseModel):
    id: int
    ordered_steps: List[Step]
    final_answer: str
    total_tokens: int
    wall_clock_time: Optional[datetime] = Field(default=None)
    @field_validator("wall_clock_time",mode = "before")
    def set_at(cls,v:Optional[datetime]) -> datetime:

        return v or datetime.now()
    termination_reason: Termination
