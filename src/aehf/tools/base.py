from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from aehf.core.case import EvalCase

ToolProviderFactory = Callable[[EvalCase],"ToolProvider"]

@runtime_checkable
class ToolProvider(Protocol):
    async def execute(self, name:str,arguments:dict[str,Any]) -> str:
        ... 
