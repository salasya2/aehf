from datetime import timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    description: str | None = None
    parameters: dict[str,Any] = Field(default_factory = dict[str,Any])

class EvalCase(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    task_prompt: str
    tools : list[ToolSpec]
    success_criteria: dict[str,Any]
    max_steps: int = Field(..., description = "Maximum Number of Steps")
    timeout_seconds: timedelta = Field(..., description = "Time out Seconds") 
    token_budget: int = Field(..., description = "Token Budget")
    tags: str | None = None

class Suite(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    eval: list[EvalCase]
