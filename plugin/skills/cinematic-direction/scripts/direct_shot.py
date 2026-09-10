#!/usr/bin/env python3
"""Offline creative IR entry. Reads snapshots, never initializes a provider."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))
from drama_plugin.contracts.cinematic import CinematicShotSpec
from drama_plugin.contracts.base import dump_contract
from drama_plugin.visual.cinematic import freeze_direction, selection_handoff, review_direction


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--context', type=Path, required=True)
    p.add_argument('--draft', type=Path, required=True)
    p.add_argument('--visual-resolution', type=Path, required=True)
    p.add_argument('--host-review', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    spec = CinematicShotSpec.model_validate(json.loads(a.draft.read_text()))
    frozen = freeze_direction(spec, context=json.loads(a.context.read_text()),
        visual_resolution=json.loads(a.visual_resolution.read_text()), host_review=a.host_review.read_text())
    handoff = selection_handoff(frozen)
    a.output.mkdir(parents=True, exist_ok=True)
    for name, value in [('cinematic-shot-spec', dump_contract(spec)), ('frozen', frozen),
                        ('review', review_direction(spec)), ('selection-handoff', handoff)]:
        (a.output / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2))
    (a.output / 'execution-brief.md').write_text(handoff['motion_prompt'] + '\n')
    print(json.dumps({'state': frozen['state'], 'fingerprint': frozen['fingerprint'],
        'shotId': spec.shot_id, 'duration': spec.duration_seconds, 'submissionAllowed': False,
        'paidGenerationCalls': 0, 'scope': 'DRY_RUN_ONLY'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
