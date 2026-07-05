from typing import Protocol, runtime_checkable

from aehf.core.case import EvalCase
from aehf.core.transcript import Transcript


@runtime_checkable
class Agent(Protocol):

    async def run(self, case: EvalCase) -> Transcript:
        ...


