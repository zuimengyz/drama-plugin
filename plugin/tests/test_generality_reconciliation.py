"""NON_NORMATIVE fixtures; no media provider or formal persistence."""
import json
from pathlib import Path
import pytest
from drama_plugin import DramaPlugin,ContextBuildRequest
from drama_plugin.config import load_config
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.creation import Work,Script,Episode,Scene,Shot
from drama_plugin.contracts.visual_route import ProjectVisualRoutes,SequenceVisualRoute
from drama_plugin.visual_route import resolve_visual_route
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.contracts.dramatic_editorial import EditorialRhythmPlan
from drama_plugin.visual.frame_request import FrameSpec,EditSource,compile_frame
from test_visual_first_pass import material

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/'tests/fixtures/generality-cases.json').read_text())['cases']
FORBIDDEN=['Xiang Yu','Yu Ji','Gaixia','Wujiang','Dongcheng','项羽','虞姬','乌江','东城','楚风','天亡我','54:00','P08','C03','神都密诏','狄仁杰']

def case_data(c):
    key=c['id']
    return MockDramaData(work=Work(id=key,title=c['title'],content={'creativeBrief':c,'provenance':'DRAMATIC INVENTION — ISOLATED TEST'}),
      script=Script(id=key+'-script',work_id=key,title=c['title'],content={'ending':c['ending']}),
      episode=Episode(id=key+'-episode',script_id=key+'-script',episode_no=1,title='单场隔离输入',content={}),
      scene=Scene(id=key+'-scene',episode_id=key+'-episode',order=1,title=c['purpose'],location=c['region'],content={'purpose':c['purpose'],'action':c['action'],'spokenContent':[{'id':key+'-line','speakerKey':key+'-person','text':c['dialogue']}]}),
      shot=Shot(id=key+'-shot',scene_id=key+'-scene',shot_no='1',content={'action':c['action'],'visual':c['visual']}),assets=[],media=[],source=None)

@pytest.fixture
def offline(monkeypatch):
    monkeypatch.setattr('drama_plugin.plugin.load_config',lambda _:load_config(environment={}))

@pytest.mark.asyncio
async def test_default_runtime_never_loads_example_story_or_verifies_mock_history(offline):
    async with DramaPlugin.load(ROOT) as p:
        assert await p.tools.invoke('work.list_works') == []
        assert await p.tools.invoke('asset.list_assets') == []
        assert await p.tools.invoke('research.search_sources',query='any history') == []
        claim=await p.tools.invoke('research.verify_claim',claim='invented claim')
        assert claim.supported is False and not claim.evidence
        assert load_config(environment={}).rhythm_speed=='work_defined'
        assert len(p.skills.list())==49 and len(p.tools.list())==50

@pytest.mark.asyncio
@pytest.mark.parametrize('c',CASES,ids=[c['id'] for c in CASES])
async def test_three_work_contexts_do_not_inherit_creative_answers(c,offline):
    async with DramaPlugin.load(ROOT,mock_data=case_data(c)) as p:
        ctx=await p.tools.invoke('context.build_context',request=ContextBuildRequest(scope='SHOT',resource_id=c['id']+'-shot',purpose='SHOT_DESIGN'))
        text=json.dumps(dump_contract(ctx),ensure_ascii=False)
        assert not any(x in text for x in FORBIDDEN)
        assert ctx.work.content['creativeBrief']==c
        route=ProjectVisualRoutes(work_id=c['id'],revision='fixture',visual_route=c['route'],enabled_routes=[c['route']])
        assert resolve_visual_route(route,SequenceVisualRoute(work_id=c['id'],sequence_key='only')).visual_route==c['route']
        assert c['runtime'] != 3240 and c['route'] != 'stylized_cinematic_cg'
        # Use the actual registered instructions, not copies maintained by the test.
        for skill in p.skills.list():
            assert not any(x in skill.instructions for x in FORBIDDEN)


def test_new_route_is_required_and_serialized_old_route_remains_readable():
    with pytest.raises(ValueError):ProjectVisualRoutes(work_id='new',revision='1')
    old={'workId':'old','revision':'1','visualRoute':'live_action_realist','enabledRoutes':['live_action_realist']}
    assert dump_contract(ProjectVisualRoutes.model_validate(old))==old


def test_political_set_piece_does_not_require_heroic_coverage():
    p=EditorialRhythmPlan(scene_ids=['hearing'],source_fingerprint='a'*64,revision='test',
        information_beats=[dict(key='page',information='missing entry',focus='ledger',change='public doubt')],
        coverage=[dict(key='view',beat_ids=['page'],duration=6,duration_basis='DRAMATIC_INFORMATION',duration_reason='allow comparison',purpose='DIALOGUE')],
        establishing_need='one room',visual_contrast_rhythm='different listeners',
        set_piece_coverage={k:['view'] for k in ['setup','escalation','reaction','payoff','aftermath']})
    assert 'hero' not in p.set_piece_coverage
    raw=dump_contract(p);raw['setPieceCoverage']['payoff']=['missing']
    with pytest.raises(ValueError):EditorialRhythmPlan.model_validate(raw)

@pytest.mark.parametrize('count',[0,1,3])
def test_edit_prompt_preserves_source_subjects_without_two_person_assumption(tmp_path,count):
    spec,t=material(tmp_path)
    ref=spec.references[0]
    edit=EditSource(media_id='edit',content_hash=ref.content_hash,local_path=ref.local_path,upload_name=ref.upload_name,uploaded_hash=ref.uploaded_hash,upload_receipt=ref.upload_receipt,review='EDIT_BASELINE',evidence='isolated frame',instruction=f'Adjust exposure only; source has {count} people.')
    # A one-image inspected template; existing helper verifies bytes and graph identity.
    g=json.loads(Path(t.graph_path).read_text());g['nodes']=[g['nodes'][0],g['nodes'][-1]];g['nodes'][-1]['inputs']=g['nodes'][-1]['inputs'][:1];g['links']=g['links'][:1]
    Path(t.graph_path).write_text(json.dumps(g))
    t=t.model_copy(update={'image_slots':('2',),'graph_hash':sha256_canonical(g)})
    spec=spec.model_copy(update={'actors':(),'props':(),'references':(),'reference_lock':{'media/edit':ref.content_hash},'edit_source':edit})
    out=compile_frame(spec,t);prompt=out['request']['input_overrides']['18']['prompt']
    assert 'two existing people' not in prompt and f'{count} people' in prompt
    assert 'subject count' in prompt


def test_music_direction_is_work_owned_not_a_four_emotion_palette():
    from drama_plugin.contracts.film_score import MusicCue,FilmScorePlan
    assert MusicCue.model_fields['emotional_direction'].annotation is str
    assert FilmScorePlan.model_fields['character_theme_policy'].default.startswith('UNDECIDED:')
    # Use the real model validator to check a non-legacy direction with full cue semantics.
    cue=MusicCue(cue_id='curiosity',scene_ids=['hearing'],narrative_function='Compare two accounts while the audience doubts both',
        emotional_direction='CURIOUS_UNSETTLED',performance_relation='ADD_INFORMATION',audience_effect='Notice the discrepancy',
        entry_trigger='The second account contradicts the first',exit_trigger='The witness asks to see the ledger',
        energy_arc=['leave space','introduce doubt'],timbre_palette='Work-approved light plucked timbre',rhythmic_function='irregular questions',
        dialogue_windows=['Witness questions remain audible'],silence_before='Before contradiction',silence_after='During the question',
        source_strategy='ORIGINAL_HUMAN',rights_requirement='Review composition and recording rights',do_not=['Do not resolve the doubt'])
    assert cue.emotional_direction=='CURIOUS_UNSETTLED'
