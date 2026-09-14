#!/usr/bin/env python3
"""Render an authorized local assembly. Does not adopt or import the result."""
import argparse
import json
from pathlib import Path
from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
from drama_plugin.hosts.picture_edit import render_picture_edit
p=argparse.ArgumentParser()
p.add_argument('plan',type=Path)
p.add_argument('sources',type=Path,help='JSON Media ID to absolute local path mapping')
p.add_argument('--current-canon-fingerprint',required=True)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--fps',default=24,type=int)
a=p.parse_args()
print(json.dumps(render_picture_edit(PictureEditPlan.model_validate_json(a.plan.read_text()),
    {k:Path(v) for k,v in json.loads(a.sources.read_text()).items()},a.output,
    current_canon_fingerprint=a.current_canon_fingerprint,fps=a.fps),ensure_ascii=False,indent=2))
