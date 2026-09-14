#!/usr/bin/env python3
"""Offline sequence preflight. Outputs readiness, never a paid authorization."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'src'))
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.contracts.production_freeze import ProductionDesignFreeze, FreezeEntry
from drama_plugin.sequence import executable_sequence_handoff
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--package',type=Path,required=True)
p.add_argument('--freeze',type=Path,required=True)
p.add_argument('--current-evidence',type=Path,required=True,help='Fresh sourceFingerprints and freezeEntries; offline evidence is not spend authority')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();current=json.loads(a.current_evidence.read_text())
result=executable_sequence_handoff(SequencePackage.model_validate_json(a.package.read_text()),freeze=ProductionDesignFreeze.model_validate_json(a.freeze.read_text()),current_entries=tuple(FreezeEntry.model_validate(e) for e in current['freezeEntries']),current_fingerprints=current['sourceFingerprints'])
a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['status','designReady','productionDesignComplete','generationAuthorized']}))
