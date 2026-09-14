"""Synthetic approval fixtures never mutate project casting."""
import asyncio
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.production_freeze import ProductionDesignFreeze
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.contracts.sequence_execution import AcceptanceCriterion
from drama_plugin.production_freeze import freeze_gate
from drama_plugin.sequence import executable_sequence_handoff
from drama_plugin.hosts.sequence_execution import SequenceRequestBinding, invoke_sequence_reserved
from test_sequence_production import package as legacy_package


def freeze(status='USER_APPROVED',visual=True):
    policy={k:'fixture policy' for k in ['historicalPlausibility','screenIdealization','realism','leadingCharacterAttractiveness','ageTreatment','bodyIdealization','beautyDirection']}|{'forbiddenDrifts':['no drift']}
    return ProductionDesignFreeze(snapshotId='fixture',scope='s',revision='1',stylization=policy,entries=[dict(role='PROP',semanticKey='console',requirement='REQUIRED',requiresVisualMedia=visual,assetId='asset-fixture',mediaId='media-fixture' if visual else None,mediaContentHash='b'*64 if visual else None,contentFingerprint='a'*64,approvalStatus=status,approvalEvidence='SYNTHETIC TEST USER APPROVAL',referenceDuty='console grip',scope='s',revision='1',sourceLineage=['fixture'])])


def executable(f):
    raw=legacy_package();raw.update(status='DESIGN_REVIEWED',productionDesignFreeze=dict(snapshotId=f.snapshot_id,fingerprint=sha256_canonical(f)))
    for s in raw['shots']:
        s['production']=dict(purpose='close door',visualInformationBeat='door state changes',blocking='captain beside console',choreography=[dict(key='pull',actor='captain',target='lever',approachDirection='hand toward lever',bodyOrientation='facing console',weaponState='not applicable',contact='fingers on handle',forceMotionDirection='down',targetReaction='lever lowers',spatialResult='door closes',followerOpportunity='crew remains inside',continuityConsequence='door closed')],camera='same axis medium',assetRefs=['console'],referenceDuties=[dict(key='prop',role='PROP',requirement='REQUIRED',freezeEntryKey='console',reason='grip identity')],audioBridge={k:'pending obligation' for k in ['dialogueCarry','nativeActionCarry','ambienceContinuity','intentionalSilence','audioCut','jlCarryCandidate']},editBoundary='grip before pull and closed door after',generationGroup=s['key'],acceptanceCriteria=[dict(key='door',observation='door closes after handle moves')],fallbackPlan='replan coverage without changing door outcome')
    raw['bridges'][0]['acceptanceCriteria']=[dict(key='receiver',observation='same closed lever')]
    return SequencePackage.model_validate(raw)


def handoff(p,f,current=None):
    return executable_sequence_handoff(p,{k:'a'*64 for k in ['s','x','y']},f,current or f.entries)


def test_approved_freeze_design_does_not_grant_spend_or_adoption():
    f=freeze();v=handoff(executable(f),f)
    assert v['designReady'] and v['productionDesignComplete']
    assert not any(v[k] for k in ['generationAuthorized','produced','reviewed','userAdopted'])
    assert v['reviewInterface']['required']=='FilmReview.mediaHash == actual output SHA-256'


@pytest.mark.parametrize('status',['CANDIDATE','PENDING_USER_REVIEW','PROJECT_DERIVED','REJECTED','UNKNOWN'])
def test_unapproved_blocked_without_hiding_design_readiness(status):
    f=freeze(status);v=handoff(executable(f),f)
    assert v['designReady'] and not v['productionDesignComplete']


@pytest.mark.parametrize('field',['assetId','contentFingerprint','mediaId','mediaContentHash','approvalEvidence'])
def test_required_reference_or_approval_cannot_be_placeholder(field):
    r=dump_contract(freeze());r['entries'][0][field]=None;f=ProductionDesignFreeze.model_validate(r)
    assert freeze_gate(f,f.entries)['status']=='INCOMPLETE'


def test_text_only_and_nonapplicable_mount_do_not_require_visual_assets():
    f=freeze(visual=False);assert freeze_gate(f,f.entries)['status']=='COMPLETE'
    assert handoff(executable(f),f)['designReady']


@pytest.mark.parametrize('field,value',[('revision','2'),('mediaId','changed'),('mediaContentHash','c'*64),('contentFingerprint','d'*64),('approvalStatus','REJECTED')])
def test_current_change_invalidates_old_seal_and_request(field,value):
    f=freeze();r=dump_contract(f);r['entries'][0][field]=value;fresh=ProductionDesignFreeze.model_validate(r)
    assert sha256_canonical(f)!=sha256_canonical(fresh)
    assert freeze_gate(f,fresh.entries)['status']=='INCOMPLETE'
    with pytest.raises(ValueError,match='STALE'):handoff(executable(f),fresh)


def test_seal_is_deeply_immutable_and_duplicate_scope_rejected():
    f=freeze()
    with pytest.raises(ValidationError):f.revision='2'
    with pytest.raises(ValidationError):f.entries[0].approval_status='REJECTED'
    r=dump_contract(f);r['entries'].append(r['entries'][0])
    with pytest.raises(ValidationError):ProductionDesignFreeze.model_validate(r)
    r=dump_contract(f);r['entries'][0]['scope']='wrong'
    with pytest.raises(ValidationError):ProductionDesignFreeze.model_validate(r)


@pytest.mark.parametrize('defect',['clip','bridge','duty','bible','action','mount','audio','edit','acceptance','fallback','order','continuity'])
def test_executable_package_has_real_obligations(defect):
    f=freeze();r=dump_contract(executable(f));s=r['shots'][0]
    if defect=='clip':s['production']=None
    if defect=='bridge':r['bridges'][0]['acceptanceCriteria']=[]
    if defect=='duty':s['production']['referenceDuties'][0]['freezeEntryKey']='missing'
    if defect=='bible':s['production']['assetRefs']=['missing']
    if defect=='action':s['production']['choreography']=[]
    if defect=='mount':s['production']['choreography'][0].update(mountOrientation='forward',mountReaction='steps forward')
    if defect=='audio':del s['production']['audioBridge']
    if defect=='edit':s['production']['editBoundary']=''
    if defect=='acceptance':s['production']['acceptanceCriteria']=[]
    if defect=='fallback':s['production']['fallbackPlan']=''
    if defect=='order':r['shots'].reverse()
    if defect=='continuity':r['shots'][1]['incomingState']['lever']='open'
    if defect in ['clip','bridge']:
        assert not handoff(SequencePackage.model_validate(r),f)['designReady']
    else:
        with pytest.raises(ValueError):handoff(SequencePackage.model_validate(r),f)


class NeverProvider:
    async def discover(self):raise AssertionError('Provider discovery must not run')
    async def invoke(self,*args):raise AssertionError('Provider invocation must not run')
async def no_claim(*args):raise AssertionError('Reservation claim must not run')
def no_verify(*args):raise AssertionError('Request verification must not run before freeze rejection')


def submit(f,p,b):
    return asyncio.run(invoke_sequence_reserved({'request':{},'frame_snapshot':{'requirements':{'shot_id':'x','target_id':'x'}}},NeverProvider(),package=p,freeze=f,current_entries=f.entries,current_fingerprints={k:'a'*64 for k in ['s','x','y']},binding=b,verify_request=no_verify,claim_submission=no_claim))
def binding(f,p):return dict(packageFingerprint=sha256_canonical(p),freezeFingerprint=sha256_canonical(f),clipKey='x',requestFingerprint=sha256_canonical({}))


def test_submission_blocks_before_provider_and_claim():
    f=freeze('PENDING_USER_REVIEW');p=executable(f)
    with pytest.raises(ValueError,match='SEQUENCE_PRODUCTION_DESIGN_BLOCKED'):submit(f,p,SequenceRequestBinding(**binding(f,p)))


@pytest.mark.parametrize('field',['packageFingerprint','freezeFingerprint','requestFingerprint','clipKey'])
def test_stale_submission_binding_blocks_before_provider(field):
    f=freeze();p=executable(f);r=binding(f,p);r[field]='missing' if field=='clipKey' else 'e'*64
    with pytest.raises(ValueError,match='SEQUENCE_REQUEST_BINDING_STALE'):submit(f,p,SequenceRequestBinding(**r))


def test_approved_entry_delegates_to_existing_mcp_gate(monkeypatch):
    import drama_plugin.hosts.sequence_execution as h
    called=[]
    async def existing(attempt,registry,**kwargs):called.append(attempt);return {'existingGate':'called'}
    monkeypatch.setattr(h,'invoke_reserved',existing)
    f=freeze();p=executable(f)
    assert submit(f,p,SequenceRequestBinding(**binding(f,p)))=={'existingGate':'called'} and called


def test_acceptance_verdict_requires_observation():
    with pytest.raises(ValidationError):AcceptanceCriterion(key='a',observation='visible',result='PASS')


def test_unrelated_old_shot_route_cannot_receive_sequence_binding():
    f=freeze();p=executable(f)
    with pytest.raises(ValueError,match='SEQUENCE_REQUEST_TARGET_MISMATCH'):
        asyncio.run(invoke_sequence_reserved({'request':{},'frame_snapshot':{'requirements':{'shot_id':'old-G07','target_id':'x'}}},NeverProvider(),package=p,freeze=f,current_entries=f.entries,current_fingerprints={k:'a'*64 for k in ['s','x','y']},binding=SequenceRequestBinding(**binding(f,p)),verify_request=no_verify,claim_submission=no_claim))


def test_character_duty_cannot_be_fulfilled_by_approved_prop():
    f=freeze();r=dump_contract(executable(f));r['shots'][0]['production']['referenceDuties'][0]['role']='CHARACTER'
    with pytest.raises(ValueError,match='REQUIRED_REFERENCE'):handoff(SequencePackage.model_validate(r),f)
