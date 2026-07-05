from pathlib import Path

import pytest

from aehf.core.loader import SuiteLoadError, load_suite


def test_emptypath() -> None:
    with pytest.raises(FileNotFoundError):
        load_suite(path = Path(__file__).parent / "demo.yaml")

def test_valid() -> None:
    demo_path = Path(__file__).resolve().parents[1] / "examples" / "demo.yaml"
    case = load_suite(path = demo_path)
    assert case.eval[0].tools[0].name == "calculator"
def test_emptyfile() -> None:
    with pytest.raises(SuiteLoadError):
        load_suite(path = Path(__file__).parent / "empty.yaml")

def test_malformedyaml() -> None:
    with pytest.raises(SuiteLoadError):
        load_suite(path = Path(__file__).parent / "malformed.yaml")

def test_erroryaml() -> None:
    with pytest.raises(SuiteLoadError):
        load_suite(path = Path(__file__).parent / "error.yaml")