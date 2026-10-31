#!/usr/bin/env python3
"""Native scene overview + animatic from one selection; legacy CLI stays readable."""
import argparse
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description='Selected storyboard -> overview and picture-only Animatic. No generation/adoption.')
    p.add_argument('sequence',type=Path,nargs='?')
    p.add_argument('boards',type=Path,nargs='?')
    p.add_argument('current_sources',type=Path,nargs='?')
    p.add_argument('--selection',type=Path,help='One JSON: selection + currentFingerprints')
    p.add_argument('--overview-only',action='store_true')
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.selection:
        if any((a.sequence,a.boards,a.current_sources)): p.error('Use selection OR legacy positional inputs')
        from drama_plugin.plugin import DramaPlugin
        value=json.loads(a.selection.read_text())
        result=DramaPlugin.render_scene_storyboard(value['selection'],a.output,
            current_fingerprints=value['currentFingerprints'],animatic=not a.overview_only)
    else:
        if not all((a.sequence,a.boards,a.current_sources)): p.error('Supply --selection or all three legacy inputs')
        from drama_plugin.contracts.sequence import SequencePackage
        from drama_plugin.hosts.storyboard_animatic import render_storyboard_animatic
        result=render_storyboard_animatic(SequencePackage.model_validate_json(a.sequence.read_text()),
            json.loads(a.boards.read_text()),a.output,current_fingerprints=json.loads(a.current_sources.read_text()))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
