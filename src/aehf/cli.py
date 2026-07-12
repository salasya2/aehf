import asyncio
import os
import subprocess
from enum import Enum
from pathlib import Path

import typer
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from aehf.adapters.anthropic import AnthropicAdapter
from aehf.adapters.base import Agent
from aehf.core.loader import SuiteLoadError, load_suite
from aehf.core.results import SuiteResult, Verdict, load_suite_result, save_suite_result
from aehf.core.runner import run_suite
from aehf.core.transcript import Termination
from aehf.judges.assertionjudge import AssertionJudge
from aehf.judges.base import Judge
from aehf.judges.calibration import (
    LabeledTranscript,
    LabelLoadError,
    cohen_kappa,
    export_unlabeled,
    load_labeled,
    render_for_label,
    save_labeled,
)
from aehf.judges.llmjudge import LLMJudge
from aehf.judges.runner import judge_suite
from aehf.regression.diff import DiffResult, diff_runs, is_regression
from aehf.regression.store import RunNotFoundError, load_run, save_run
from aehf.reporting.markdown import render_markdown
from aehf.stats.aggregate import CaseStats, aggregate
from aehf.stats.compare import ComparisonResult, compare_result
from aehf.tools.base import ToolProviderFactory
from aehf.tools.mock import mock_provider_factory
from aehf.tools.replay import record_provider_factory, replay_provider_factory

app = typer.Typer()


class AgentChoice(Enum):
    anthropic = "anthropic"
    
class ToolChoice(Enum):
    mock = "mock"
    record = "record"
    replay = "replay"

class JudgeChoice(Enum):
    assertion = "assertion"
    llm = "llm"
def build_agent(agent: AgentChoice, tools : ToolChoice, recordings_dir:Path, model : str, max_tokens:int) -> Agent: 
    
    if tools == ToolChoice.mock:
        factory : ToolProviderFactory = mock_provider_factory
    elif tools  == ToolChoice.record:
        factory  = record_provider_factory(recordings_dir,mock_provider_factory)
    elif tools == ToolChoice.replay:
        factory = replay_provider_factory(recordings_dir)
    else:
        raise ValueError(f"unknown tools choice {tools}")

    if agent == AgentChoice.anthropic:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ANTHROPIC_API_KEY not set")
            raise typer.Exit(2)
        client = AsyncAnthropic(api_key = api_key)
        return AnthropicAdapter(client = client,provider_factory = factory,model = model, max_tokens = max_tokens)
    raise ValueError(f"unknown agent choice {agent}")
    
def build_judge(judgechoice: JudgeChoice, prompt_version:str,model :str,max_tokens:int) -> Judge:

    if judgechoice == JudgeChoice.assertion:
        judge = AssertionJudge() 
    elif judgechoice == JudgeChoice.llm:
        
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            print("ANTHROPIC_API_KEY not set")
            raise typer.Exit(2)
        return LLMJudge(client=AsyncAnthropic(api_key=key), prompt_version=prompt_version, model=model, max_tokens=max_tokens)
    else:
        raise ValueError(f"unknown Judge choice : {judgechoice}")
    
    return judge

def _current_sha() -> str:
    # CI hands us the SHA directly; fall back to git for local runs
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


async def _score_labeled(judge:Judge, records : list[LabeledTranscript], concurrency : int) -> list[Verdict]:
    sem = asyncio.Semaphore(concurrency)

    async def one(record: LabeledTranscript) -> Verdict:
        async with sem:
            return await judge.score(record.case,record.transcript)
    return await asyncio.gather(*(one(r) for r in records))




@app.command()
def run(path: Path, agent : AgentChoice, tools: ToolChoice, n_samples:int = 1,  concurrency: int = 5, max_tokens : int = 1024, recordings_dir : Path = Path("output/"), model : str = "claude-haiku-4-5-20251001", prompt_version:str = "v1",judge_model :str = "claude-haiku-4-5-20251001",judgechoice : JudgeChoice = JudgeChoice.assertion, output :Path | None = None, store: Path | None = None) ->None:
    load_dotenv()
    try:
        suite = load_suite(path)
    except (SuiteLoadError, FileNotFoundError) as e:
        print(e)
        raise typer.Exit(2)
    if n_samples == 0:
        raise ValueError("n_samples value must be greater than 0")
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
    adapter = build_agent(agent,tools,recordings_dir,model,max_tokens)
    judge = build_judge(judgechoice,prompt_version,judge_model,max_tokens)
    runs : list[SuiteResult] = []
    for _ in range(n_samples):
        suite_result = asyncio.run(run_suite(adapter,suite,concurrency))
        runs.append(asyncio.run(judge_suite(judge,suite,suite_result,concurrency)))

    if store is not None:
        # regression store holds ONE canonical run per (sha, model, judge_version);
        # diff compares single runs. ponytail: store runs[0]; per-sample storage is
        # future work if diff ever consumes n-sampled data.
        save_run(store, _current_sha(), model, prompt_version, runs[0])
    if n_samples == 1:
        if output is not None:
            save_suite_result(suite_result, output / f"{suite_result.suite_name}-{suite_result.run_id}.json")
        failed = [r for r in suite_result.results if r.transcript.termination_reason != Termination.finished]
        print(f"{len(suite_result.results)} cases: {len(suite_result.results) - len(failed)} completed, {len(failed)} failed") 
        print(f"{'id':>23} {'reason':<12} {'steps':>5} {'tokens':>7} {'secs':>6}")
        for r in suite_result.results:
            t = r.transcript
            
            print(f"{r.case_id:>23} {t.termination_reason.value:<12} {len(t.ordered_steps):>5} {t.total_tokens:>7} {t.duration_seconds:>6.2f}")
        if failed:
            raise typer.Exit(1)
    else:
        if output is not None:
            for sr in runs:
                save_suite_result(sr, output / f"{sr.suite_name}-{sr.run_id}.json")
        aggregate_results:list[CaseStats] = aggregate(runs)
        print(f"{'id':>23} {'n':>5} {'pass':>5} {'rate':>7} {'95% CI':>16} {'flaky':>6}")
        for case_stats in aggregate_results:
            ci = f"[{case_stats.ci_low:.2f}, {case_stats.ci_high:.2f}]"
            flag = "flaky" if case_stats.flaky else ""
            print(f"{case_stats.case_id:>23} {case_stats.n:>5} {case_stats.passes:>5} {case_stats.pass_rate:>7.2f} {ci:>16} {flag:>6}")

    

@app.command()
def calibrate(label: Path,judgechoice : JudgeChoice, prompt_version :str = "v1", judge_model :str = "claude-haiku-4-5-20251001", max_tokens : int = 1024 ,concurrency : int = 5) -> None:
    load_dotenv()
    try:
        records = load_labeled(label)
    except (LabelLoadError , FileNotFoundError) as e:
        print(e)
        raise typer.Exit(2)

    if not records:
        print("No labeled records found")
        raise typer.Exit(2)
    judge = build_judge(judgechoice,prompt_version,judge_model,max_tokens)
    verdicts = asyncio.run(_score_labeled(judge, records,concurrency))
    judge_labels = [v.passed for v in verdicts]
    human_labels = [r.human_label for r in records]
    kappa = cohen_kappa(judge_labels,human_labels)
    agreement = sum(j == h for j,h in zip(judge_labels,human_labels,strict = True))

    print(f"records : {len(records)}")
    print(f"raw agreement : {agreement}/{len(records)}")
    print(f"cohen kappa : {kappa:.3f}")

    jp_hp = sum(v.passed and r.human_label for v, r in zip(verdicts, records, strict=True))
    jp_hf = sum(v.passed and not r.human_label for v, r in zip(verdicts, records, strict=True))
    jf_hp = sum(not v.passed and r.human_label for v, r in zip(verdicts, records, strict=True))
    jf_hf = sum(not v.passed and not r.human_label for v, r in zip(verdicts, records, strict=True))
    print()
    print(f"{'':12}{'human_pass':>12}{'human_fail':>12}")
    print(f"{'judge_pass':12}{jp_hp:>12}{jp_hf:>12}")
    print(f"{'judge_fail':12}{jf_hp:>12}{jf_hf:>12}")

    
    disagreements = [(v, r) for v, r in zip(verdicts, records, strict=True) if v.passed != r.human_label]
    print(f"\nDISAGREEMENTS ({len(disagreements)}):")
    for v, r in disagreements:
        human = "PASS" if r.human_label else "FAIL"
        judge_label = "PASS" if v.passed else "FAIL"
        conf = f"{v.score:.2f}" if v.score is not None else "n/a"
        print(f"  {r.case.id:12} human={human} judge={judge_label} conf={conf}")
        print(f"    judge: {v.reasoning}")

@app.command()
def export_labels(suite_path: Path, out: Path, results: list[Path]) -> None:
    load_dotenv()
    try:
        suite = load_suite(suite_path)
    except (SuiteLoadError, FileNotFoundError) as e:
        print(e)
        raise typer.Exit(2)

    records: list[LabeledTranscript] = []
    for path in results:
        try:
            suite_result = load_suite_result(path)
        except FileNotFoundError as e:
            print(e)
            raise typer.Exit(2)
        records.extend(export_unlabeled(suite, suite_result))

    save_labeled(records, out)
    print(f"wrote {len(records)} unlabeled records to {out}")  

@app.command()
def compare(path_a: Path, path_b: Path) -> None:
    try:
        a = load_suite_result(path_a)
        b = load_suite_result(path_b)
        result : ComparisonResult = compare_result(a,b)
        print(f"n_cases   : {result.n_cases}")
        print(f"a passed  : {result.a_passed}")
        print(f"b passed  : {result.b_passed}")
        print(f"both pass : {result.both_pass}")
        print(f"both fail : {result.both_fail}")
        print(f" only a   : {result.a_only}")
        print(f" only b   : {result.b_only}")
        verdict = "significant" if result.p_value < 0.05 else "not significant"
        print(f" P value  : {result.p_value:.4f} → {verdict} at alpha=0.05")
    except (FileNotFoundError,ValueError) as e:
        print(e)
        raise typer.Exit(2)

@app.command()
def diff(base_sha:str, head_sha:str, model: str = "claude-haiku-4-5-20251001", judge_version: str = "v1", store: Path = Path(".aehf"), out: Path = Path("scorecard.md") ) -> None:

    try:
        base = load_run(base = store,sha = base_sha,model = model, judge_version =judge_version)
        head = load_run(base = store,sha = head_sha,model = model, judge_version =judge_version)
        diff_result : DiffResult = diff_runs(base,head)
    except RunNotFoundError as e:
        print(e)
        raise typer.Exit(2)
    except ValueError as e:
        print(e)
        raise typer.Exit(2)

    markdown_string = render_markdown(diff_result,base_sha,head_sha)
    print(markdown_string)                       # terminal user sees the scorecard
    out.parent.mkdir(parents = True, exist_ok = True)
    out.write_text(markdown_string, encoding = "utf-8")

    if is_regression(diff_result):
        raise typer.Exit(1)
@app.command()
def label(path: Path, only_provisional: bool = False) -> None:
    """Interactively set human_label and note on each record, saving after each."""
    try:
        records = load_labeled(path)
    except (LabelLoadError, FileNotFoundError) as e:
        print(e)
        raise typer.Exit(2)

    for i, rec in enumerate(records):
        if only_provisional and not rec.note.startswith("provisional"):
            continue
        print("\n" + render_for_label(rec))
        current = "PASS" if rec.human_label else "FAIL"
        print(f"[{i + 1}/{len(records)}] current label: {current}  note={rec.note!r}")

        choice = typer.prompt("[p]ass / [f]ail / [s]kip / [q]uit", default="s")
        if choice == "q":
            break
        if choice not in ("p", "f"):
            continue  # skip: leave the record as-is

        note = typer.prompt("note", default="reviewed")
        records[i] = rec.model_copy(update={"human_label": choice == "p", "note": note})
        save_labeled(records, path)  # persist after every label so quitting is safe

    print("saved.")


if __name__== "__main__":
    app()
