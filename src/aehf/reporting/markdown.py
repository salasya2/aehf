from aehf.regression.diff import DiffResult, is_regression


def render_markdown(diff: DiffResult, base_sha: str = "", head_sha: str = "") -> str:
    res = ""
    comparison = diff.comparison
    if is_regression(diff):
        res += "## Agent Regression Detected\n"
    else:
        res += "## No significant Regression Detected\n"
    res += f"{base_sha}  → {head_sha}"
    res += f"{len(diff.newly_failing)} newly failing · {len(diff.newly_passing)} newly passing · {diff.unchanged_pass + diff.unchanged_fail} unchanged · McNemar p={comparison.p_value}\n\n"
    if not diff.newly_failing and not diff.newly_passing:
        return res
    res += "|            case         |       change       |\n"

    for cases in diff.newly_failing:

        res += f"|            {cases}            |       ✅→❌       |\n"
    for cases in diff.newly_passing:
        res += f"|            {cases}            |       ❌→✅       |\n"
    

    return res
