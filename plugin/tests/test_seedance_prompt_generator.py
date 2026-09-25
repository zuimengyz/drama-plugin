"""Offline adversarial tests: source meaning and transfer, never media quality."""
from copy import deepcopy
import json
import pytest
import httpx
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.video import VideoRequest, VideoReference
from drama_plugin.prompt_generators.contracts import ReferenceBinding, ReferenceCoverage, ProjectionAnnotations, AudioBinding
from drama_plugin.prompt_generators.registry import registry, get_generator, is_seedance2, RESERVED
from drama_plugin.prompt_generators.seedance_2.generator import semantic_key
from drama_plugin.visual.video_prompt import compile_request_ir, compile_video_prompt, ir_source_fingerprint
from drama_plugin.visual.prompt_ir import compile_ir, verify_compilation, require_submission_ir
from test_official_video_providers import request, ref, config, resolve
from test_visual_prompt_ir import visual_ir, fact


def sample(mode='text_to_video', *, cover=True):
    r = request()
    ir = visual_ir('VIDEO', 'seedance')
    ir['secondary_details'] = []
    ir['task']['input_mode'] = dict(text_to_video='text', image_to_video='single_image', first_last_frame='first_last', reference='reference')[mode]
    ir['blocking'].update(positions=fact('man at left'), orientation=fact('man remains facing away'),
                          contact=fact('man keeps hold of the sleeve'), visible_relation=fact('one man beside the gate'))
    ir['video_temporal'].update(start_state=fact('man holds the sleeve'),
        action_progression=[fact('man maintains the grip until the other person stops', scope='CLIP')],
        performance=[fact('man remains facing away', scope='CLIP')],end_state=fact('man still holds the sleeve'))
    ir['continuity'] = [fact('The grip never releases; identity and costume remain unchanged throughout', scope='CLIP')]
    def reference(id, semantics, path=None, duty=None, actor=None):
        claim = ()
        if path and cover:
            if path.startswith('subject.'):
                value = ir['subjects'][0][path.rsplit('.',1)[-1]]
            else: value = ir['environment'][path.rsplit('.',1)[-1]]
            claim = (ReferenceCoverage(path=path,source=value['source'],text_hash=fp(value['text']),duty=duty),)
        return ref(id, semantics=semantics).model_copy(update={'prompt_binding':ReferenceBinding(
            subject_id=actor, coverage=claim, must_not_carry=('pose','lighting','composition','expression'))})
    face = reference('asset-face',('identity',),'subject.man.face','FACE_IDENTITY','man')
    costume = reference('asset-costume',('costume',),'subject.man.costume','COSTUME','man')
    scene = reference('asset-scene',('environment',),'environment.architecture','SCENE')
    args = dict(input_mode=mode, first_frame=None, last_frame=None, reference_images=())
    refs = ()
    if mode == 'image_to_video': args['first_frame']=face; refs=(face,)
    if mode == 'first_last_frame': args.update(first_frame=face,last_frame=scene); refs=(face,scene)
    if mode == 'reference': args['reference_images']=(costume,face,scene); refs=(costume,face,scene)
    r = r.model_copy(update={**args,'continuity':r.continuity.model_copy(update={'references':refs})})
    ir['source_fingerprint'] = ir_source_fingerprint(r)
    return r.model_copy(update={'prompt_ir':ir})


def rebound(r, **changes):
    r = r.model_copy(update=changes)
    ir=deepcopy(r.prompt_ir);ir['source_fingerprint']=ir_source_fingerprint(r)
    return r.model_copy(update={'prompt_ir':ir})


@pytest.mark.parametrize('model', ['seedance-2-standard','seedance-2-fast','seedance-2-mini'])
def test_one_family_for_actual_models(model):
    r=sample();r=rebound(r,continuity=r.continuity.model_copy(update={'primary_model':model}))
    assert is_seedance2(model)
    assert compile_request_ir(r)['generator']['family']=='seedance_2'


@pytest.mark.parametrize('name', [*RESERVED,'unknown'])
def test_reserved_never_dispatch(name):
    if name in RESERVED:
        assert not registry()[name]['implemented'] and not registry()[name]['runtime_dispatch']
    with pytest.raises(ValueError,match='NOT_IMPLEMENTED'):get_generator(name)


@pytest.mark.parametrize('mode', ['text_to_video','image_to_video','first_last_frame','reference'])
def test_modes_complete_coverage_immutable_replay(mode):
    r=sample(mode);before=deepcopy(r.model_dump())
    c=compile_request_ir(r);verify_compilation(c,c['prompt'])
    assert r.model_dump()==before
    required={a['obligation_id'] for a in c['atoms'] if a['required']}
    receipts={a['obligation_id']:a for a in c['coverage']}
    assert required <= receipts.keys() and len(receipts)==len(c['coverage'])
    assert c['statistics']['uncovered_required']==0
    for a in c['coverage']:
        start,end=a['span'];assert c['prompt'][start:end]
        if a['status']=='REFERENCE_COVERED':assert a['input_tag'] in c['prompt'][start:end]
    assert '全程保持：The grip never releases' in c['prompt']
    assert not any(x in c['prompt'] for x in ['asset-','test:approved','policy_hash','REFERENCE_COVERED','空间层','时间层'])
    assert '<主体1> maintains the grip' in c['prompt']
    assert c['generator']['policy']['validation_status']=='LOCAL_EXPERIMENTAL'
    assert c['generator']['soft_budget']=='UNVALIDATED' and c['hard_limit']==5000
    if mode=='text_to_video':assert 'narrow long face' in c['prompt'] and c['statistics']['reference_covered']==0
    else:assert 'narrow long face' not in c['prompt'] and '38–42 years old' in c['prompt']
    if mode=='first_last_frame':
        assert '@图片1 作为首帧' in c['prompt'] and '@图片2 作为尾帧' in c['prompt']
        assert '开场：<主体1> holds' in c['prompt'] and '终态：<主体1> still holds' in c['prompt']


def test_only_reference_proved_facts_reduce():
    c=compile_request_ir(sample('image_to_video',cover=False))
    assert 'narrow long face' in c['prompt'] and c['statistics']['reference_covered']==0
    assert '开场朝向' in c['prompt'] and '光源：gas lamps' in c['prompt']
    assert '不承担姿势职责' in c['prompt'] and '不承担灯光职责' in c['prompt']


def test_multireference_duties_order_and_stable_subject():
    c=compile_request_ir(sample('reference'))
    receipts={a['obligation_id']:a for a in c['coverage']}
    assert receipts['subject.man.costume']['input_tag']=='@图片1'
    assert receipts['subject.man.face']['input_tag']=='@图片2'
    assert receipts['environment.architecture']['input_tag']=='@图片3'
    assert c['prompt'].count('<主体1>')>5 and '<主体2>' not in c['prompt']


def test_input_kind_order_matches_adapter_content():
    r=sample('reference');v=ref('asset-movement','video',('motion',),3);a=ref('asset-sound','audio',('style',),3)
    r=rebound(r,reference_videos=(v,),reference_audios=(a,),continuity=r.continuity.model_copy(update={'references':r.references()+(v,a)}))
    c=compile_request_ir(r)
    from drama_plugin.providers.video.adapters import ADAPTERS
    adapter=ADAPTERS['seedance'](r.continuity.primary_model,config('seedance'),resolve=resolve)
    payload=adapter.payload(r,{x.media_id:'https://example.test/'+x.media_id for x in r.references()},'offline')
    assert payload['content'][0]['text']==c['prompt']
    assert [s['tag'] for s in c['input_slots']]==['@图片1','@图片2','@图片3','@视频1','@音频1']
    for item,slot in zip(payload['content'][1:],c['input_slots']):
        assert next(v['url'] for v in item.values() if isinstance(v,dict)).endswith(slot['media_id'])


@pytest.mark.parametrize('bad',['hash','source','path','actor','noncanonical'])
def test_invalid_reference_coverage_fails(bad):
    r=sample('image_to_video');ref0=r.first_frame;b=ref0.prompt_binding;c=b.coverage[0]
    if bad=='hash':c=c.model_copy(update={'text_hash':'c'*64})
    if bad=='source':c=c.model_copy(update={'source':'forged:owner'})
    if bad=='path':c=c.model_copy(update={'path':'blocking.contact'})
    b=b.model_copy(update={'coverage':(c,),**({'subject_id':'other'} if bad=='actor' else {})})
    ref0=ref0.model_copy(update={'prompt_binding':b})
    continuity=r.continuity if bad=='noncanonical' else r.continuity.model_copy(update={'references':(ref0,)})
    if bad=='noncanonical': ref0=ref0.model_copy(update={'content_hash':'d'*64})
    r=rebound(r,first_frame=ref0,continuity=continuity)
    with pytest.raises(ValueError):compile_request_ir(r)


@pytest.mark.parametrize('pair',[
 ('女孩抓男人袖口','男人抓女孩袖口'),('男人尚未转身','男人已经转身'),('左侧角色','右侧角色'),
 ('开场握住','终场握住'),('同一个人脸','两个不同主体')])
def test_reversal_counterexamples_never_merge(pair):
    r=sample();ir=deepcopy(r.prompt_ir);ir['continuity']=[fact(t,scope='CLIP') for t in pair]
    r=r.model_copy(update={'prompt_ir':ir});c=compile_request_ir(r)
    selected=[a for a in c['atoms'] if a['path'].startswith('continuity')]
    from drama_plugin.prompt_generators.contracts import PromptAtom
    assert semantic_key(PromptAtom.model_validate(selected[0])) != semantic_key(PromptAtom.model_validate(selected[1]))
    for t in pair: assert t in c['prompt']


def test_equivalent_scoped_duplicate_emits_once_but_each_source_receipted():
    r=sample();ir=deepcopy(r.prompt_ir);f=fact('保持接触',scope='CLIP');ir['continuity']=[f,{**f,'source':'another:approved'}]
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert c['prompt'].count('保持接触')==1 and c['statistics']['semantic_duplicates']==1
    receipts=[x for x in c['coverage'] if x['obligation_id'].startswith('continuity')]
    assert len(receipts)==2 and receipts[0]['span']==receipts[1]['span']


def test_same_literal_start_end_and_duties_remain_separate():
    r=sample();ir=deepcopy(r.prompt_ir)
    ir['video_temporal']['start_state']=fact('保持接触');ir['video_temporal']['end_state']=fact('保持接触')
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert '开场：保持接触' in c['prompt'] and '终态：保持接触' in c['prompt']


def test_critical_overflow_and_only_optional_drops():
    r=sample();ir=deepcopy(r.prompt_ir);ir['secondary_details']=[fact('decorative '*1000,'SECONDARY')]
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert c['statistics']['omitted_optional']==1 and c['statistics']['uncovered_required']==0
    ir['continuity']=[fact('required '*1000)]
    with pytest.raises(ValueError,match='BUDGET_OVERFLOW'):compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


@pytest.mark.parametrize('part',['action','video_temporal'])
def test_missing_creative_facts_never_completed(part):
    r=sample();ir=deepcopy(r.prompt_ir);ir.pop(part)
    with pytest.raises(ValueError):compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


@pytest.mark.parametrize('emotion',['sad','angry','悲伤','疏离'])
def test_abstract_performance_returns_owner(emotion):
    r=sample();ir=deepcopy(r.prompt_ir);ir['video_temporal']['performance']=[fact(emotion,scope='CLIP')]
    with pytest.raises(ValueError,match='OBSERVABLE_CARRIER_REQUIRED'):compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


def test_no_default_packages_or_source_metadata():
    p=compile_request_ir(sample())['prompt']
    for value in ['高清','细节丰富','电影质感','色彩自然','光影柔和','无水印','无字幕','Logo','双胞胎','五官清晰','无穿模']:
        assert value not in p


def test_explicit_scoped_constraint_is_not_universal_default():
    r=sample();ir=deepcopy(r.prompt_ir);ir['preserve']=[fact('本镜头不显示字幕或 Logo')]
    assert '本镜头不显示字幕或 Logo' in compile_request_ir(r.model_copy(update={'prompt_ir':ir}))['prompt']


def test_camera_conflict_reports_and_approved_compound_preserves():
    r=sample();ir=deepcopy(r.prompt_ir);ir['video_temporal']['camera_motion']=fact('同时推近并拉远',scope='CLIP')
    r=r.model_copy(update={'prompt_ir':ir})
    with pytest.raises(ValueError,match='CAMERA_CONFLICT'):compile_request_ir(r)
    r=rebound(r,prompt_projection=ProjectionAnnotations(approved_compound_camera_source=ir['video_temporal']['camera_motion']['source']))
    assert '同时推近并拉远' in compile_request_ir(r)['prompt']


def test_time_and_approved_beats_are_not_reauthored_as_shots():
    r=sample();ir=deepcopy(r.prompt_ir);ir['video_temporal']['action_progression']=[fact('0–3s 保持接触',scope='CLIP'),fact('直到停下后才松手',scope='CLIP')]
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert '事件1：0–3s 保持接触' in c['prompt'] and '事件2：直到停下后才松手' in c['prompt']
    assert '镜头2' not in c['prompt']


def audio_sample(kind='DIALOGUE'):
    r=sample();ir=deepcopy(r.prompt_ir);text='螭龙山，我从未答应过你。'
    ir['video_temporal']['audio_requirements']=[fact(text,scope='CLIP')]
    a=AudioBinding(path='video.audio_requirements[0]',source='test:approved-visual-intent',text_hash=fp(text),kind=kind,
                   speaker='man' if kind=='DIALOGUE' else None,language='中文' if kind=='DIALOGUE' else None)
    return rebound(r.model_copy(update={'prompt_ir':ir}),prompt_projection=ProjectionAnnotations(audio=(a,)))


@pytest.mark.parametrize('kind,brackets',[('DIALOGUE',('{}')),('BGM',('（）')),('SFX',('<>'))])
def test_audio_exact_original_no_homophone_rewrite(kind,brackets):
    r=audio_sample(kind);c=compile_request_ir(r)
    text=r.prompt_ir['video_temporal']['audio_requirements'][0]['text']
    assert brackets[0]+text+brackets[1] in c['prompt'] and '吃龙山' not in c['prompt']
    if kind=='DIALOGUE':assert '<主体1> 用中文说道' in c['prompt']
    ir=deepcopy(r.prompt_ir);ir['video_temporal']['audio_requirements'][0]['text']='吃龙山，我答应你。'
    with pytest.raises(ValueError,match='DIALOGUE_SOURCE_CHANGED'):compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


def test_missing_audio_binding_or_speaker_fails_closed():
    r=audio_sample()
    with pytest.raises(ValueError,match='AUDIO_BINDING_REQUIRED'):compile_request_ir(rebound(r,prompt_projection=None))
    a=r.prompt_projection.audio[0].model_copy(update={'speaker':'not-approved'})
    with pytest.raises(ValueError,match='SPEAKER_LANGUAGE_REQUIRED'):
        compile_request_ir(rebound(r,prompt_projection=ProjectionAnnotations(audio=(a,))))


@pytest.mark.parametrize('text',['asset-hidden does something','@图片1 runs','{{actor:missing}} turns'])
def test_unbound_identifier_never_leaks(text):
    r=sample();ir=deepcopy(r.prompt_ir);ir['continuity']=[fact(text)]
    with pytest.raises(ValueError):compile_request_ir(r.model_copy(update={'prompt_ir':ir}))


def test_no_generic_fallback_and_legacy_explicit_read_only():
    r=sample()
    with pytest.raises(ValueError,match='REQUIRES_CANONICAL_IR'):compile_video_prompt(r.model_copy(update={'prompt_ir':None}))
    with pytest.raises(ValueError,match='CONTEXT_REQUIRED'):
        compile_ir(r.prompt_ir,provider_family='seedance',model=r.continuity.primary_model,hard_limit=5000)
    legacy=compile_ir(r.prompt_ir,provider_family='seedance',model=r.continuity.primary_model,hard_limit=5000,legacy_replay=True)
    verify_compilation(legacy,legacy['prompt'],legacy_replay=True)
    with pytest.raises(ValueError):require_submission_ir({'prompt_ir_compilation':legacy},{'prompt':legacy['prompt']})
    r=rebound(sample('reference'),input_mode='edit')
    with pytest.raises(ValueError,match='UNSUPPORTED_INPUT_MODE'):compile_request_ir(r)


def test_tampered_required_receipt_or_prompt_rejected():
    c=compile_request_ir(sample());bad=deepcopy(c);bad['coverage'].pop()
    with pytest.raises(ValueError,match='COMPILATION_CHANGED'):verify_compilation(bad,c['prompt'])
    with pytest.raises(ValueError):verify_compilation(c,c['prompt'][:-20])


async def test_adapter_exact_transfer_mock_only():
    from drama_plugin.providers.video.adapters import ADAPTERS
    r=sample('reference');c=compile_request_ir(r);calls=[]
    def handler(req):calls.append(json.loads(req.content));return httpx.Response(200,json={'id':'offline'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter=ADAPTERS['seedance'](r.continuity.primary_model,config('seedance'),resolve=resolve,client=client)
        await adapter.create_task(r,client_request_id='offline')
    assert len(calls)==1 and calls[0]['content'][0]['text']==c['prompt']
    assert calls[0]['watermark'] is False


def cinematic_sample(tmp_path):
    from seedance_helpers import seed_fixture
    from drama_plugin.hosts.cinematic_projection import executable, prose
    from drama_plugin.visual.cinematic import selection_handoff
    from drama_plugin.contracts.base import dump_contract
    r,_,_,_,_=seed_fixture(tmp_path,'t2v')
    frozen=r.frozen_creative['cinematic_direction'];raw=frozen['spec']
    v=sample();ir=deepcopy(v.prompt_ir)
    ir['task']['clip_id']=r.target_id
    ir['subjects'][0]['id']='A';ir['subjects'][0]['role']=fact('A')
    ir['video_temporal'].update(start_state=fact(raw['openingState']),end_state=fact(raw['endingState']),
        action_progression=[fact(f"{b['start']:g}–{b['end']:g}s "+prose(executable({k:x for k,x in b.items() if k not in ('start','end','kind')})),scope='CLIP') for b in raw['performance']['beats']],
        audio_requirements=[fact(raw['dialogue'][0]['text'],scope='CLIP')])
    ir['continuity']=[fact(prose(executable(raw[k])),scope='CLIP') for k in ('visualBible','cinematography','lighting','stabilityContract','secondaryMotion')]
    a=AudioBinding(path='video.audio_requirements[0]',source='test:approved-visual-intent',text_hash=fp('Hold it.'),
                   kind='DIALOGUE',speaker='A',language='English',timing='1–3s')
    v=rebound(v.model_copy(update={'prompt_ir':ir}),duration=r.duration_seconds,prompt_projection=ProjectionAnnotations(audio=(a,)))
    return r.model_copy(update={'video_request':v,'prompt_ir':None})


def test_cinematic_seedance_formal_http_uses_single_generator(tmp_path):
    from drama_plugin.hosts.http_video import compile_request as host_compile,candidate
    from test_video_selection import evidence,quote
    from test_official_video_providers import cost_metrics
    from drama_plugin.visual.video_selection import Quality,Cost,Evidence
    r=cinematic_sample(tmp_path)
    # Use the actual registry candidate; source compilation is entirely offline.
    c=candidate(r,'seedance-2-mini',cost=Cost(components={'video':20,'audio':0,'references':0,'addons':0,'correction':0},evidence=evidence()),evidence=Evidence.model_validate(evidence()),quality=Quality())
    result=host_compile(r,c)
    assert result['promptCompilation']==compile_request_ir(r.video_request)
    assert result['promptCompilation']['generator']['family']=='seedance_2'
    assert '{Hold it.}' in result['promptCompilation']['prompt']
    ir=deepcopy(r.video_request.prompt_ir);ir['video_temporal']['action_progression'][0]['text']='New action'
    with pytest.raises(ValueError,match='CANONICAL_TIMED_ACTION_MISSING'):
        host_compile(r.model_copy(update={'video_request':r.video_request.model_copy(update={'prompt_ir':ir})}),c)


def test_current_vs_clip_same_literal_not_deduplicated():
    r=sample();ir=deepcopy(r.prompt_ir);ir['continuity']=[fact('保持接触'),fact('保持接触',scope='CLIP')]
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert c['prompt'].count('保持接触')==2


def test_selected_seedance_route_not_continuity_primary_drives_dispatch():
    from drama_plugin.contracts.video import SwitchEvidence
    from drama_plugin.providers.video.adapters import ADAPTERS
    r=sample('reference');r=rebound(r,continuity=r.continuity.model_copy(update={'primary_provider':'kling','primary_model':'kling-3'}),
        switch_evidence=SwitchEvidence(primary_capability_gap='UNSUPPORTED_INPUT_MODE',evidence_ref='offline:approved-switch',at_shot_boundary=True))
    c=compile_request_ir(r,provider='seedance',model='seedance-2-mini')
    adapter=ADAPTERS['seedance']('seedance-2-mini',config('seedance'),resolve=resolve)
    assert adapter.payload(r,{x.media_id:'https://example.test/'+x.media_id for x in r.references()},'offline')['content'][0]['text']==c['prompt']
    assert c['generator']['family']=='seedance_2'
    assert r.continuity.primary_provider=='kling'


def test_subject_labels_stable_when_ir_subject_order_changes():
    r=sample();ir=deepcopy(r.prompt_ir)
    second=deepcopy(ir['subjects'][0]);second.update(id='z-person',role=fact('woman'))
    ir['subjects'].append(second)
    a=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))['prompt']
    ir['subjects'].reverse()
    b=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))['prompt']
    for text in ['<主体1>身份：man','<主体2>身份：woman']:
        assert text in a and text in b


def test_unknown_seedance_model_cannot_use_generic_serializer():
    with pytest.raises(ValueError,match='NOT_IMPLEMENTED'):
        compile_ir(sample().prompt_ir,provider_family='seedance',model='unknown-seedance',hard_limit=5000)


def test_current_constraint_cannot_be_promoted_to_whole_clip():
    r=sample();ir=deepcopy(r.prompt_ir)
    ir['continuity']=[fact('AT CLIP START: hand remains open')]
    c=compile_request_ir(r.model_copy(update={'prompt_ir':ir}))
    assert '当前保持：AT CLIP START: hand remains open' in c['prompt']
    assert '全程保持：hand remains open' not in c['prompt']
