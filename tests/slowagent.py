import asyncio
from datetime import timedelta

from aehf.core.case import EvalCase
from aehf.core.transcript import Termination, Transcript


class SlowAgent:

    def __init__(self, transcripts: dict[str, Transcript]) ->  None:
        self.transcripts = transcripts
    
    async def run(self, case: EvalCase) -> Transcript:
        await asyncio.sleep(10)
        
        

        return Transcript(id = "-1", ordered_steps =[], final_answer ="", total_tokens = 10, duration_seconds = timedelta(10), termination_reason = Termination.finished)
