"""Approval execution authority never comes from retained provenance (offline only)."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
import pytest
from drama_plugin.contracts.base import dump_contract, sha256_canonical as fp
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.specialized_asset import SpecializedAssetBible
from drama_plugin.hosts.professional import ProfessionalDepartmentHost
from drama_plugin.specialized_asset import provider_projection
from drama_plugin.professional import validate_bible, bible_pin
from r3d_r_helpers import blocker_case
from r3d_helpers import case, approval
from test_specialized_asset import fixture


def submitted(tmp_path: Path) -> dict[str, Any]:
    x=blocker_case(tmp_path)
    ref=x['host'].submit(x['candidate'],current=x['current'],approved_interpretation_refs=(x['trusted'],))
    x['ref']=ref;x['current'][ref.key]=ref.fingerprint
    return x


def test_exact_blocker_and_stored_user_claim_is_not_authority(tmp_path: Path) -> None:
    x=blocker_case(tmp_path);h=x['host'];b=x['candidate'];cur=x['current']
    o,c=h._inputs(b,cur)
    assert validate_bible(x['character'],o,c,approved_interpretation_refs=(x['trusted'],))['validationStatus']=='PASS'
    # The original already includes actorType=USER and an APPROVE receipt.
    for refs in [(),(approval(case(identity='other')), )]:
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
            h.submit(b,current=cur,approved_interpretation_refs=refs)
    assert h.submit(b,current=cur,approved_interpretation_refs=(x['trusted'],))
    fake=dump_contract(b);fake['interpretationApprovals']=[{'actorType':'USER','approved':True}]
    with pytest.raises(ValueError):SpecializedAssetBible.model_validate(fake)


@pytest.mark.parametrize('stale',['ref','source_ref','approval_ref'])
def test_stale_interpretation_evidence_or_approval(tmp_path: Path, stale: str) -> None:
    x=blocker_case(tmp_path);cur=x['current'];cur[x['c'][stale].key]='f'*64
    with pytest.raises(ValueError,match='STALE'):
        x['host'].submit(x['candidate'],current=cur,approved_interpretation_refs=(x['trusted'],))


@pytest.mark.parametrize('change',['scope','subjectFingerprint','evidenceFingerprint'])
def test_even_trusted_wrong_receipt_cannot_change_scope_or_version(tmp_path: Path, change: str) -> None:
    x=blocker_case(tmp_path);h=x['host'];cur=x['current'];c=x['c'];old=x['trusted']
    raw=deepcopy(c['artifacts'][old.key]);raw[change]={'kind':'SCENE','refs':['other-scene']} if change=='scope' else 'f'*64
    new=h.store.put(old.key,raw);cur[new.key]=new.fingerprint
    char=x['character'];r=char.content[0];u=r.interpretation_uses[0].model_copy(update={'approval_ref':new})
    r=r.model_copy(update={'interpretation_uses':(u,), 'source_refs':tuple(new if p==old else p for p in r.source_refs)})
    char=char.model_copy(update={'content':(r,), 'status':'READY_FOR_REVIEW','approval_refs':(), 'approved_by':()})
    o,current=h._inputs(x['candidate'],cur);o[new.key]=raw
    with pytest.raises(ValueError,match='SCOPE_OR_VERSION_MISMATCH'):
        validate_bible(char,o,current,approved_interpretation_refs=(new,))


@pytest.mark.parametrize('asset,department',[('char','character-art'),('coat','costume-design')])
def test_compile_records_and_original_replay_revalidate(tmp_path: Path,asset: str,department: str) -> None:
    x=submitted(tmp_path);h=x['host'];cur=x['current'];refs=(x['trusted'],)
    out=h.compile(x['ref'],asset,current=cur,approved_interpretation_refs=refs)
    o,c=h._inputs(x['candidate'],cur)
    assert provider_projection(out['compilation'],o,c,approved_interpretation_refs=refs)==out['projection']
    replay_calls: list[Callable[[], Any]] = [lambda:h.compile(x['ref'],asset,current=cur),lambda:provider_projection(out['compilation'],o,c),
                 lambda:h.department_records(x['ref'],(asset,),department,current=cur)]
    for call in replay_calls:
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):call()
    records=h.department_records(x['ref'],(asset,),department,current=cur,approved_interpretation_refs=refs)
    assert records[0].source_refs==(x['ref'],)  # Original graph carries the exact InterpretationUse.
    cur[x['candidate'].runtime_ref.key]=x['candidate'].runtime_ref.fingerprint
    key='bible:baseline-'+department
    base=CreativeBible.model_validate(h.store.read_ref(SourcePin(key=key,kind='DESIGN',fingerprint=cur[key])))
    view=base.model_copy(update={'id':'projected-'+department,'status':'READY_FOR_REVIEW','not_required_reason':None,'content':records})
    professional=ProfessionalDepartmentHost(tmp_path)
    assert professional.submit(department,view,current=cur,approved_interpretation_refs=refs)['validationStatus']=='PASS'
    ref=bible_pin(view);cur[ref.key]=ref.fingerprint
    originals=professional._artifacts((ref,))
    assert x['c']['ref'].key in originals and x['trusted'].key in originals
    assert originals[x['character'].content[0].interpretation_uses[0].interpretation_ref.key]==x['c']['item']
    assert validate_bible(view,originals,cur,approved_interpretation_refs=refs)['validationStatus']=='PASS'
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        professional.submit(department,view,current=cur)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):validate_bible(view,originals,cur)
    from test_professional_departments import baseline, rebind, package_fixture
    bibles,artifacts,current=baseline()  # type: ignore[no-untyped-call]
    bibles={k:v.model_copy(update={'id':'package-'+k}) for k,v in bibles.items()}
    rebind(bibles,artifacts,current)  # type: ignore[no-untyped-call]
    artifacts.update(originals);current.update(cur);bibles[department]=view
    rebind(bibles,artifacts,current)  # type: ignore[no-untyped-call]
    package=package_fixture(bibles,artifacts,current)  # type: ignore[no-untyped-call]
    for key,value in artifacts.items():professional.store.put(key,value)
    assert professional.retain_package(package,current=current,approved_interpretation_refs=refs)['status']=='READY_FOR_PHASE_I_R2_USER_REVIEW'
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        professional.retain_package(package,current=current)
    for token in (x['c']['item']['meaning'],x['trusted'].key,'interpretationUses','confidence','approved_interpretation_refs'):
        assert token not in out['projection']['prompt']


def test_legacy_no_opt_in_and_stage_scope_preserved(tmp_path: Path) -> None:
    h,b,r,c=fixture(tmp_path)  # type: ignore[no-untyped-call]
    before=h.compile(r,'char',current=c)
    assert before==h.compile(r,'char',current=c,approved_interpretation_refs=())
    x=blocker_case(tmp_path/'opted');raw=dump_contract(x['candidate']);raw['assets'][0]['arcStage']='another-stage'
    with pytest.raises(ValueError,match='STAGE_MISMATCH'):
        x['host'].submit(SpecializedAssetBible.model_validate(raw),current=x['current'],approved_interpretation_refs=(x['trusted'],))


def test_production_replay_needs_fresh_external_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from drama_plugin.contracts.creation import Work
    from drama_plugin.hosts.specialized_asset import (require_production_visual_authority,
        compile_authority_context, validate_authority_context, validate_visual_submission, bind_video_request)
    from test_official_video_providers import request
    x=blocker_case(tmp_path,medium='cg');h=x['host'];b=x['candidate'];cur=x['current'];refs=(x['trusted'],)
    # Synthetic asset review only; never touches current-work approvals.
    review=h.store.put('asset-review:work',dict(kind='SPECIALIZED_ASSET_REVIEW',decision='APPROVE',workId='work',reviewer='offline',
        checkedBoundaries=['DRAMATURGY','DIRECTOR_INTENT','SOURCE_WORLD','GLOBAL_STYLE'],subjectFingerprint=fp(dump_contract(b,exclude={'approval_ref'}))))
    cur[review.key]=review.fingerprint;b=b.model_copy(update={'approval_ref':review})
    ref=h.submit(b,current=cur,approved_interpretation_refs=refs);cur[ref.key]=ref.fingerprint
    out=h.compile(ref,'char',current=cur,approved_interpretation_refs=refs)
    monkeypatch.setenv('DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT',str(tmp_path))
    work=Work(id='work',title='OFFLINE',content={'movieVisualMediumRef':dump_contract(b.runtime_ref),
        'specializedAssetCompilationRefs':[out['compilationRef']],'visualSourceCurrent':cur})
    assert require_production_visual_authority(work,approved_interpretation_refs=refs)
    intent={'prompt':'A person waits.'}
    context=compile_authority_context(work,intent,approved_interpretation_refs=refs)
    validate_authority_context(context,intent,approved_interpretation_refs=refs)
    missing_calls: list[Callable[[], Any]] = [lambda:require_production_visual_authority(work),lambda:validate_authority_context(context,intent)]
    for call in missing_calls:
        with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):call()
    # Forged candidate fields and persisted receipts are not an execution context.
    work.content['approved_interpretation_refs']=[dump_contract(x['trusted'])]
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):require_production_visual_authority(work)
    video=request()  # type: ignore[no-untyped-call]
    video.continuity.work_id='work'
    video=bind_video_request(work,video,approved_interpretation_refs=refs)
    validate_visual_submission(work,{'videoRequest':dump_contract(video)},approved_interpretation_refs=refs)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):
        validate_visual_submission(work,dump_contract(video))
    assert x['trusted'].key not in video.prompt and x['c']['item']['meaning'] not in video.prompt


@pytest.mark.parametrize('department,values',[
    ('character-dramaturgy',{'behavior_pattern':'careful movement'}),
    ('cinematography',{'camera_height':'shoulder height'}),
    ('lighting-design',{'source':'window daylight'}),
    ('sound-design',{'ambience':'quiet courtyard'}),
    ('editorial-design',{'rhythm':'hold the pause'})])
def test_generic_opted_in_consumers(tmp_path: Path, department: str, values: dict[str, Any]) -> None:
    from test_professional_departments import baseline, record, with_records, rebind
    from r3d_helpers import use
    b,a,cur=baseline()  # type: ignore[no-untyped-call]
    c=case(department=department);trusted=approval(c);a.update(c['artifacts']);cur.update(c['current'])
    row=record(values).model_copy(update={'source_refs':(c['ref'],trusted),'interpretation_uses':(use(c,values),)})  # type: ignore[no-untyped-call]
    b[department]=with_records(b[department],row)  # type: ignore[no-untyped-call]
    rebind(b,a,cur)  # type: ignore[no-untyped-call]
    host=ProfessionalDepartmentHost(tmp_path)
    for key,value in a.items():host.store.put(key,value)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):host.submit(department,b[department],current=cur)
    assert host.submit(department,b[department],current=cur,approved_interpretation_refs=(trusted,))['validationStatus']=='PASS'


def test_global_style_imaging_professional_context(tmp_path: Path) -> None:
    from drama_plugin.contracts.specialized_asset import GlobalVisualStyle, ImagingCharacterIntent
    from drama_plugin.specialized_asset import validate_assets
    from test_r3d_integration import consumer_graph, approve_bible
    from test_professional_departments import rebind
    h,b,_,cur=fixture(tmp_path)  # type: ignore[no-untyped-call]
    bibles,a,current,c=consumer_graph()
    bibles={k:v.model_copy(update={'id':'imaging-'+k}) for k,v in bibles.items()}
    rebind(bibles,a,current)  # type: ignore[no-untyped-call]
    bibles['cinematography']=approve_bible(bibles['cinematography'],a,current)
    rebind(bibles,a,current)  # type: ignore[no-untyped-call]
    for key,value in a.items():h.store.put(key,value)
    cur.update({k:v for k,v in current.items() if k not in cur});trusted=(c['approval_ref'],)
    style=GlobalVisualStyle.model_validate(h.store.read_ref(b.style_ref)).model_copy(update={'imaging_character':ImagingCharacterIntent(
        capture_character='Observed daylight',reason='Offline context propagation',source_refs=(bible_pin(bibles['cinematography']),))})
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):h.save_style(style,current=cur)
    ref=h.save_style(style,current=cur,approved_interpretation_refs=trusted);cur[ref.key]=ref.fingerprint
    b=b.model_copy(update={'style_ref':ref,'approval_ref':None})
    o,current=h._inputs(b,cur)
    validate_assets(b,o,current,approved_interpretation_refs=trusted)
    with pytest.raises(ValueError,match='USER_INTERPRETATION_APPROVAL_REQUIRED'):validate_assets(b,o,current)
    asset_ref=h.submit(b,current=cur,approved_interpretation_refs=trusted)
    retained=ProfessionalDepartmentHost(tmp_path)._artifacts((asset_ref,))
    validate_assets(b,retained,{**cur,b.runtime_ref.key:b.runtime_ref.fingerprint},approved_interpretation_refs=trusted)
