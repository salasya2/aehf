from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import timedelta

class ToolSpec(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: dict = Field(default_factory = dict)

class EvalCase(BaseModel):
    id: int
    task_prompt: str
    tools : List[ToolSpec]
    success_criteria: Dict
    max_steps: int = Field(..., description = "Maximum Number of Steps")
    timeout_seconds: timedelta = Field(..., description = "Time out Seconds") 
    token_budget: int = Field(..., description = "Token Budget")
    tags: Optional[str] = None

class Suite(BaseModel):
    name: str
    eval: List[EvalCase]
