
from aehf.core.case import EvalCase
from aehf.core.transcript import Transcript


class FakeAgent:
    def __init__(self, transcripts:dict[str,Transcript]) -> None:
        self.transcripts = transcripts
    
    async def run(self, case : EvalCase) ->  Transcript:
            
        return self.transcripts[case.id]
