import asyncio

from aehf.tools.mock import MockToolProvider

tool_answers = {"French" : "Hola"}
mocktool = MockToolProvider(tool_answers)
def test_knowntool() -> None:

    assert asyncio.run(mocktool.execute("French",{})) == "Hola"

def test_unknowntool() -> None:

    name = "English"
    output = asyncio.run(mocktool.execute(name,{}))
    assert f"Error: Unknown tool {name}" in output

