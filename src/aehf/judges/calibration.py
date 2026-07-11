from pathlib import Path

from pydantic import BaseModel, ValidationError

from aehf.core.case import EvalCase, Suite
from aehf.core.results import SuiteResult
from aehf.core.transcript import Transcript


class LabelLoadError(Exception):
    ...


class LabeledTranscript(BaseModel):
    case : EvalCase
    transcript: Transcript
    human_label : bool
    note : str  = ""

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

    for i in range(len(case_results)):

        id = case_results[i].case_id
        transcript = case_results[i].transcript

        case  = cases_by_id[id]

        records.append(LabeledTranscript(case = case, transcript = transcript, human_label = case_results[i].verdicts[0].passed,note= "provisional:assertion"))
    return records




