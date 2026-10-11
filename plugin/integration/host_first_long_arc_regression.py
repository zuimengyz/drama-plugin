"""Retain actual candidate discoveries and inspect a far-scene context, text only."""
import asyncio
import json
from pathlib import Path
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.screenplay import ContextOriginal, NarrativeThread
from host_first_text_regression import OUTPUT, plugin, write

async def main():
    p = plugin()
    packet = json.loads((OUTPUT / 'regression/scene9/author-packet.json').read_text())['authorPacket']
    retained = []
    for scene, account, ids in [
        ('scene4', '本次作者候选保留女孩改投另一人并持续求援；与末场找到女孩形成作者理解中的长程关系。未知母亲结局、路人是否救援及重逢细节，不把新动作登记为正式事实。', ('4','8','12')),
        ('scene9', '本次作者候选从对笑的戒备、资格问询、等待死亡答案，发展到共同抬身与安放孩子的手；作者将其联系采用Scene2/6/11/12，而未预定跨场物件回收。', ('2','6','9','11','12')),
    ]:
        body = (OUTPUT / 'regression' / scene / 'screenplay-final.md').read_text()
        use = (OUTPUT / 'regression' / scene / 'long-arc-use.md').read_text()
        ref = await p.tools.invoke('screenplay.retain_context', original=ContextOriginal(
            work_id='ridiculous-man', label='candidate-' + scene + '-discovery', status='AUTHOR_CONCEPT',
            text=body + '\n\n' + use))
        thread = await p.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(
            work_id='ridiculous-man', key='candidate-' + scene + '-responsiveness', status='AUTHOR_CONCEPT',
            account=account, scene_ids=ids, source_refs=(ref,)))
        retained.append(thread)
    original = await p.tools.invoke('screenplay.retain_context', original=ContextOriginal(
        work_id='ridiculous-man', label='open-dream-girl-appearance', status='OPEN_POSSIBILITY',
        text='原著向另一地球飞行时女孩形象闪现，正式Scene7未列出；Scene4作者只提出未来可研究该开放可能。本轮未写该场、未提请采用，未指定回收场次。'))
    possibility = await p.tools.invoke('screenplay.retain_thread', thread=NarrativeThread(
        work_id='ridiculous-man', key='open-dream-girl-appearance', status='OPEN_POSSIBILITY',
        account='未来可研究原著女孩闪现与梦中羞耻/爱的关系；这是开放创作可能，没有新增Canon。',
        scene_ids=('4','7','12'), source_refs=(original,)))
    sources = tuple(SourcePin.model_validate(s['ref']) for s in packet['sources'])
    film = next(s for s in sources if 'complete-adopted' in s.key)
    before = p.screenplays.relevant_memory('ridiculous-man','12')
    after = await p.tools.invoke('screenplay.begin', session_id='regression-far-scene12-context',
        work_id='ridiculous-man', scope='SCENE', scene_id='12', goal='Inspect selected far-scene context; no scene authored in this receipt.',
        source_refs=sources, full_film_ref=film, memory_refs=tuple([*retained, possibility]))
    rows = after['authorPacket']['longArcMemory']
    assert all(r['status'] not in {'AUTHOR_CONCEPT','OPEN_POSSIBILITY'} for r in before)
    assert {r['status'] for r in rows} >= {'ADOPTED_FACT','AUTHOR_CONCEPT','OPEN_POSSIBILITY'}
    assert all(r['possibleReturnScene'] is None for r in rows)
    assert after['session']['originalV1Ref'] is None
    write(OUTPUT / 'regression/long-arc/actual-memory-evolution.json', {
        'actual_authored_use': ['scene4/long-arc-use.md','scene9/long-arc-use.md'],
        'later_context_only_not_new_scene': True, 'default_scene12_memory': before,
        'selected_scene12_author_packet': after, 'candidate_refs': [dump_contract(r) for r in retained],
        'possibility_ref': dump_contract(possibility), 'formalAdoption': False,
        'observedFilmResultClaimed': False, 'noDesignatedPayoff': True})
    await p.aclose()

if __name__ == '__main__':
    asyncio.run(main())
