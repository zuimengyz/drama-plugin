"""Replay F01-TS01-R offline artifacts. Never connects, reserves or generates.

Run from plugin with: python tests/replay_video_reconciliation.py --output PATH
All Media/upload/evidence records are explicitly synthetic test records.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from test_video_reconciliation import ROUTES, current_fixture, compile_all
from drama_plugin.hosts.comfy_video import verify_execution
from drama_plugin.visual.video_selection import seal_decision
from seedance_helpers import execution_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = []
    for route, variant in ROUTES:
        directory = args.output.resolve() / (route + '-' + variant.replace(' ', '-'))
        directory.mkdir(parents=True, exist_ok=True)
        r, c, g, s, host = current_fixture(directory, route, variant)
        request = compile_all(r, c, g, s, host)
        decision = seal_decision(r, c, request, stage_id='OFFLINE', rationale='F01-TS01-R schema replay; synthetic receipts',
            comparisons=[], fallback='stop', host_adapter=host, production_route=execution_plan(r, c), dry_run=True)
        verify_execution(decision, allow_dry_run=True)
        for name, value in [('request', request), ('sealed-request', decision)]:
            (directory / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2))
        results.append({'template': route, 'variant': variant, 'model_key': c.capability['model_key'],
            'state': 'SEALED_DRY_RUN', 'submissionAllowed': False, 'requestFingerprint': decision['request_fingerprint'],
            'sealFingerprint': decision['fingerprint']})
    summary = {'scope': 'OFFLINE SYNTHETIC CONTRACT REPLAY; not runtime authorization', 'paidGenerationCalls': 0, 'routes': results}
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
