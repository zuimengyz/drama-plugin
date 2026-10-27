#!/usr/bin/env python3
"""Explicit local director preview; no Provider, DB or adoption writes."""
import argparse
import json
from pathlib import Path
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.hosts.storyboard_animatic import render_storyboard_animatic
p = argparse.ArgumentParser(description='Local picture-only DRAFT from storyboard stills; complete sound through the existing finishing owner. No generation or adoption.')
p.add_argument('sequence', type=Path)
p.add_argument('boards', type=Path, help='Shot key -> [{path: absolute still image, duration: seconds}]')
p.add_argument('current_sources', type=Path, help='Current source key -> fingerprint')
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
print(json.dumps(render_storyboard_animatic(SequencePackage.model_validate_json(a.sequence.read_text()),
    json.loads(a.boards.read_text()), a.output,
    current_fingerprints=json.loads(a.current_sources.read_text())), ensure_ascii=False, indent=2))
