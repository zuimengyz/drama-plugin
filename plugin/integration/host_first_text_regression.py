"""Exercise registered screenplay tools with real external Host-authored text.

Service providers are isolated in-memory stubs; creative bodies are never fixture
responses. This runner does no model/API/media call, Canon write or adoption.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.screenplay import ContextOriginal, NarrativeThread
from drama_plugin.providers.mock import MockDramaData

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parent
OUTPUT = REPO / 'reports/aie-08-host-first-architecture'
INPUT = REPO / 'reports/aie-07-host-artistic-potential/inputs'


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def plugin() -> DramaPlugin:
    # Fixed local infrastructure only; no environment text backend or live service.
    import drama_plugin.plugin as module
    original = module.load_config
    try:
        module.load_config = lambda _: DramaPluginConfig()
        return DramaPlugin.load(PLUGIN, mock_data=MockDramaData(), creative_root=OUTPUT / 'artifacts')
    finally:
        module.load_config = original


async def prepare(p: DramaPlugin) -> None:
    manifest = json.loads((INPUT / 'source-manifest.json').read_text())
    locations = {r['input']: r['original'] for r in manifest}
    refs = []
    for filename, status in [('original-ru.txt', 'DESIGNATED_SOURCE'), ('adopted-Work.json', 'ADOPTED_FACT'),
                             ('adopted-Script.json', 'ADOPTED_FACT'), ('adopted-Scene3.json', 'ADOPTED_FACT'),
                             ('adopted-Scene4.json', 'ADOPTED_FACT'), ('adopted-Scene5.json', 'ADOPTED_FACT')]:
        path = INPUT / filename
        ref = await p.tools.invoke('screenplay.retain_context', original=ContextOriginal(work_id='ridiculous-man',
            label=filename, status=status, text=path.read_text(), authority_ref=locations[filename] if status == 'ADOPTED_FACT' else None))
        refs.append(ref)
    film = await p.tools.invoke('screenplay.retain_context', original=ContextOriginal(work_id='ridiculous-man',
        label='complete-adopted-twelve-scene-director-screenplay', status='ADOPTED_FACT',
        text=(INPUT / 'full-film-director-screenplay.txt').read_text(), authority_ref=locations['adopted-Script.json'] + '#body/screenplay'))
    refs.append(film)
    threads = []
    for key, scenes, tags, account in [
        ('request-and-return', ('4','5','11','12'), ('request','responsibility'),
         '正式全片：Scene4女孩为母亲求援、被驱斥后转向别人；Scene5面对枪而承认痛；Scene11醒来推开枪、要求生活；Scene12宣讲且找到女孩。母亲结局与后来相见的完整过程未在此框架实现。'),
        ('life-death-and-knowledge', ('2','6','9','10','11','12'), ('life','knowledge'),
         '正式全片：Scene2宣称世界存在与否都无所谓；Scene6梦见自杀、棺中受水滴折磨；Scene9他见共同生活与老人安静死亡，满怀生命而祈祷；Scene10自认败坏众人；Scene11醒来求生活；Scene12宣称见过真理。此索引记述场中事实，不替作者解释它们。'),
        ('same-star', ('3','7'), ('star',),
         '正式全片：Scene3雨夜看到星而决定当夜自杀；Scene7同行者称所见正是回家时云间那颗星。')]:
        ref = await p.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(work_id='ridiculous-man', key=key,
            status='ADOPTED_FACT', account=account, scene_ids=scenes, tags=tags, source_refs=(film,)))
        threads.append(ref)
    for name, scene, tags in [('scene4','4',('request','responsibility')), ('scene9','9',('life','knowledge'))]:
        result = await p.tools.invoke('screenplay.begin', session_id='regression-' + name,
            work_id='ridiculous-man', scope='SCENE', scene_id=scene,
            goal='基于完整原著与正式全片，自由完成本场完整原创导演剧本V1，追求有生命、有思想、有独立电影构思的作品。具体表达、篇幅和时长由作者自主决定。先写完整作品，不先提交取舍计划。',
            source_refs=tuple(refs if name == 'scene4' else [*refs[:3], film]), full_film_ref=film, memory_tags=tags)
        write(OUTPUT / 'regression' / name / 'author-packet.json', result)
    write(OUTPUT / 'audit/registered-entry-preparation.json', {'entry': 'DramaPlugin.tools.invoke(screenplay.*)',
        'service_infrastructure': 'in-memory providers only; no creative fixture', 'source_refs': [dump_contract(r) for r in refs],
        'thread_refs': [dump_contract(r) for r in threads], 'registered_tools': [t.code for t in p.tools.list('screenplay')],
        'professional_preload': [], 'prior_art_candidates_in_author_packet': [], 'formal_adoption': False})


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'record-v1', 'support-packet', 'record-support', 'decide', 'handoff', 'state'])
    parser.add_argument('--scene', choices=['scene4','scene9'])
    parser.add_argument('--file', type=Path)
    parser.add_argument('--specialty')
    parser.add_argument('--question', default='研究完整原稿的艺术可能、具体实现、竞争表达及收益与代价。')
    parser.add_argument('--choice', choices=['KEEP_ALL','DEVELOP','RESTRUCTURE','REDUCE'])
    parser.add_argument('--reason-file', type=Path)
    args = parser.parse_args()
    p = plugin()
    if args.action == 'prepare':
        await prepare(p)
        print('Prepared both autonomous packets through registered Plugin tools.')
        return
    if args.scene is None:
        parser.error('--scene is required')
    folder = OUTPUT / 'regression' / args.scene
    session_id = json.loads((folder / 'author-packet.json').read_text())['session']['sessionId']
    session = p.screenplays.load(session_id)
    result = None
    if args.action == 'record-v1':
        if args.file is None: parser.error('--file is required')
        text = args.file.read_text()
        result = await p.tools.invoke('screenplay.retain_v1', session_id=session_id, text=text, expected_revision=session.revision)
        write(folder / 'v1-registration.json', {'ref': dump_contract(result), 'file': str(args.file.resolve()),
            'utf8_sha256': hashlib.sha256(text.encode()).hexdigest(), 'exact_original_preserved': True})
    elif args.action == 'support-packet':
        result = await p.tools.invoke('screenplay.support_packet', session_id=session_id, specialty=args.specialty, question=args.question)
        write(folder / (args.specialty + '-support-packet.json'), result)
    elif args.action == 'record-support':
        if args.file is None: parser.error('--file is required')
        result = await p.tools.invoke('screenplay.retain_support', session_id=session_id, specialty=args.specialty,
            text=args.file.read_text(), expected_revision=session.revision)
    elif args.action == 'decide':
        if args.reason_file is None or args.choice is None: parser.error('--choice and --reason-file are required')
        result = await p.tools.invoke('screenplay.decide', session_id=session_id, choice=args.choice,
            reason=args.reason_file.read_text(), text=args.file.read_text() if args.file else None, expected_revision=session.revision)
        final = p.screenplays.objects.read_ref(result)
        (folder / 'screenplay-final.md').write_text(final['text'])
        write(folder / 'decision-registration.json', {'selected_ref': dump_contract(result), 'choice': args.choice,
            'original_v1_ref': dump_contract(session.original_v1_ref), 'formal_adoption': False})
    elif args.action == 'handoff':
        result = await p.tools.invoke('screenplay.shot_handoff', session_id=session_id)
        write(folder / 'shot-handoff.json', result)
    elif args.action == 'state':
        result = dump_contract(session)
    if result is not None:
        print(json.dumps(dump_contract(result) if hasattr(result, 'model_dump') else
            {'recorded': args.action, 'session': session_id, 'revision': p.screenplays.load(session_id).revision}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
