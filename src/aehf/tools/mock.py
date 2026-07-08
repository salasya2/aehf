from typing import Any

from aehf.core.case import EvalCase


class MockToolProvider:
    def __init__(self,tool_answers:dict[str,str])->None:
        self.tool_answers = tool_answers
    async def execute(self,name:str,arguments : dict[str,Any]) ->str:

        try:
            tool_res = self.tool_answers[name]
        except KeyError:
            return f"Error: Unknown tool {name}"
        return tool_res


def mock_provider_factory(case: EvalCase) -> MockToolProvider:
    return MockToolProvider(case.tool_fixtures or {})
