#!/usr/bin/env python3
"""Build a source-pinned text creation brief via the actual configured context tool."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))
from drama_plugin import DramaPlugin
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.context import ContextBuildRequest


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision-id')
    args = parser.parse_args()
    snapshot = json.loads(args.source.read_text())
    if snapshot['fingerprint'] != sha256_canonical(snapshot['source']):
        raise ValueError('Source snapshot fingerprint mismatch')
    episode = snapshot['source']['episode']
    request = ContextBuildRequest(
        scope='EPISODE', resource_id=episode['id'], purpose='SHOT_DESIGN',
        options={'creativeRevisionId': args.revision_id} if args.revision_id else {},
    )
    async with DramaPlugin.load(os.environ.get('DRAMA_PLUGIN_ROOT'), os.environ.get('DRAMA_PLUGIN_CONFIG')) as plugin:
        context = await plugin.tools.invoke('context.build_context', request=request)
        if (context.episode is None or context.episode.model_dump(mode='json') != episode
                or context.script is None or context.script.model_dump(mode='json') != snapshot['source']['script']):
            raise ValueError('Formal Episode/Script differs from the pinned source; reconcile before authoring')
        brief = {
            'sourceFingerprint': snapshot['fingerprint'],
            'sourcePath': str(args.source.resolve()), 'episodeId': episode['id'],
            'rhythm': context.creative_rhythm.model_dump(mode='json', by_alias=True),
            'contextId': context.context_id, 'contextPurpose': context.purpose,
            'entry': 'DramaPlugin.load -> tools.context.build_context -> RhythmContextProvider',
            'restoredRevisionId': args.revision_id,
            'instruction': 'Use this effective rhythm to author complete independent coverage from the pinned full source; preserve its causal spine and user scope. No media calls.',
            'pluginRoot': str(plugin.root.resolve()),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(brief, ensure_ascii=False, indent=2))
        print(json.dumps(brief, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
