"""New cold start through actual Formal author adapters; all IO stays in-process."""
import copy
import json
import socket
import subprocess
import sys
from collections import Counter

import httpx
import pytest
from pydantic import TypeAdapter
from drama_plugin import DramaPlugin
from drama_plugin.config.loader import load_config
from drama_plugin.creative_engine.author_projection import (SYSTEM_FIELDS, author_payload, canon_schema,
    canon_projection, direction_schema, direction_projection, professional_schema, professional_projection)
from drama_plugin.creative_engine.contracts import CanonDraft, AuthorRequest, Kind, DesignBody
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure
from drama_plugin.film.contracts import FilmCanon, FilmDirection, FilmAuthorRequest
from drama_plugin.generation.contracts import PromptIR, PromptCoverage, FinalPromptArtifact, GenerationPreparation
from drama_plugin.execution.contracts import MediaBinding
from drama_plugin.runtime.contracts import RuntimeState
from test_formal_author_backends import ENV, SKILLS, request
from test_unified_planning_recovery import DOMAINS
from test_unified_mainline import video


def canon_dto(film=False):
    scene={'sceneText':'A traveler waits before making a request at a closed door.',
        'subjects':[{'name':'traveler','meaning':'The person seeking shelter.'}],
        'dialogue':[{'speakerSelection':0,'text':'Please open.','mustKeep':False}]}
    return {'work':{'interpretation':'A request remains unanswered.','dramaticIntent':'Observe a bounded appeal.','characterMeaning':'Shelter is needed.'},
        'script':{'screenplay':'Wait at the door, call, then listen.'}, 'scenes' if film else 'scene':[{'scene':scene}] if film else scene}


def direction_dto(film=False):
    shot={'purpose':'Observe the appeal.','requiredTransition':'Waiting becomes a request.','durationMs':60000,
        'subjectAction':'Wait, then make the canonical request.','entryState':'Before the request.','exitState':'The request remains unanswered.',
        'coverage':'The approved action.','blockingIntent':'Remain at the doorway.','cameraIntent':'Preserve the relation to the door.',
        'editingRelation':'Hold through the action.','performanceDirection':'Address the approved request.',
        'spokenSelections':[0],'professionalDomains':list(DOMAINS)}
    return {'shots':[{'sceneSelection':0,'shot':shot,'requiresSelections':[],'transition':'cut'}]} if film else shot


def professional_dto():
    baseline={'objective':'Seek shelter.','interactionTargetSelection':0,'tactic':'Make the approved appeal.',
        'authorityPosition':'No authority over the door.','relationshipStance':'Address the absent respondent.',
        'internalActivation':'LOW','externalControl':'HIGH','publicPrivateContext':'Public doorway.'}
    beat={'actorSelection':0,'targetSelection':0,'objective':'Seek shelter.','obstacle':'The closed door.',
        'tactic':'Wait before calling.','note':'Keep the approved action.','transitionTrigger':'Waiting ends.',
        'direction':{'objective':'Seek shelter.'},'physicalExpression':'Remain still before the request.'}
    facts={
      'ACTION':{'actionPhases':[{'beatSelection':0,'action':'Wait at the door.','entryState':'The request has not started.',
        'observable':'The waiting ends.','spokenSelections':[]},{'beatSelection':1,'action':'Make the approved request.',
        'entryState':'The waiting has ended.','observable':'The request remains unanswered.','spokenSelections':[0]}]},
      'CAMERA':{'movement':{'policy':'Keep the camera fixed.'},'lensIntention':'Preserve the spatial relationship.'},
      'LIGHTING':{'sources':['Visible doorway light.'],'directionAndQuality':'Soft sidelight.'},
      'COLOR':{'scenePalette':['Muted ochre.']},'EDITORIAL':{'temporalStructure':'Hold through the waiting.'},
      'WORLD':{'setting':'An enclosed historical doorway.'},
      'SUBJECTS':{'presentSubjects':[{'subjectSelection':0,'role':'The traveler seeking shelter.','inSceneBehaviour':'Remain before the door.'}]},
      'SOUND':{'ambience':[{'design':'Quiet air at the doorway.'}],'orderingRules':['Do not add speech.']},
      'REFERENCE':{'references':[{'priority':'PREFERRED','beatSelections':[1],'designPurpose':'Preserve doorway geography.','inputDuty':'World layout.'}]},
      'PERFORMANCE':{'sceneDPD':{'dramaticPurpose':'Make an unanswered appeal.','conflictCondition':'Shelter is unavailable.',
        'powerStructure':'No control over the door.','direction':baseline},'beats':[beat,{**beat,'tactic':'Make the approved request.',
        'transitionTrigger':'The request ends.','physicalExpression':'Address the closed door.'}],
        'lines':[{'spokenSelection':0,'beatSelection':1,'dramaticAction':'Ask for entry.','observableIntent':'Address the door.',
          'continuity':'Stay in place.','changeFromPrevious':'Waiting becomes a request.'}],
        'projectionSubjects':[{'subjectSelection':0,'role':'INTERACTIVE_PARTNER','beatSelections':[0,1],'objectives':['Seek shelter.']}]}}
    return [{'domain':d,'facts':facts[d]} for d in DOMAINS]


def raw_response(body):
    return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(body)}}]})


def model_paths(value, path=()):
    if isinstance(value,dict):
        for k,v in value.items():
            if k=='properties':
                for key,child in v.items():
                    yield path+(key,)
                    yield from model_paths(child,path+(key,))
            elif k not in {'description','default'}:yield from model_paths(v,path)
    elif isinstance(value,list):
        for child in value:yield from model_paths(child,path)


def test_all_model_schemas_have_no_system_owned_fields():
    for schema in (canon_schema(),canon_schema(film=True),direction_schema(),direction_schema(film=True),professional_schema()):
        paths=list(model_paths(schema))
        assert not any(p[-1] in SYSTEM_FIELDS for p in paths)
    assert len(professional_schema()['$defs']['SourceDomain']['enum'])==10


@pytest.mark.parametrize('field',['artifactRef','sourceRef','subjectRef','fingerprint','sourcePins','scope','mediaId'])
def test_invented_system_fields_cannot_enter_authority(field):
    req=AuthorRequest.model_validate(request('professional').model_copy(update={'shot':request('professional').shot.model_copy(update={'professional_domains':tuple(__import__('drama_plugin.production.contracts',fromlist=['SourceDomain']).SourceDomain(d) for d in DOMAINS)})}).model_dump())
    dto=professional_dto();dto[0]['facts'][field]='MODEL-INVENTED-IDENTITY'
    original=copy.deepcopy(dto)
    with pytest.raises(AuthorResultFailure) as caught:professional_projection(dto,req)
    assert 'AUTHOR_SYSTEM_FIELD_FORBIDDEN' in {i.code for i in caught.value.diagnostic.issues}
    assert dto==original and 'MODEL-INVENTED-IDENTITY' not in caught.value.diagnostic.model_dump_json()


def test_selection_from_candidates_and_restart_projection_identical(tmp_path):
    req=request();c=CanonDraft.model_validate(canon_projection(canon_dto(),req))
    direction_req=req.model_copy(update={'canon':c})
    shot=TypeAdapter(__import__('drama_plugin.creative_engine.contracts',fromlist=['ShotBody']).ShotBody).validate_python(direction_projection(direction_dto(),direction_req))
    req=direction_req.model_copy(update={'shot':shot})
    dto=professional_dto();fixed=professional_projection(dto,req)
    perf=next(v['facts'] for v in fixed if v['domain']=='PERFORMANCE')
    assert perf['projectionSubjects'][0]['subjectRef']==c.scene.subjects[0].id
    assert perf['projectionSubjects'][0]['spokenIds']==list(shot.spoken_ids)
    assert perf['lines'][0]['spokenContentId']==c.scene.dialogue[0].id
    body={'request':req.model_dump(mode='json',by_alias=True),'dto':dto}
    script='''import json,sys\nfrom drama_plugin.creative_engine.author_projection import professional_projection\nfrom drama_plugin.creative_engine.contracts import AuthorRequest\nd=json.load(sys.stdin)\nprint(json.dumps(professional_projection(d['dto'],AuthorRequest.model_validate(d['request'])),sort_keys=True))'''
    restored=json.loads(subprocess.check_output([sys.executable,'-c',script],input=json.dumps(body).encode()))
    assert restored==fixed
    dto[0]['facts']['actionPhases'][0]['beatSelection']=99
    with pytest.raises(AuthorResultFailure,match='AUTHOR_SELECTION_NOT_IN_AUTHORITY'):professional_projection(dto,req)


@pytest.mark.asyncio
async def test_empty_formal_authors_to_exact_canonical_media_review(tmp_path,monkeypatch,video):
    from test_unified_cold_start_simulation import test_empty_source_to_canonical_media_and_exact_human_receipt
    import test_unified_cold_start_simulation as cold
    calls=[]; payloads=[]; plugins=[]
    def fresh_load(path,patch):
        def blocked(*args,**kwargs):raise AssertionError('Network prohibited in reconciliation')
        patch.setattr(socket.socket,'connect',blocked);patch.setattr(socket.socket,'connect_ex',blocked)
        cfg=load_config(environment=ENV)
        patch.setattr('drama_plugin.plugin.load_config',lambda _:cfg)
        plugin=DramaPlugin.load(ledger_path=path/'ledger.sqlite',creative_root=path/'owners',target_media_root=path/'cache',legacy_reads=False)
        def text(req):
            payload=json.loads(req.content);payloads.append(payload)
            role={'offline-canon-model':'canon','offline-direction-model':'direction','offline-professional-model':'professional'}[payload['model']]
            calls.append(role)
            return raw_response({'canon':canon_dto(True),'direction':direction_dto(True),'professional':professional_dto()}[role])
        plugin.creative.canon_author.client.transport=httpx.MockTransport(text)
        plugins.append(plugin)
        class CounterView:
            @property
            def calls(self):return calls
        return plugin,CounterView()
    monkeypatch.setattr(cold,'load',fresh_load)
    await test_empty_source_to_canonical_media_and_exact_human_receipt(tmp_path,monkeypatch,video,'PASS',False)
    p=plugins[0]; cp=p.film.store.checkpoint('native-film')
    assert calls==['canon','direction','professional']
    # Derive actual prepared identity from existing immutable artifacts, no new owner.
    with p.ledger.transaction() as db:
        raw=db.execute("select body_json from immutable_artifact where artifact_type='generation-preparation'").fetchone()[0]
    prepared=GenerationPreparation.model_validate_json(raw)
    assert len(prepared.task.owners.snapshot_pins)==1
    dpd=p.creative_versions.objects.read_ref(prepared.task.owners.dpd_pin)
    assert dpd['fullShotDPDCoverage']['status']=='PASS'
    final=p.generation_artifacts.get(prepared.final_prompt_ref,FinalPromptArtifact)
    coverage=p.generation_artifacts.get(final.coverage_ref,PromptCoverage)
    assert {entry.domain.value for entry in coverage.entries}>=set(DOMAINS)
    for sentinel in ('Wait at the door.','Keep the camera fixed.','Soft sidelight.','Muted ochre.',
        'Hold through the waiting.','An enclosed historical doorway.','The traveler seeking shelter.','Remain still before the request.'):
        assert sentinel in final.prompt_text
    assert 'Make the approved request.' not in final.prompt_text
    assert prepared.task.profile.requested_duration_ms==4000
    # Available model-specific projections share the same authoritative IR.
    # Reserved Provider families must remain unavailable, without generic repair.
    from drama_plugin.generation.contracts import AudioExecutionPlan
    from drama_plugin.generation.seedance import ModelPolicyCatalog, SeedanceTargetAdapter
    from drama_plugin.prompt_generators.registry import get_generator
    package=p.production_packages.get(prepared.source_package_ref)
    selected=await p.prompt_compiler.reader.operations.selected(package,prepared.task,p.prompt_compiler.reader)
    plan=p.generation_artifacts.get(prepared.audio_plan_ref,AudioExecutionPlan)
    projected=await p.prompt_compiler.projection.project(package,prepared.task,plan,selected)
    assert projected.ir is not None and not projected.diagnostics
    required={f.fact_id for f in projected.ir.facts if f.obligation=='EXECUTION_REQUIRED'}
    model_variants={}
    for model in ('seedance-2-fast','seedance-2-standard'):
        policy=ModelPolicyCatalog().policy(model);assert policy is not None
        generated=SeedanceTargetAdapter().generate(projected.ir,plan,policy=policy,input_mode=prepared.task.input_mode)
        covered={generated['target_mapping'][row['path']] for row in generated['atoms']}
        assert required<=covered
        assert len(generated['prompt'])<=policy.hard_limit
        model_variants[model]={'hardLimit':policy.hard_limit,'requiredFactIds':sorted(required)}
    for reserved in ('flux','vidu'):
        with pytest.raises(ValueError,match='MODEL_PROMPT_GENERATOR_NOT_IMPLEMENTED'):
            get_generator(reserved)
    assert all('artifactRef' not in json.dumps(json.loads(w['messages'][1]['content'])) for w in payloads)
    assert p.providers.memory.data.work is None
    receipt={'scenario':'Empty → Formal Canon → Direction → ten Professional → Candidate → simulated Adoption/Rights/Cost → Package/DPD/Reference → Preparation → simulated Provider → canonical Media → system Technical QA → simulated human receipt',
        'realNetworkAllowed':False,'authorAttempts':dict(Counter(calls)),'canonicalMediaRef':'canonical-service-media-1',
        'preparationRef':prepared.artifact_reference().model_dump(mode='json',by_alias=True),
        'finalPromptRef':final.artifact_reference().model_dump(mode='json',by_alias=True),
        'finalPromptFingerprint':final.fingerprint,'coverageByDomain':{
            d:[entry.model_dump(mode='json',by_alias=True) for entry in coverage.entries if entry.domain.value==d] for d in DOMAINS},
        'dpdCoverage':dpd['fullShotDPDCoverage'],'nativeAudio':prepared.task.profile.native_audio,
        'modelProjectionCoverage':model_variants,'reservedProviderFallbackUsed':False,
        'plannedDurationMs':p.production_packages.get(prepared.source_package_ref).generation_intent.duration_ms,
        'operationDurationMs':prepared.task.profile.requested_duration_ms,'simulatedProviderSubmissions':1,
        'simulatedCanonicalImports':1,'technicalReview':'PASS','humanReviewReceipt':'PASS_SIMULATED_USER',
        'noAuthorOutputSystemFields':True,'oldProductionInputUsed':False,'legacyWorkflowCalls':0}
    (tmp_path/'reconciliation-evidence.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))

@pytest.mark.parametrize('role',('canon','direction','professional'))
def test_no_internal_reference_output_in_any_author_role(role):
    req=request();dto=canon_dto()
    if role=='canon':
        dto['scene']['dialogue'][0]['id']='invented-spoken'
        with pytest.raises(AuthorResultFailure):canon_projection(dto,req)
    elif role=='direction':
        req=req.model_copy(update={'canon':CanonDraft.model_validate(canon_projection(dto,req))})
        out=direction_dto();out['spokenIds']=['invented-spoken']
        with pytest.raises(AuthorResultFailure):direction_projection(out,req)
    else:
        req=req.model_copy(update={'canon':CanonDraft.model_validate(canon_projection(dto,req))})
        from drama_plugin.creative_engine.contracts import ShotBody
        req=req.model_copy(update={'shot':ShotBody.model_validate(direction_projection(direction_dto(),req))})
        out=professional_dto();out[0]['facts']['artifactRef']='invented-asset'
        with pytest.raises(AuthorResultFailure):professional_projection(out,req)


def test_model_selection_never_filters_invalid_candidates_and_domain_semantics_preserved():
    req=request(); c=CanonDraft.model_validate(canon_projection(canon_dto(),req));req=req.model_copy(update={'canon':c})
    bad=direction_dto();bad['spokenSelections']=[0,99]
    with pytest.raises(AuthorResultFailure):direction_projection(bad,req)
    from drama_plugin.creative_engine.contracts import ShotBody
    req=req.model_copy(update={'shot':ShotBody.model_validate(direction_projection(direction_dto(),req))})
    authored=professional_dto();fixed=professional_projection(authored,req)
    for source, bound in zip(authored,fixed,strict=True):
        if source['domain'] in {'CAMERA','COLOR','EDITORIAL','LIGHTING','WORLD'}:assert source['facts']==bound['facts']
    ref=next(row['facts']['references'][0] for row in fixed if row['domain']=='REFERENCE')
    assert ref['priority']=='PREFERRED' and ref['inputDuty']=='World layout.'
    assert 'mediaId' not in ref and ref['beatIds']
    bad=copy.deepcopy(authored);bad[0]['facts']['actionPhases'][0]['beatSelection']=99
    bad[0]['facts']['actionPhases'][1]['spokenSelections']=[99]
    with pytest.raises(AuthorResultFailure) as caught:professional_projection(bad,req)
    assert len(caught.value.diagnostic.issues)==2


def test_subtitle_text_is_creative_but_language_and_source_hash_are_system_bound():
    from drama_plugin.creative_engine.contracts import VersionRef
    from drama_plugin.film.contracts import LanguageMetadata
    from test_formal_author_backends import REF, source
    req=FilmAuthorRequest(scope=request().scope,source=source().model_copy(update={'subtitle_languages':('zh',)}),
        languages=LanguageMetadata(source_document_language='en',original_work_language='ru',spoken_language='ru',authority_ref=REF),
        source_ref=VersionRef(identity='source-test',version=1,fingerprint='1'*64))
    dto=canon_dto(True);dto['scenes'][0]['subtitleLocalizations']=[{'spokenSelection':0,'subtitleLanguageSelection':0,'text':'请开门。'}]
    fixed=FilmCanon.model_validate(canon_projection(dto,req,film=True))
    subtitle=fixed.scenes[0].subtitle_localizations[0]
    from drama_plugin.contracts.base import sha256_canonical
    assert subtitle.dialogue_id==fixed.scenes[0].scene.dialogue[0].id
    assert subtitle.source_text_hash==sha256_canonical('Please open.') and subtitle.language=='zh'
    dto['scenes'][0]['subtitleLocalizations'][0]['sourceTextHash']='invented-hash'
    with pytest.raises(AuthorResultFailure):canon_projection(dto,req,film=True)


def test_destination_selection_cannot_gain_interactive_obligations():
    from drama_plugin.creative_engine.contracts import ShotBody
    from drama_plugin.creative_engine.backends import validate_professional_facts
    req=request();dto=canon_dto();dto['scene']['subjects'].append({'name':'distant figure','meaning':'Presence only; no authored response.'})
    c=CanonDraft.model_validate(canon_projection(dto,req));req=req.model_copy(update={'canon':c})
    req=req.model_copy(update={'shot':ShotBody.model_validate(direction_projection(direction_dto(),req))})
    pro=professional_dto();performance=next(d['facts'] for d in pro if d['domain']=='PERFORMANCE')
    performance['projectionSubjects'].append({'subjectSelection':1,'role':'NON_INTERACTIVE_DESTINATION','beatSelections':[0],
        'spatialPresenceOnly':True,'behaviorExpansionForbidden':True})
    fixed=TypeAdapter(tuple[DesignBody,...]).validate_python(professional_projection(pro,req))
    validate_professional_facts(fixed,req)
    dest=next(d.facts for d in fixed if d.domain=='PERFORMANCE')['projectionSubjects'][1]
    assert dest['subjectRef']==c.scene.subjects[1].id and dest['spokenIds']==[]
    performance['projectionSubjects'][1]['authoredResponses']=['Respond to the traveler.']
    invalid=TypeAdapter(tuple[DesignBody,...]).validate_python(professional_projection(pro,req))
    with pytest.raises(AuthorResultFailure):validate_professional_facts(invalid,req)


def test_corrective_feedback_uses_the_same_authority_menus_not_machine_ids():
    from drama_plugin.creative_engine.author_projection import author_feedback, identity
    from drama_plugin.creative_engine.diagnostics import failure
    from drama_plugin.creative_engine.contracts import ShotBody
    req=request();c=CanonDraft.model_validate(canon_projection(canon_dto(),req))
    req=req.model_copy(update={'canon':c})
    req=req.model_copy(update={'shot':ShotBody.model_validate(direction_projection(direction_dto(),req))})
    beat=identity('beat',[req.scope.work_id,req.scope.scene_id,req.scope.shot_id],0)
    diagnostic=failure('DTO_SCHEMA','PROFESSIONAL_PARTNER_DPD_REQUIRED',role='professional',
        field_path=('facts','projectionSubjects'),validator='FormalProfessionalAuthor.interactive_coverage',
        reason='BEAT_ACTOR_MISSING',missing_subject_id=c.scene.subjects[0].id,beat_id=beat,
        expected_coverage_role='INTERACTIVE_PARTNER',allowed_spoken_ids=(c.scene.dialogue[0].id,))
    feedback=author_feedback(diagnostic,req)
    assert feedback['missingSubjectSelection']==0 and feedback['beatSelection']==0
    assert feedback['issues'][0]['allowedSpokenSelections']==[0]
    serialized=json.dumps(feedback)
    assert not any(v in serialized for v in (c.scene.subjects[0].id,c.scene.dialogue[0].id,beat))
    assert diagnostic.missing_subject_id==c.scene.subjects[0].id
