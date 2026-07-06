import asyncio

from aehf.core.case import EvalCase
from aehf.core.transcript import Termination, Transcript


class SlowAgent:

    def __init__(self, transcripts: dict[str, Transcript]) ->  None:
        self.transcripts = transcripts
    
    async def run(self, case: EvalCase) -> Transcript:
        await asyncio.sleep(10)
        
        

        return Transcript(id = "-1", ordered_steps =[], final_answer ="", total_tokens = 10, duration_seconds = 20.0, termination_reason = Termination.finished)
    
class TrackingAgent:
    def __init__(self, transcripts:dict[str,Transcript], max_concurrency_holder:int)-> None:
        self.transcripts = transcripts
        self.current = 0
        self.peak = 0
    async def run(self, case:EvalCase) -> Transcript:
        self.current += 1
        self.peak = max(self.peak, self.current)
        await asyncio.sleep(0.05)
        self.current -= 1
        return self.transcripts[case.id]