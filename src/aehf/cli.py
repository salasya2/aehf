import asyncio
from pathlib import Path

import typer

from aehf.adapters.fake import FakeAgent
from aehf.core.case import Suite
from aehf.core.loader import SuiteLoadError, load_suite
from aehf.core.runner import run_suite
from aehf.core.transcript import Step, Termination, Transcript

app = typer.Typer()


def demo_transcripts(suite: Suite) -> dict[str, Transcript]:
    transcripts: dict[str, Transcript] = {}
    for i, case in enumerate(suite.eval):
        if i == 1:  
            continue
        n_steps = case.max_steps + 2 if i == 2 else 1 
        transcripts[case.id] = Transcript(
            id=case.id,
            ordered_steps=[
                Step(model_output=f"step {s}", tool_calls=None, token_usage=10)
                for s in range(n_steps)
            ],
            final_answer="demo answer",
            total_tokens=10 * n_steps,
            duration_seconds=0.1,
            termination_reason=Termination.finished,
        )
    return transcripts

@app.command()
def run(path:Path, concurrency:int = 5) -> None:

    try:
        suite = load_suite(path)
        transcripts = demo_transcripts(suite)
        agent = FakeAgent(transcripts)
        suiteresult = asyncio.run(run_suite(agent,suite,concurrency))
    except SuiteLoadError as e:
        print(e)
        raise typer.Exit(2)
    except FileNotFoundError as e:
        print(e)
        raise typer.Exit(2)
    except Exception as e:
        print(e)
        raise typer.Exit(1)
    failed = [r for r in suiteresult.results if r.transcript.termination_reason != Termination.finished]
    print(f"{len(suiteresult.results)} cases: {len(suiteresult.results) - len(failed)} completed, {len(failed)} failed")
    
        

    print(f"{'id':<12} {'reason':<16} {'steps':>5} {'tokens':>7} {'secs':>6}")
    for r in suiteresult.results:
        t = r.transcript
        
        print(f"{r.case_id:<12} {t.termination_reason.value:<16} {len(t.ordered_steps):>5} {t.total_tokens:>7} {t.duration_seconds:>6.2f}")
    if failed:
        raise typer.Exit(1)
if __name__== "__main__":
    app()
