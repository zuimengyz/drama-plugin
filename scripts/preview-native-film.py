#!/usr/bin/env python3
"""Read a snapshot of a native Film; compile a volatile request, never execute."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import sys
import tempfile

from dotenv import load_dotenv

PLUGIN = Path(__file__).resolve().parents[1] / 'plugin'
sys.path.insert(0, str(PLUGIN / 'src'))
from drama_plugin.plugin import DramaPlugin
from drama_plugin.providers.mock import MockDramaData


def digest(root):
    paths = [root / 'production.sqlite3', *sorted((root / 'creative-authority').rglob('*.json'))]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


async def main(root, run_id, output):
    for filename in ('mcp-host.env', 'drama-plugin.env'):
        load_dotenv(Path.home() / '.config/historical-plugin' / filename, override=True, interpolate=False)
    def denied(*args, **kwargs):
        raise AssertionError('Offline preview prohibits network IO')
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    before = digest(root)
    with tempfile.TemporaryDirectory(prefix='native-film-preview-') as temporary:
        snapshot = Path(temporary)
        with sqlite3.connect(f'file:{root / "production.sqlite3"}?mode=ro', uri=True) as source:
            with sqlite3.connect(snapshot / 'ledger.sqlite3') as target:
                source.backup(target)
        shutil.copytree(root / 'creative-authority', snapshot / 'creative-authority')
        if (root/'subtitle-authority').exists():
            shutil.copytree(root/'subtitle-authority', snapshot/'subtitle-authority')
        async with DramaPlugin.load(PLUGIN, config_path=os.environ.get('DRAMA_PLUGIN_CONFIG') or None,
                mock_data=MockDramaData.empty(), ledger_path=snapshot / 'ledger.sqlite3',
                creative_root=snapshot / 'creative-authority', target_media_root=snapshot / 'media',
                legacy_reads=False) as plugin:
            def counts():
                with plugin.ledger.transaction() as db:
                    return {name: db.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
                            for name in ('production_run', 'immutable_artifact', 'ledger_index', 'production_operation')}
            start = counts()
            progress = plugin.source_film_production_progress(run_id)
            preview = await plugin.preview_source_film_next_unit(run_id)
            assert counts() == start, 'Preview wrote persistent runtime/artifact/index/operation records'
        assert digest(root) == before, 'Original creative or production data changed'
    output.mkdir(parents=True, exist_ok=True)
    for name, body in (('production-progress.json', progress), ('school-request-preview.json', preview)):
        (output / name).write_text(json.dumps(body, ensure_ascii=False, indent=2))
    rows=['# 原生生产进度（程序输出）','',
        '父 Run 状态：'+progress['runtimeState']+'；全片写定内容完成：'+str(progress['filmContentComplete']),
        '覆盖依据为正式采纳的 phase／台词分配；实际声音准确性单独保存。','',
        '| Scene / 内容 | Shot | 已采用 phase | 规划 / 实际采用时长 | 剩余 phase |',
        '|---|---|---|---|---|']
    for index, scene in enumerate(progress['scenes'],1):
        for shot in scene['shots']:
            rows.append('| '+f'Scene {index} `{scene["sceneId"]}` '+scene['name'][:70].replace('|','／').replace('\n',' ')+' | '+shot['shotId']+' | '+str(shot['adoptedPhases'])+' | '+f'{shot["plannedDurationMs"]/1000:g}s / {shot["actualAdoptedDurationMs"]/1000:g}s'+' | '+str([row['phaseIndex'] for row in shot['remaining']])+' |')
    rows+=['','下一单元：`'+json.dumps(progress['nextUnit'],ensure_ascii=False)+'`','',
        '字幕：场景完成后统一制作。已有归档 '+str(len(progress['archives']))+'；声音／翻译待核保留，不重新生产已采纳片段。']
    (output/'production-progress.md').write_text('\n'.join(rows)+'\n')
    if preview.get('request'):
        (output/'school-prompt-preview.txt').write_text('OFFLINE SIMULATION — NOT SUBMITTED — NOT AUTHORIZED\n\n'+preview['request']['content'][0]['text']+'\n')
    (output / 'read-only-evidence.json').write_text(json.dumps({'originalDigestsUnchanged':True,
        'snapshotCountsBefore':start,'snapshotCountsAfter':start,'networkAllowed':False,
        'simulation':True,'providerPosts':0,'audioCalls':0,'newReservations':0}, indent=2))
    print(json.dumps({'nextUnit':progress['nextUnit'],'requestProduced':bool(preview.get('request')),
        'diagnostics':preview.get('diagnostics'),'references':preview.get('references'),
        'archives':progress['archives'],'output':str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.root, args.run_id, args.output))
