"""Offline source/receipt regressions; no claim about generated film quality."""
from types import SimpleNamespace
import pytest

from drama_plugin.contracts.video import VideoReference
from drama_plugin.generation.contracts import AudioExecutionPlan, ExecutableFact, Obligation, PromptIR
from drama_plugin.generation.seedance import ModelPolicyCatalog, SeedanceTargetAdapter
from drama_plugin.generation.projection import ExecutionProjection
from drama_plugin.generation.sources import SelectedValue
from drama_plugin.production.contracts import DomainReference, SourceReference
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


def source(*path):
    return SourceReference(owner='professional', artifact_ref='approved-design', version=1,
                           fingerprint='a'*64, path=('content', *path))


def test_native_inventory_names_reference_and_coverage_survive_execution_layout():
    scope = RuntimeScope(work_id='film', scene_id='room', shot_id='group-shot')
    package = ArtifactReference(owner='production-package', artifact_ref='package', version=1)
    facts = []
    def add(domain, slot, text, *path, subject=None):
        facts.append(ExecutableFact(fact_id='fact-'+str(len(facts)), domain=domain, slot=slot, text=text,
            source_ref=source(*path), subject_id=subject, obligation=Obligation.EXECUTION_REQUIRED))
    roles = ['朋友乙', '朋友甲', '工程师主人', '成年叙述者，室内客人']
    for i, role in enumerate(roles, 1):
        add('SUBJECTS', 'subject.role', role, 'presentSubjects', str(i-1), 'role', subject=f'cast-{i}')
        add('SUBJECTS', 'subject.role', '继续听取桌边的问题。', 'presentSubjects', str(i-1),
            'inSceneBehaviour', subject=f'cast-{i}')
    add('SUBJECTS', 'preserve.subject_constraints',
        '全镜恰好四名成年男子：工程师（{{actor:cast-3}}）、朋友甲（{{actor:cast-2}}）、朋友乙（{{actor:cast-1}}）、主人公（{{actor:cast-4}}）；没有第五人。',
        'identityConstraints')
    add('WORLD', 'environment.architecture', '十一月三日傍晚。', 'time')
    add('ACTION', 'video.action_progression', '{{actor:cast-1}}拿起茶杯。', 'actionPhases', '0', 'action')
    add('ACTION', 'video.action_progression', '四人已在房间内。', 'actionPhases', '0', 'entryState')
    add('ACTION', 'video.start_state', '四人已在房间内。', 'actionPhases', '0', 'entryState')
    add('ACTION', 'video.action_progression', '杯仍在乙手中。', 'actionPhases', '0', 'observable')
    add('ACTION', 'video.action_progression', '同一只杯，不换座。', 'physicalStateConstraints')
    add('CAMERA', 'video.camera_motion', '甲指向图纸时缓慢靠近，然后停止。', 'movement', 'policy')
    add('LIGHTING', 'lighting.light_sources', '暖侧光，暗面仍可辨衣褶。', 'directionAndQuality')
    add('COLOR', 'secondary.color', '低饱和棕灰衣料，冷暗窗不染青肤色。', 'scenePalette')
    ir = PromptIR.seal(source_package_ref=package, scope=scope, duration_ms=14000, facts=tuple(facts))
    plan = AudioExecutionPlan.seal(source_package_ref=package, scope=scope, duration_ms=14000,
        native_audio_policy='DISABLED', source_roles=())
    media = VideoReference(kind='video', media_id='retained-face-video', version='1', content_hash='b'*64,
        semantics=('identity',), review_ref='reviewed-native-media')
    reference = SimpleNamespace(binding=SimpleNamespace(media=media, role='REFERENCE', subject_ids=('cast-4',)))
    result = SeedanceTargetAdapter().generate(ir, plan, policy=ModelPolicyCatalog().policy('seedance-2-fast'),
        input_mode='reference', references=(reference,))
    prompt = result['prompt']
    assert prompt.startswith('<主体4>仅参考 @视频1 的身份。')
    for name, label in [('朋友乙', 1), ('朋友甲', 2), ('工程师', 3), ('主人公', 4)]:
        assert f'{name}（<主体{label}>）' in prompt
    assert '<主体1>动作：继续听取桌边的问题。' in prompt
    assert prompt.count('四人已在房间内。') == 1
    assert '事件2' not in prompt and '终态：杯仍在乙手中。' in prompt
    assert prompt.index('十一月三日傍晚') < prompt.index('全镜恰好四名') < prompt.index('事件1')
    assert {result['target_mapping'][r['obligation_id']] for r in result['coverage']} == {f.fact_id for f in facts}
    assert result['statistics']['uncovered_required'] == 0
    assert result['input_slots'][0]['content_hash'] == media.content_hash


@pytest.mark.asyncio
async def test_camera_background_stays_retained_without_replaying_future_or_prior_events():
    fields = {'sceneContext':'This encounter belongs to the whole film.',
        'precedingBeatContext':'The previous walk is completed.',
        'followingBeatContext':'He will refuse food and leave later.',
        'trigger':'Friend points at the paper.', 'trajectory':'Approach the table, then stop.'}
    facts = tuple(DomainReference(domain='CAMERA',reference=source('movement','phaseDirections','0',key)) for key in fields)
    selected = [SelectedValue(fact,fields[fact.reference.path[-1]]) for fact in facts]
    for domain,key,text in [('WORLD','setting','The approved room.'),
                           ('PERFORMANCE','physicalExpression','Listen while holding the cup.'),
                           ('ACTION','physicalStateConstraints','One cup, same seat.')]:
        selected.append(SelectedValue(DomainReference(domain=domain,reference=source(key)),text))
    selected.append(SelectedValue(DomainReference(domain='SUBJECTS',reference=source('presentSubjects','0','role')),'Guest'))
    action = source('actionPhases','0','action')
    start,end = source('actionPhases','0','entryState'),source('actionPhases','0','observable')
    values = {item.selection.reference:item.value for item in selected}
    values.update({action:'Point to the paper.',start:'Guest in the room.',end:'Cup still in hand.',
                   source('presentSubjects','0','id'):'guest'})
    class Reader:
        async def resolve(self,ref): return values[ref]
        async def selections(self,package): return ()
    reader = Reader(); reader.resolver = reader
    package_ref = ArtifactReference(owner='production-package',artifact_ref='package',version=1)
    package = SimpleNamespace(scope=SimpleNamespace(work=SimpleNamespace(artifact_ref='film'),
        scene=SimpleNamespace(artifact_ref='room'),shot=SimpleNamespace(artifact_ref='group-shot')),
        artifact_reference=lambda:package_ref)
    unit = SimpleNamespace(execution_context=None,start_ref=start,end_ref=end,action_refs=(action,),reference_disposition=(),fact_refs=facts)
    task = SimpleNamespace(unit=unit,profile=SimpleNamespace(native_audio=False,requested_duration_ms=14000),camera_direction_ref=None,
        return_last_frame=False,continuation=None)
    plan = SimpleNamespace(relations=(),speech_events=())
    result = await ExecutionProjection(reader).project(package,task,plan,tuple(selected))
    assert result.ir is not None
    assert all(text not in ' '.join(f.text for f in result.ir.facts) for key,text in fields.items() if key.endswith('Context'))
    assert {e.source_ref.path[-1] for e in result.internal if e.status=='OUT_OF_UNIT'} == {
        'sceneContext','precedingBeatContext','followingBeatContext'}
    assert fields['trigger'] in {f.text for f in result.ir.facts}
    assert fields['trajectory'] in {f.text for f in result.ir.facts}
    assert task.unit.fact_refs == facts  # Earlier frozen selections remain intact.
