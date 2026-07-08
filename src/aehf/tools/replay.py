import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from aehf.core.case import EvalCase
from aehf.tools.base import ToolProvider, ToolProviderFactory


class ReplayMissError(Exception):
    """Replay mode lookup miss: harness misconfiguration, not an agent error"""


class ReplayToolProvider:

    def __init__(self,recording_dir: Path,mode:str,inner:ToolProvider  | None =None) -> None:
        self.recording_dir = recording_dir
        self.mode = mode
        self.inner = inner
        if mode not in ['record','replay']:
            raise ValueError(f"mode must be 'record' or 'replay', got {mode!r}")
        # fail at wiring time, not on the first tool call
        if mode == 'record' and inner is None:
            raise ValueError("record mode requires an inner provider")
        if mode == 'replay' and inner is not None:
            raise ValueError("replay mode takes no inner provider")

        self.cache:dict[str,str] = {}
        if self.mode == 'replay':
            try:
                self.cache= json.loads(self.recording_dir.read_text())
            except FileNotFoundError:
                raise FileNotFoundError(f"no recordings found at {self.recording_dir}") from None
        
            

    def _key(self,name:str,arguments:dict[str,Any])->str:
        json_dump = json.dumps(arguments,sort_keys = True)
        bytes_data = json_dump.encode('utf-8')
        hash = f"{name}:{sha256(bytes_data).hexdigest()}"
        return hash

    def _save(self) -> None:
        self.recording_dir.parent.mkdir(parents =True,exist_ok=True)
        self.recording_dir.write_text(json.dumps(self.cache,indent= 2))

    async def execute(self, name : str,arguments:dict[str,Any])  -> str:
        key = self._key(name,arguments)

        if self.mode == 'record':
            assert self.inner is not None  
            result = await self.inner.execute(name,arguments)
            self.cache[key] = result
            self._save()
            
        else:
            try:
                result = self.cache[key]
            except KeyError:
                raise ReplayMissError(f"no recording for {name!r} in {self.recording_dir}; re-record") from None
        return result

def record_provider_factory(recordings_dir: Path, inner_factory :ToolProviderFactory) -> ToolProviderFactory:
    def factory(case: EvalCase) -> ToolProvider:
        return ReplayToolProvider(recording_dir= recordings_dir / f"{case.id}.json", mode="record",inner = inner_factory(case))
    return factory

def replay_provider_factory(recordings_dir:Path) -> ToolProviderFactory:
    def factory(case: EvalCase) -> ToolProvider:
        return ReplayToolProvider(recording_dir=recordings_dir / f"{case.id}.json", mode="replay")
    return factory