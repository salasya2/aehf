import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SuccessCriteria(BaseModel):
    model_config = ConfigDict(frozen = True)
    
    answer_regex : str | None = None
    required_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    rubric : str | None = None
    @field_validator("answer_regex")
    @classmethod
    def _must_compile(cls, v: str | None) -> str | None:
        #
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"invalid answer_regex {v!r}: {e}") from e
        return v

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
    success_criteria: SuccessCriteria
    max_steps: int = Field(..., description = "Maximum Number of Steps")
    timeout_seconds: float = Field(..., description = "Time out Seconds") 
    token_budget: int = Field(..., description = "Token Budget")
    tags: str | None = None
    tool_fixtures: dict[str,str] | None = None

class Suite(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    eval: list[EvalCase]
