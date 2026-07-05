from pathlib import Path

import yaml
from pydantic import ValidationError

from aehf.core.case import Suite


class SuiteLoadError(Exception):
    ...

def load_suite(path: Path) -> Suite:

    
    with open(path,encoding = "utf-8") as file:
        try:
            data = yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise SuiteLoadError(f"{path}: {e}") from e

    
    try:
        result = Suite.model_validate(data)

    except ValidationError as e:
        raise SuiteLoadError(f"{path}: {e}") from e
    
    return result


    
