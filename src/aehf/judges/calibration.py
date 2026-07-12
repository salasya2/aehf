from pathlib import Path

from pydantic import BaseModel, ValidationError

from aehf.core.case import EvalCase, Suite
from aehf.core.results import SuiteResult, case_passed
from aehf.core.transcript import Transcript


class LabelLoadError(Exception):
    ...


class LabeledTranscript(BaseModel):
    case : EvalCase
    transcript: Transcript
    human_label : bool
    note : str  = ""


def render_for_label(record: LabeledTranscript) -> str:
    # human-readable view for hand-labeling: the task, the rubric to judge
    # against, then what the agent actually did
    case = record.case
    lines = [
        f"case: {case.id}",
        f"task: {case.task_prompt}",
        f"rubric: {case.success_criteria.rubric or '(none)'}",
        "-- transcript --",
    ]
    for i, step in enumerate(record.transcript.ordered_steps, start=1):
        lines.append(f"  step {i}: {step.model_output}")
        for tc in step.tool_calls or []:
            lines.append(f"    tool {tc.toolname}({tc.arguments}) -> {tc.result}")
    lines.append(f"final answer: {record.transcript.final_answer}")
    lines.append(f"termination: {record.transcript.termination_reason.value}")
    return "\n".join(lines)

def load_labeled(path : Path) -> list[LabeledTranscript]:
    labeled_transcript : list[LabeledTranscript] = []
    with open(path,encoding = 'utf-8') as f:
        for lineno,line in enumerate(f,start = 1):
            try:
                line = line.strip()
                if not line:
                    continue
                lbtranscript = LabeledTranscript.model_validate_json(line)
            except ValidationError as e:
                raise LabelLoadError(f"{path}, line {lineno} : {e}") from e
            labeled_transcript.append(lbtranscript)
    return labeled_transcript
    
def save_labeled(records : list[LabeledTranscript] , path:Path) -> None:
    
    with path.open("w",encoding = "utf-8") as f:
        for record in records:
            f.write(record.model_dump_json())
            f.write("\n")
def cohen_kappa(judge:list[bool] , human : list[bool]) -> float:

    a,b,c,d = 0,0,0,0
    
    if len(judge) == 0:
        raise ValueError("Empty Judge and Human labels") 
    for j,h in zip(judge,human, strict = True):

        if j == h and j :
            a += 1
        elif j == h and not j:
            d += 1
        elif j:
            b += 1
        elif not j:
            c += 1
        
    p_o = (a+d)/len(judge)
    p_e = ((a+b)*(a+c) + (c+d)*(b+d))/(len(judge)**2)

    if p_e == 1:
        return 1.0
    k = (p_o - p_e)/(1 - p_e)

    return k
        
def export_unlabeled(suite: Suite, suite_result: SuiteResult) -> list[LabeledTranscript]:

    cases_by_id : dict[str,EvalCase]= {c.id : c for c in suite.eval}
    case_results = suite_result.results

    records : list[LabeledTranscript] = []

    for cr in case_results:
        case = cases_by_id[cr.case_id]
        records.append(LabeledTranscript(
            case=case,
            transcript=cr.transcript,
            human_label=case_passed(cr),  # provisional; unguarded verdicts[0] would crash on a crashed run
            note="provisional:assertion",
        ))
    return records




