from pathlib import Path

from aehf.core.results import SuiteResult, load_suite_result, save_suite_result


class RunNotFoundError(Exception):
    ...


def _run_path(base:Path,sha:str,model:str,judge_version:str) -> Path:
    return base / sha / f"{model}__{judge_version}.json"

def save_run(base:Path, sha:str,model:str,judge_version:str,result:SuiteResult) -> None:
    run_path = _run_path(base,sha,model,judge_version)
    run_path.parent.mkdir(parents = True,exist_ok = True)
    save_suite_result(result, run_path)

def load_run(base:Path,sha:str,model:str,judge_version:str) -> SuiteResult:

    try:
        run_path = _run_path(base,sha,model,judge_version)
        suite = load_suite_result(run_path)
    except FileNotFoundError:
        raise RunNotFoundError(f"no run for {sha}/{model}/{judge_version} under {base}")
    return suite

def list_runs(base:Path) -> list[tuple[str,str,str]]:
    runs: list[tuple[str, str, str]] = []
    if not base.exists():
        return []                      
    for path in base.glob("*/*.json"):  
        sha = path.parent.name          
        model, _, judge_version = path.stem.partition("__")
        runs.append((sha, model, judge_version))
    return sorted(runs)