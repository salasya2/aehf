from typing import Protocol, runtime_checkable

from aehf.core.case import EvalCase
from aehf.core.results import Verdict
from aehf.core.transcript import Transcript


@runtime_checkable
class Judge(Protocol):
    async def score(self, case : EvalCase, transcript: Transcript) -> Verdict:
        ...
