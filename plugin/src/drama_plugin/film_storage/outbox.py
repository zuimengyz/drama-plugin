from __future__ import annotations
import hashlib,json,time,os
from pathlib import Path
from typing import Any
from drama_plugin.hosts.artifact_io import native_io
from drama_plugin.contracts.base import canonical_json

class FilmOutbox:
    """Durable pointers only: no creative payload, provider dispatch or production state."""
    def __init__(self,path:Path):
        self.path=path;self.io=native_io();path.mkdir(parents=True,exist_ok=True,mode=0o700)
    def enqueue(self,event:dict[str,Any])->str:
        identity=hashlib.sha256(canonical_json(event).encode()).hexdigest()
        target=self.path/(identity+'.json')
        with self.io.guard(self.path/'.queue.lock'):
            if not target.exists():
                self.io.write(target,canonical_json({'event':event,'sourceOrder':time.time_ns()//1000,'acknowledged':False}))
                target.chmod(0o600)
        return identity
    def pending(self)->list[tuple[str,dict[str,Any]]]:
        values=[(p.stem,json.loads(p.read_text())) for p in self.path.glob('*.json')]
        return sorted([(k,v) for k,v in values if not v['acknowledged']],key=lambda kv:kv[1]['sourceOrder'])
    def acknowledge(self,identity:str)->None:
        target=self.path/(identity+'.json')
        with self.io.guard(self.path/'.queue.lock'):
            value=json.loads(target.read_text());value['acknowledged']=True;self.io.write(target,canonical_json(value))

