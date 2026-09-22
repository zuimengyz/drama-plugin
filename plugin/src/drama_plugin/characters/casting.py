"""Package-only casting projection; no legacy profile, personality defaults or provider calls."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal
import json
from pydantic import Field
from drama_plugin.contracts.base import ContractModel, dump_contract, sha256_canonical
from drama_plugin.contracts.creative_asset import Text, Hash
from drama_plugin.contracts.character_package import CharacterPackageRef, Route
from drama_plugin.contracts.character_prompt import FactDomain
from drama_plugin.contracts.visual_medium import VisualMediumIntent, CastingMode, legacy_medium_intent, medium_route
from drama_plugin.visual_medium import compile_character_art, VERSION
from drama_plugin.full_body_casting import CastingExecutionAuthorization
from drama_plugin.hosts.artifact_io import native_io
from drama_plugin.hosts.casting_projection import full_body_seedream_projection
from .repository import CharacterRepository, digest

class PackageVisualParagraph(ContractModel):
    key: Text
    text: Text
    domain: FactDomain | None = None
    package_pointers: tuple[Text,...] = Field(min_length=1)
    interpretation: Literal['VISUAL_INTERPRETATION_NOT_NEW_CORE']

class PackageCastingProjection(ContractModel):
    character_package: CharacterPackageRef
    route: Route
    casting_mode: CastingMode
    visual_medium_intent: VisualMediumIntent | None = None
    framing: Literal['FULL_BODY']
    paragraphs: tuple[PackageVisualParagraph,...] = Field(min_length=1)
    scope_text: Text
    directive_ref: Text
    directive_hash: Hash

_ALLOWED = {'core','dramaticIdentity','visualExpression','actionSignature','antiDrift','performance','embodiment','historicalBasis'}
_REQUIRED = {'core','dramaticIdentity','visualExpression','actionSignature','antiDrift'}

def pointer_value(package: dict[str,Any], pointer: str) -> Any:
    parts=pointer.lstrip('/').split('/')
    if not pointer.startswith('/') or parts[0] not in _ALLOWED:
        raise ValueError('PACKAGE_ONLY_SOURCE_POINTER_REQUIRED')
    if parts[0]=='embodiment' and (len(parts)<2 or parts[1] not in ('rules','visualTheses')):
        raise ValueError('EMBODIMENT_REVIEW_MUST_NOT_ENTER_PROMPT')
    current: Any=package
    try:
        for key in parts: current=current[int(key)] if isinstance(current,list) else current[key]
    except (KeyError,IndexError,ValueError,TypeError):
        raise ValueError('CHARACTER_PACKAGE_SOURCE_POINTER_MISSING') from None
    return current

def compile_package_casting(repository: CharacterRepository, projection: PackageCastingProjection) -> dict[str,Any]:
    projection=PackageCastingProjection.model_validate(dump_contract(projection))
    if digest(Path(projection.directive_ref).read_bytes())!=projection.directive_hash:
        raise ValueError('CASTING_DIRECTIVE_CHANGED')
    package=repository.resolve_character_package(projection.character_package,consumer='character-art',purpose='CASTING',route=projection.route)
    if package.get('embodiment') is not None:
        from .embodiment import embodiment_handoff
        embodiment_handoff(repository,projection.character_package,consumer='performance-casting',purpose='CASTING',route=projection.route)
    # No Work expression bundles or old profile arguments exist on this interface.
    sources=[];covered=set();keys=set()
    for paragraph in projection.paragraphs:
        if paragraph.key in keys:raise ValueError('DUPLICATE_VISUAL_PARAGRAPH')
        keys.add(paragraph.key);pins=[]
        for pointer in paragraph.package_pointers:
            value=pointer_value(package,pointer);covered.add(pointer.split('/')[1])
            pins.append({'pointer':pointer,'sourceValue':value,'sourceFingerprint':sha256_canonical(value)})
        sources.append({'paragraph':paragraph.key,'text':paragraph.text,'sources':pins,'authority':paragraph.interpretation})
    if not _REQUIRED<=covered:raise ValueError('INCOMPLETE_PACKAGE_SOURCE_MAP')
    if package.get('embodiment') is not None and 'embodiment' not in covered:
        raise ValueError('EMBODIMENT_SOURCE_MAP_REQUIRED')
    legacy_intent = legacy_medium_intent(projection.route, projection.casting_mode)
    intent = projection.visual_medium_intent or legacy_intent
    if intent.visual_medium != legacy_intent.visual_medium or intent.casting_mode != projection.casting_mode:
        raise ValueError('PACKAGE_MEDIUM_ROUTE_OR_CASTING_MODE_MISMATCH')
    compiled = compile_character_art(intent, [
        {'id':'scope','domain':'rendering','text':projection.scope_text,'sources':['directive:'+projection.directive_hash]},
        *[{'id':'package.'+p.key,'text':p.text,'sources':list(p.package_pointers), **({'domain':p.domain} if p.domain else {})} for p in projection.paragraphs],
    ], legacy=projection.visual_medium_intent is None,
       source_intent='projection.visualMediumIntent' if projection.visual_medium_intent else 'legacy:projection.route')
    prompt=compiled['prompt']
    trace={'characterPackageRef':projection.character_package.character_package_ref,
           'characterPackageVersion':projection.character_package.character_package_version,
           'checksum':projection.character_package.checksum,'packageStatus':package['status'],
           'visualMediumCompilation':compiled['visualMediumCompilation'],'mediumGate':compiled['mediumGate'],
           'route':projection.route,'castingMode':projection.casting_mode,'framing':projection.framing,
           'scopeSource':{'directiveRef':projection.directive_ref,'directiveHash':projection.directive_hash,'text':projection.scope_text},
           'paragraphs':sources,'legacyProfileInputs':[],'coreFingerprint':sha256_canonical(package['core'])}
    return {**compiled,'purpose':'CHARACTER_FULL_BODY_CASTING','character':package['characterId'],
            'visualRoute':medium_route(intent),'visualLanguage':projection.route.upper(),
            'visualMedium':intent.visual_medium,'castingMode':intent.casting_mode,
            'sourceTrace':trace,'prompt':prompt,'promptFingerprint':sha256_canonical(prompt),
            'inputsFingerprint':sha256_canonical({'projection':dump_contract(projection),'compilerVersion':VERSION,'compiledPrompt':compiled['promptFingerprint']}),
            'status':'DESIGN_ONLY','userAdoption':'PENDING','maxOutputs':1}

def executable_package_casting(work: Any, repository: CharacterRepository, projection: PackageCastingProjection,
                               authorization_id: str) -> dict[str,Any]:
    brief=compile_package_casting(repository,projection)
    content=work.content;roster=content.get('characterPackageRoster',{})
    if (content.get('approval',{}).get('status')!='APPROVED' or content.get('visualRoute')!=brief['visualRoute']
        or content.get('visualLanguage')!=brief['visualLanguage'] or roster.get('sourceRevision')!=content.get('revisionId')):
        raise ValueError('CURRENT_APPROVED_WORK_ROUTE_REQUIRED')
    if content.get('visualMediumIntent') is not None and content['visualMediumIntent'] != brief['visualMediumIntent']:
        raise ValueError('CURRENT_WORK_MEDIUM_INTENT_MISMATCH')
    rows=[r for r in roster.get('characters',[]) if r['characterId']==brief['character']]
    if len(rows)!=1 or rows[0].get('package')!=dump_contract(projection.character_package):
        raise ValueError('CURRENT_WORK_PACKAGE_PIN_MISMATCH')
    package=repository.load_character_package(projection.character_package.character_package_ref,projection.character_package.character_package_version,checksum=projection.character_package.checksum)
    if package.manifest.source_work!=work.id or package.manifest.source_revision!=content['revisionId'] or package.core.identity!=rows[0]['name']:
        raise ValueError('PACKAGE_WORK_SOURCE_MISMATCH')
    auth=CastingExecutionAuthorization.model_validate(content.get('characterCastingAuthorizations',{}).get(authorization_id,{}))
    if (auth.authorization_id!=authorization_id or auth.work_id!=work.id or auth.work_revision!=content['revisionId']
        or auth.character!=brief['character'] or auth.inputs_fingerprint!=brief['inputsFingerprint'] or auth.status!='AUTHORIZED'
        or auth.directive_hash!=projection.directive_hash or auth.directive_ref!=projection.directive_ref):
        raise ValueError('CASTING_AUTHORIZATION_STALE_OR_CONSUMED')
    return {**brief,'status':'EXECUTABLE_SINGLE_CANDIDATE','workId':work.id,'workRevision':content['revisionId'],
            'authorizationId':authorization_id,'stopAfterFirstResult':True,'referenceMediaIds':[],
            'executionRoute':'QUALIFIED_HOST_VISUAL_MCP'}

async def reserve_package_casting(memory: Any, work_id: str, repository: CharacterRepository,
                                  projection: PackageCastingProjection, authorization_id: str,
                                  request: dict[str,Any], ledger_root: Path) -> dict[str,Any]:
    ledger_root.mkdir(parents=True,exist_ok=True);key=sha256_canonical([work_id,authorization_id]);io=native_io()
    ledger=ledger_root/(key+'.json')
    with io.guard(ledger_root/(key+'.lock')):
        if ledger.exists():raise ValueError('CASTING_ATTEMPT_ALREADY_RESERVED_RECOVER_ONLY')
        work=await memory.get_work(work_id)
        from drama_plugin.creative_source import production_gate
        production_gate(work.content, work.content.get('productionJurisdiction'))
        from drama_plugin.hosts.specialized_asset import validate_visual_submission
        validate_visual_submission(work, request)
        brief=executable_package_casting(work,repository,projection,authorization_id)
        if (request.get('transport')!='MCP' or request.get('mock') is not False or request.get('modality')!='IMAGE'
            or request.get('outputCount')!=1 or request.get('prompt')!=brief['prompt'] or not request.get('durableCompletionAvailable')):
            raise ValueError('QUALIFIED_SINGLE_IMAGE_REQUEST_REQUIRED')
        expected=full_body_seedream_projection(brief,request['capabilityEvidence'],seed=request['seed'])
        if request.get('providerRequest')!=expected:raise ValueError('CASTING_PROVIDER_PROJECTION_CHANGED')
        record={'status':'RESERVED_SUBMISSION_OUTCOME_UNKNOWN','brief':brief,'request':request,'requestFingerprint':sha256_canonical(request)}
        io.write(ledger,json.dumps(record,ensure_ascii=False,indent=2))
        content=deepcopy(work.content);content['characterCastingAuthorizations'][authorization_id]['status']='RESERVED'
        content.setdefault('characterCastingAttempts',{})[authorization_id]=record
        await memory.save_work(work.id,work.title,content,work.description)
        fresh=await memory.get_work(work.id)
        if fresh.content['characterCastingAttempts'].get(authorization_id)!=record:raise ValueError('CASTING_RESERVATION_READBACK_FAILED')
        return record
