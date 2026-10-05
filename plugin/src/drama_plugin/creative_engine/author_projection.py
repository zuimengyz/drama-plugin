"""Ephemeral model DTO projection. No store, workflow, authoring or external IO.

Models create semantic rows and select ordinal candidates, never infrastructure
identities. The exact authority request owns the ordinal map. Unknown selections
are rejected; projections never repair, filter or invent creative facts.
"""
from __future__ import annotations
from copy import deepcopy
from drama_plugin.config.text_composition import AuthorRole
from pydantic import JsonValue, TypeAdapter
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import AuthorRequest, CanonDraft, SceneBody
from drama_plugin.creative_engine.diagnostics import AuthorDiagnostic, AuthorResultFailure, aggregate_failures, failure
from drama_plugin.film.contracts import FilmAuthorRequest
from drama_plugin.professional_design.provenance import MANAGED_FIELDS

JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
SYSTEM_FIELDS = frozenset({*MANAGED_FIELDS, 'artifactRef', 'subjectRef', 'sourceRef', 'mediaId',
    'storageId', 'contentHash', 'owner', 'version', 'fingerprint', 'hash', 'provenance',
    'adoptionDecisionRef', 'packageRef', 'dpdSnapshotRef', 'identity', 'id', 'beatId', 'beatIds',
    'spokenId', 'spokenIds', 'spokenContentId', 'eventId', 'targetEventId', 'speaker', 'actor', 'sceneId', 'shotId', 'sourceFingerprint'})
TEXT: dict[str, JsonValue] = {'type': 'string', 'minLength': 1}
SELECT: dict[str, JsonValue] = {'type': 'integer', 'minimum': 0, 'maximum': 99,
    'description': 'Choose an ordinal from the supplied legal candidates; never construct an internal identifier.'}


def obj(fields: dict[str, JsonValue], required: tuple[str, ...] | None = None) -> dict[str, JsonValue]:
    return {'type': 'object', 'properties': fields, 'required': list(required if required is not None else fields), 'additionalProperties': False}


def arr(item: dict[str, JsonValue], minimum: int = 0, maximum: int = 100) -> dict[str, JsonValue]:
    return {'type': 'array', 'items': item, 'minItems': minimum, 'maxItems': maximum}


def identity(kind: str, scope: object, ordinal: object) -> str:
    return kind + '-' + sha256_canonical([kind, scope, ordinal])[:24]


def object_value(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError('AUTHOR_PROJECTION_OBJECT_REQUIRED')
    return value


def sequence(value: JsonValue) -> list[JsonValue]:
    if not isinstance(value, list):
        raise ValueError('AUTHOR_PROJECTION_ARRAY_REQUIRED')
    return value


def select(value: JsonValue, candidates: list[JsonValue], path: tuple[str | int, ...], role: AuthorRole) -> JsonValue:
    if type(value) is not int or not 0 <= value < len(candidates):
        raise AuthorResultFailure(failure('DIALOGUE_AUTHORITY', 'AUTHOR_SELECTION_NOT_IN_AUTHORITY',
            role=role, field_path=path, validator='authority_candidate_selection'))
    return candidates[value]


def check(value: JsonValue, schema: dict[str, JsonValue], role: AuthorRole) -> None:
    """Collect model-shape failures before any identity projection, without echoing values."""
    definitions = schema.get('$defs', {})
    assert isinstance(definitions, dict)
    findings = []
    def walk(v: JsonValue, c: dict[str, JsonValue], path: tuple[str | int, ...]) -> None:
        ref = c.get('$ref')
        if isinstance(ref, str):
            target = definitions[ref.rsplit('/', 1)[1]]
            assert isinstance(target, dict)
            walk(v, target, path); return
        alternatives = c.get('anyOf')
        if isinstance(alternatives, list):
            # Pydantic checks the exact semantic alternatives after projection.
            for alternative in alternatives:
                if isinstance(alternative, dict) and (alternative.get('type') == 'null' and v is None
                        or alternative.get('type') == 'string' and isinstance(v, str)
                        or alternative.get('type') == 'array' and isinstance(v, list)
                        or alternative.get('type') == 'object' and isinstance(v, dict)):
                    walk(v, alternative, path); return
            if v is None and c.get('default') is None: return
        kind = c.get('type')
        lower, upper = c.get('minimum'), c.get('maximum')
        bad = (kind == 'string' and (not isinstance(v, str) or not v.strip())
            or kind == 'integer' and (type(v) is not int or isinstance(lower,int) and v < lower or isinstance(upper,int) and v > upper)
            or kind == 'boolean' and type(v) is not bool
            or kind == 'object' and not isinstance(v, dict)
            or kind == 'array' and not isinstance(v, list)
            or 'enum' in c and v not in sequence(c['enum']))
        if bad:
            findings.append(failure('DTO_SCHEMA', 'AUTHOR_MODEL_FIELD_INVALID', role=role,
                field_path=path, validator='model_semantic_contract')); return
        if isinstance(v, dict):
            properties = object_value(c.get('properties', {}))
            required = sequence(c.get('required', []))
            for key in required:
                if isinstance(key, str) and key not in v:
                    findings.append(failure('DTO_SCHEMA', 'AUTHOR_MODEL_FIELD_REQUIRED', role=role,
                        field_path=(*path,key), validator='model_semantic_contract'))
            for key, child in v.items():
                if key in SYSTEM_FIELDS or c.get('additionalProperties') is False and key not in properties:
                    findings.append(failure('DTO_SCHEMA', 'AUTHOR_SYSTEM_FIELD_FORBIDDEN', role=role,
                        field_path=(*path,key if key in SYSTEM_FIELDS else '<extra>'), validator='system_field_ownership')); continue
                contract = properties.get(key)
                if isinstance(contract, dict): walk(child, contract, (*path,key))
                else: reject_nested(child, (*path,key))
        elif isinstance(v, list):
            minimum, maximum = c.get('minItems',0), c.get('maxItems',100)
            assert isinstance(minimum,int) and isinstance(maximum,int)
            if len(v) < minimum or len(v) > maximum:
                findings.append(failure('DTO_SCHEMA','AUTHOR_MODEL_ARRAY_BOUND',role=role,field_path=path,validator='model_semantic_contract'))
            item = c.get('items')
            if isinstance(item, dict):
                for i, child in enumerate(v): walk(child,item,(*path,i))
    def reject_nested(v: JsonValue, path: tuple[str | int, ...]) -> None:
        if isinstance(v,dict):
            for key, child in v.items():
                if key in SYSTEM_FIELDS or key in {'id','beatId','spokenId','spokenIds','speaker','actor','eventId','targetEventId','beatIds'}:
                    findings.append(failure('DTO_SCHEMA','AUTHOR_SYSTEM_FIELD_FORBIDDEN',role=role,field_path=(*path,key),validator='system_field_ownership'))
                reject_nested(child,(*path,key))
        elif isinstance(v,list):
            for i,child in enumerate(v): reject_nested(child,(*path,i))
    walk(value,schema,())
    if findings: raise AuthorResultFailure(aggregate_failures(tuple(findings)))


def canon_schema(*, film: bool = False) -> dict[str, JsonValue]:
    from drama_plugin.creative_engine.contracts import WorkBody, ScriptBody
    work = JSON.validate_python(TypeAdapter(WorkBody).json_schema(by_alias=True)); script = JSON.validate_python(TypeAdapter(ScriptBody).json_schema(by_alias=True))
    scene = obj({'sceneText':TEXT,'subjects':arr(obj({'name':TEXT,'meaning':TEXT}),1),
        'dialogue':arr(obj({'speakerSelection':SELECT,'text':TEXT,'mustKeep':{'type':'boolean','default':False}},('speakerSelection','text')))})
    return obj({'work':work,'script':script, 'scenes' if film else 'scene':arr(obj({'scene':scene,
        'subtitleLocalizations':arr(obj({'spokenSelection':SELECT,'subtitleLanguageSelection':SELECT,'text':TEXT}))},('scene',)),1,12) if film else scene})


def canon_projection(value: JsonValue, request: AuthorRequest | FilmAuthorRequest, *, film: bool = False) -> JsonValue:
    check(value,canon_schema(film=film),'canon'); body=object_value(value)
    rows=sequence(body['scenes']) if film else [{'scene':body['scene']}]
    result: list[JsonValue]=[]
    for n,raw in enumerate(rows):
        row=object_value(raw); scene=object_value(row['scene'])
        sid=identity('scene',request.scope.work_id,n) if film else request.scope.scene_id
        subjects: list[JsonValue]=[]
        names=set()
        for raw_subject in sequence(scene['subjects']):
            subject=object_value(raw_subject); name=subject['name']
            if name in names: raise AuthorResultFailure(failure('DTO_SCHEMA','CANON_SUBJECT_DUPLICATE',role='canon',validator='canon_subject_inventory'))
            assert isinstance(name,str); names.add(name)
            subjects.append({'id':identity('subject',request.scope.work_id,name),**subject})
        dialogue: list[JsonValue]=[]
        for i,raw_line in enumerate(sequence(scene['dialogue'])):
            line=object_value(raw_line)
            subject=object_value(select(line['speakerSelection'],subjects,('dialogue',i,'speakerSelection'),'canon'))
            dialogue.append({'id':identity('spoken',[request.scope.work_id,sid],i),'speaker':subject['id'],
                **{k:v for k,v in line.items() if k!='speakerSelection'}})
        localizations: list[JsonValue]=[]
        for raw_local in sequence(row.get('subtitleLocalizations',[])):
            local=object_value(raw_local)
            spoken=object_value(select(local['spokenSelection'],dialogue,('subtitleLocalizations','spokenSelection'),'canon'))
            language=select(local['subtitleLanguageSelection'],list(request.source.subtitle_languages),('subtitleLocalizations','subtitleLanguageSelection'),'canon')
            localizations.append({'dialogueId':spoken['id'],'sourceTextHash':sha256_canonical(spoken['text']),'language':language,'text':local['text']})
        result.append({'sceneId':sid,'scene':{'sceneText':scene['sceneText'],'subjects':subjects,'dialogue':dialogue},
            **({'subtitleLocalizations':localizations} if localizations else {})})
    return {'work':body['work'],'script':body['script'], 'scenes' if film else 'scene':result if film else object_value(result[0])['scene']}


def direction_schema(*, film: bool = False) -> dict[str, JsonValue]:
    from drama_plugin.creative_engine.contracts import ShotBody
    schema=JSON.validate_python(TypeAdapter(ShotBody).json_schema(by_alias=True)); assert isinstance(schema,dict)
    schema=deepcopy(schema); properties=object_value(schema['properties'])
    properties.pop('spokenIds'); properties['spokenSelections']=arr(SELECT)
    domains=object_value(properties['professionalDomains'])
    from drama_plugin.production.contracts import SourceDomain
    domains['items']={'type':'string','enum':[d.value for d in sorted(SourceDomain) if d.value not in {'CANON','DIRECTION'}]}
    domains['uniqueItems']=True
    domains['description']='Downstream professional needs, once each in lexicographic order; not Canon or Direction ownership.'
    schema.pop('$defs',None)
    if film:
        return obj({'shots':arr(obj({'sceneSelection':SELECT,'shot':schema,'requiresSelections':arr(SELECT,0,4),
            'transition':{'type':'string','enum':['cut'],'default':'cut'}},('sceneSelection','shot')),1,12)})
    return schema


def direction_projection(value: JsonValue, request: AuthorRequest | FilmAuthorRequest, *, film: bool = False) -> JsonValue:
    check(value,direction_schema(film=film),'direction')
    assert request.canon is not None
    if not film:
        assert isinstance(request.canon,CanonDraft)
        row=object_value(value)
        lines=JSON.validate_python([line.model_dump(mode='json',by_alias=True) for line in request.canon.scene.dialogue]); assert isinstance(lines,list)
        return {**{k:v for k,v in row.items() if k!='spokenSelections'},'spokenIds':[
            object_value(select(v,lines,('spokenSelections',i),'direction'))['id'] for i,v in enumerate(sequence(row.get('spokenSelections',[])))]}
    assert isinstance(request,FilmAuthorRequest) and request.canon is not None
    result: list[JsonValue]=[]
    scenes=JSON.validate_python([s.model_dump(mode='json',by_alias=True) for s in request.canon.scenes]); assert isinstance(scenes,list)
    for i,raw in enumerate(sequence(object_value(value)['shots'])):
        row=object_value(raw); scene=object_value(select(row['sceneSelection'],scenes,('shots',i,'sceneSelection'),'direction'))
        shot=object_value(row['shot']); lines=sequence(object_value(scene['scene'])['dialogue'])
        requires=[object_value(select(v,result,('shots',i,'requiresSelections'),'direction'))['shotId'] for v in sequence(row.get('requiresSelections',[]))]
        result.append({'sceneId':scene['sceneId'],'shotId':identity('shot',request.scope.work_id,i),
            'requires':requires,'transition':row.get('transition','cut'),'shot':{
                **{k:v for k,v in shot.items() if k!='spokenSelections'},'spokenIds':[
                    object_value(select(v,lines,('shots',i,'shot','spokenSelections',j),'direction'))['id'] for j,v in enumerate(sequence(shot.get('spokenSelections',[])))]}})
    return {'shots':result}


def subjects(scene: SceneBody) -> list[dict[str, JsonValue]]:
    if scene.subjects:
        return [object_value(JSON.validate_python(s.model_dump(mode='json',by_alias=True))) for s in scene.subjects]
    # Historical canonical input may be read: these IDs already belong to Canon,
    # never inferred from Professional prose or matched approximately.
    return [{'id':speaker,'name':speaker,'meaning':'Canonical dialogue speaker'} for speaker in dict.fromkeys(line.speaker for line in scene.dialogue)]


def professional_schema() -> dict[str, JsonValue]:
    from drama_plugin.creative_engine.backends import professional_validation_schema
    schema=professional_validation_schema(); definitions=object_value(schema['$defs'])
    design=object_value(definitions['DesignBody']); facts=object_value(object_value(design['properties'])['facts'])
    # Closed semantic row contracts remain professional-specific.
    optional_fields = {
        'ACTION': ('physicalStateConstraints',), 'CAMERA': ('cameraPosition','height','pointOfView','lensIntention','axisAndScreenDirection'),
        'WORLD': ('weather','time','physicalWorldRules'), 'SUBJECTS': ('identityConstraints','absences'),
        'SOUND': ('contactTiedSound','dialogueAndLegibility','silence','acousticSpace'),
        'LIGHTING': ('intensityRatios','constraints','nightContinuity'), 'COLOR': ('arc','constraints'),
        'EDITORIAL': ('compression','protectedEvents','spatialOrientation'), 'PERFORMANCE': (), 'REFERENCE': ()}
    layer=object_value(definitions['DPDLayerState']); layer_properties=object_value(layer['properties'])
    layer_properties.pop('interactionTarget',None);layer_properties['interactionTargetSelection']={**SELECT,'default':None}
    layer['required']=[k for k in sequence(layer.get('required',[])) if k!='interactionTarget']
    for conditional in sequence(design['allOf']):
        contract=object_value(object_value(object_value(conditional)['then'])['properties'])['facts']; assert isinstance(contract,dict)
        domain=object_value(object_value(object_value(object_value(conditional)['if'])['properties'])['domain'])['const']
        props=object_value(contract['properties'])
        contract['additionalProperties']=False
        assert isinstance(domain,str)
        for name in optional_fields[domain]:props[name]={'$ref':'#/$defs/JsonValue'}
        def rename(c:dict[str,JsonValue], old:str, new:str, replacement:dict[str,JsonValue]) -> None:
            p=object_value(c['properties']); p.pop(old,None);p[new]=replacement
            c['required']=[new if k==old else k for k in sequence(c.get('required',[]))]
        if domain=='SUBJECTS':
            row=object_value(object_value(props['presentSubjects'])['items']); rename(row,'id','subjectSelection',SELECT)
        if domain=='ACTION':
            row=object_value(object_value(props['actionPhases'])['items']);rename(row,'beatId','beatSelection',SELECT);rename(row,'spokenIds','spokenSelections',arr(SELECT))
        if domain=='REFERENCE':
            row=object_value(object_value(props['references'])['items']);p=object_value(row['properties']);p.pop('id');row['required']=[k for k in sequence(row['required']) if k!='id'];rename(row,'beatIds','beatSelections',arr(SELECT))
        if domain=='SOUND':
            row=object_value(object_value(props['speechRelations'])['items']);rename(row,'eventId','spokenSelection',SELECT);rename(row,'targetEventId','targetSpokenSelection',SELECT)
        if domain=='PERFORMANCE':
            scene=object_value(props['sceneDPD']); direction=object_value(object_value(scene['properties'])['direction'])
            p=object_value(direction['properties']);p.pop('interactionTarget',None);p['interactionTargetSelection']=SELECT
            direction['required']=['interactionTargetSelection' if k=='interactionTarget' else k for k in sequence(direction['required'])]
            beat=object_value(object_value(props['beats'])['items']);p=object_value(beat['properties']);
            for old in ('id','actor','target'): p.pop(old,None)
            beat['required']=[k for k in sequence(beat['required']) if k not in {'id','actor','target'}]
            p.update({'actorSelection':SELECT,'targetSelection':SELECT});beat['required']=[*sequence(beat['required']),'actorSelection','targetSelection']
            line=object_value(object_value(props['lines'])['items']);rename(line,'beatId','beatSelection',SELECT);rename(line,'spokenContentId','spokenSelection',SELECT)
            subject=object_value(object_value(props['projectionSubjects'])['items']);p=object_value(subject['properties'])
            for old in ('subjectRef','sourceTargetLabel','spokenIds'): p.pop(old,None)
            subject['required']=[k for k in sequence(subject['required']) if k not in {'subjectRef','sourceTargetLabel','spokenIds'}]
            rename(subject,'beatIds','beatSelections',arr(SELECT,1));p['subjectSelection']=SELECT;subject['required']=[*sequence(subject['required']),'subjectSelection']
        # Embedded optional playability/response interpretation objects contain
        # old machine references; they belong to their owners, not this author.
        def remove_infrastructure(c:JsonValue) -> None:
            if isinstance(c,dict):
                p=c.get('properties')
                if isinstance(p,dict):
                    for key in ('playability','responseInterpretations','schemaVersion','scope','sceneId','sourceFingerprint','speaker'):
                        p.pop(key,None)
                    c['required']=[k for k in sequence(c.get('required',[])) if k in p]
                for child in list(c.values()):remove_infrastructure(child)
            elif isinstance(c,list):
                for child in c:remove_infrastructure(child)
        remove_infrastructure(contract)
    facts['description']='Author semantic professional facts and ordinal selections only. System binds all exact identities and provenance. Never emit internal IDs or refs.'
    # Only referenced definitions, not misleading unused identity DTOs.
    used={'DesignBody','SourceDomain','JsonValue'}
    def refs(v:JsonValue) -> None:
        if isinstance(v,dict):
            ref=v.get('$ref')
            if isinstance(ref,str):
                name=ref.rsplit('/',1)[1]
                if name not in used: used.add(name);refs(definitions[name])
            for child in v.values():refs(child)
        elif isinstance(v,list):
            for child in v:refs(child)
    refs(design)
    schema['$defs']={k:v for k,v in definitions.items() if k in used}
    return schema


def professional_projection(value: JsonValue, request: AuthorRequest) -> JsonValue:
    assert request.canon is not None and request.shot is not None
    # Validate each domain's specific model facts, with collective findings.
    schema=professional_schema(); defs=object_value(schema['$defs']); design_schema=object_value(defs['DesignBody'])
    findings=[]
    raw_rows=sequence(value)
    requested=tuple(d.value for d in request.shot.professional_domains)
    actual=tuple(r.get('domain') for r in raw_rows if isinstance(r,dict))
    from drama_plugin.production.contracts import SourceDomain
    for expected_domain in sorted(set(requested) | {d for d in actual if isinstance(d,str)}):
        if actual.count(expected_domain)!=requested.count(expected_domain):
            findings.append(failure('DTO_SCHEMA','PROFESSIONAL_DOMAIN_AUTHORITY_MISMATCH',role='professional',
                field_path=('domain',),validator='FormalProfessionalAuthor.required_domains',
                domain=SourceDomain(expected_domain) if expected_domain in {d.value for d in SourceDomain} else None))
    for i,raw in enumerate(raw_rows):
        try:
            check(raw,{'$defs':defs,**design_schema},'professional')
            row=object_value(raw)
            for condition in sequence(design_schema['allOf']):
                cond=object_value(condition)
                domain=object_value(object_value(object_value(cond['if'])['properties'])['domain'])['const']
                if row.get('domain')==domain:
                    c=object_value(object_value(cond['then'])['properties'])['facts'];assert isinstance(c,dict)
                    check(row['facts'],{'$defs':defs,**c},'professional')
        except AuthorResultFailure as error: findings.append(error.diagnostic)
    roster=JSON.validate_python(subjects(request.canon.scene)); assert isinstance(roster,list)
    spoken=JSON.validate_python([line.model_dump(mode='json',by_alias=True) for line in request.canon.scene.dialogue if line.id in request.shot.spoken_ids]); assert isinstance(spoken,list)
    rows=[object_value(r) for r in raw_rows if isinstance(r,dict)]
    performances=[r for r in rows if r.get('domain')=='PERFORMANCE' and isinstance(r.get('facts'),dict)]
    performance_facts=object_value(performances[0]['facts']) if len(performances)==1 else {}
    raw_beats=performance_facts.get('beats',[])
    beat_count=len(raw_beats) if isinstance(raw_beats,list) else 0
    sizes={'subjectSelection':len(roster),'actorSelection':len(roster),'targetSelection':len(roster),
        'interactionTargetSelection':len(roster),'spokenSelection':len(spoken),'spokenSelections':len(spoken),
        'targetSpokenSelection':len(spoken),'beatSelection':beat_count,'beatSelections':beat_count}
    def selection_findings(v:JsonValue,path:tuple[str|int,...],domain:str)->None:
        if isinstance(v,dict):
            for key,child in v.items():
                if key in sizes and child is not None:
                    choices=child if isinstance(child,list) else [child]
                    for offset,choice in enumerate(choices):
                        if type(choice) is not int or not 0<=choice<sizes[key]:
                            findings.append(failure('DIALOGUE_AUTHORITY','AUTHOR_SELECTION_NOT_IN_AUTHORITY',role='professional',
                                field_path=(*path,key,offset) if isinstance(child,list) else (*path,key),
                                validator='authority_candidate_selection',domain=SourceDomain(domain) if domain in {d.value for d in SourceDomain} else None))
                elif child is not None:selection_findings(child,(*path,key),domain)
        elif isinstance(v,list):
            for index,child in enumerate(v):selection_findings(child,(*path,index),domain)
    for index,row in enumerate(rows):
        d=row.get('domain')
        if isinstance(d,str):selection_findings(row.get('facts'),(index,'facts'),d)
    if findings: raise AuthorResultFailure(aggregate_failures(tuple(findings)))
    beat_ids: list[JsonValue]=[identity('beat',[request.scope.work_id,request.scope.scene_id,request.scope.shot_id],i) for i in range(beat_count)]
    def choose(v:JsonValue, menu:list[JsonValue], key:str)->JsonValue:return select(v,menu,(key,),'professional')
    output: list[JsonValue]=[]
    for row in rows:
        facts=deepcopy(object_value(row['facts']));domain=row['domain']
        def bind_targets(v:JsonValue)->JsonValue:
            if isinstance(v,dict):
                result={k:bind_targets(child) for k,child in v.items() if k!='interactionTargetSelection'}
                if 'interactionTargetSelection' in v and v['interactionTargetSelection'] is not None:
                    result['interactionTarget']=object_value(choose(v['interactionTargetSelection'],roster,'interactionTargetSelection'))['name']
                return result
            if isinstance(v,list):return [bind_targets(child) for child in v]
            return v
        facts=object_value(bind_targets(facts))
        if domain=='PERFORMANCE':
            beats: list[JsonValue]=[]
            for i,raw in enumerate(sequence(facts['beats'])):
                b=object_value(raw); actor=object_value(choose(b['actorSelection'],roster,'actorSelection'));target=object_value(choose(b['targetSelection'],roster,'targetSelection'))
                beats.append({**{k:v for k,v in b.items() if k not in {'actorSelection','targetSelection'}},'id':beat_ids[i],'actor':actor['id'],'target':target['name']})
            facts['beats']=beats
            lines: list[JsonValue]=[]
            for raw in sequence(facts['lines']):
                line=object_value(raw); canon=object_value(choose(line['spokenSelection'],spoken,'spokenSelection'))
                lines.append({**{k:v for k,v in line.items() if k not in {'spokenSelection','beatSelection'}},'spokenContentId':canon['id'],'beatId':choose(line['beatSelection'],beat_ids,'beatSelection')})
            facts['lines']=lines
            projections: list[JsonValue]=[]
            for raw in sequence(facts['projectionSubjects']):
                s=object_value(raw); chosen=object_value(choose(s['subjectSelection'],roster,'subjectSelection'))
                projections.append({**{k:v for k,v in s.items() if k not in {'subjectSelection','beatSelections'}},'subjectRef':chosen['id'],'sourceTargetLabel':chosen['name'],
                    'beatIds':[choose(v,beat_ids,'beatSelections') for v in sequence(s['beatSelections'])],
                    'spokenIds':[object_value(v)['id'] for v in spoken if object_value(v)['speaker']==chosen['id']]})
            facts['projectionSubjects']=projections
        elif domain=='SUBJECTS':
            facts['presentSubjects']=[{**{k:v for k,v in object_value(raw).items() if k!='subjectSelection'},'id':object_value(choose(object_value(raw)['subjectSelection'],roster,'subjectSelection'))['id']} for raw in sequence(facts['presentSubjects'])]
        elif domain=='ACTION':
            facts['actionPhases']=[{**{k:v for k,v in object_value(raw).items() if k not in {'beatSelection','spokenSelections'}},
                'beatId':choose(object_value(raw)['beatSelection'],beat_ids,'beatSelection'),
                'spokenIds':[object_value(choose(v,spoken,'spokenSelections'))['id'] for v in sequence(object_value(raw)['spokenSelections'])]} for raw in sequence(facts['actionPhases'])]
        elif domain=='REFERENCE':
            facts['references']=[{**{k:v for k,v in object_value(raw).items() if k!='beatSelections'},'id':identity('reference',[request.scope.work_id,request.scope.scene_id,request.scope.shot_id],i),
                'beatIds':[choose(v,beat_ids,'beatSelections') for v in sequence(object_value(raw)['beatSelections'])]} for i,raw in enumerate(sequence(facts['references']))]
        elif domain=='SOUND' and 'speechRelations' in facts:
            facts['speechRelations']=[{**{k:v for k,v in object_value(raw).items() if k not in {'spokenSelection','targetSpokenSelection'}},
                'eventId':object_value(choose(object_value(raw)['spokenSelection'],spoken,'spokenSelection'))['id'],
                'targetEventId':object_value(choose(object_value(raw)['targetSpokenSelection'],spoken,'targetSpokenSelection'))['id']} for raw in sequence(facts['speechRelations'])]
        output.append({'domain':domain,'facts':facts})
    return output


def author_payload(request: AuthorRequest | FilmAuthorRequest) -> dict[str, JsonValue]:
    source=request.source.model_dump(mode='json',by_alias=True)
    source={k:v for k,v in source.items() if k not in {'originalOwnerRef','languageMetadataRef'}}
    result: dict[str,JsonValue]={'source':JSON.validate_python(source)}
    def scene_view(scene:SceneBody)->dict[str,JsonValue]:
        roster=subjects(scene)
        return {'sceneText':scene.scene_text,'subjectCandidates':[{'selection':i,'name':s['name'],'meaning':s['meaning']} for i,s in enumerate(roster)],
            'spokenCandidates':[{'selection':i,'speakerSelection':next(j for j,s in enumerate(roster) if s['id']==line.speaker),'text':line.text,'mustKeep':line.must_keep} for i,line in enumerate(scene.dialogue)]}
    if isinstance(request,FilmAuthorRequest):
        result['productionGoal']=request.production_goal
        if request.canon:
            result['canon']={'work':JSON.validate_python(request.canon.work.model_dump(mode="json",by_alias=True)),'script':JSON.validate_python(request.canon.script.model_dump(mode="json",by_alias=True)),
                'sceneCandidates':[{'selection':i,**scene_view(s.scene)} for i,s in enumerate(request.canon.scenes)]}
    elif request.canon:
        result['canon']={'work':JSON.validate_python(request.canon.work.model_dump(mode="json",by_alias=True)),'script':JSON.validate_python(request.canon.script.model_dump(mode="json",by_alias=True)),'scene':scene_view(request.canon.scene)}
        if request.shot:
            result['shot']=JSON.validate_python(request.shot.model_dump(mode='json',by_alias=True,exclude={'spoken_ids'}))
            result['selectedSpokenCandidates']=[{'selection':i,'text':line.text,'speakerSelection':next(j for j,s in enumerate(subjects(request.canon.scene)) if s['id']==line.speaker)} for i,line in enumerate(line for line in request.canon.scene.dialogue if line.id in request.shot.spoken_ids)]
            result['beatSelectionRule']='Select ordinal rows from PERFORMANCE.beats in this same professional bundle; identities are assigned by the system after all owners validate. ACTION/REFERENCE consume those exact approved rows.'
    return result


def author_feedback(diagnostic: AuthorDiagnostic, request: AuthorRequest | FilmAuthorRequest) -> dict[str, JsonValue]:
    """Diagnostic refs remain local; corrective wire uses the same legal menus.

    Only exact authoritative maps are used. No ref inference or output repair.
    """
    menus: dict[str, list[str]] = {}
    if isinstance(request, FilmAuthorRequest):
        if request.canon:
            menus['scene'] = [scene.scene_id for scene in request.canon.scenes]
    elif request.canon:
        menus['subject'] = [str(s['id']) for s in subjects(request.canon.scene)]
        menus['spoken'] = [line.id for line in request.canon.scene.dialogue
            if diagnostic.role != 'professional' or request.shot is not None and line.id in request.shot.spoken_ids]
        menus['beat'] = [identity('beat',[request.scope.work_id,request.scope.scene_id,request.scope.shot_id],i)
            for i in range(100)]
    keys = {'missingSubjectId': ('subject','missingSubjectSelection'), 'beatId': ('beat','beatSelection'),
        'spokenId': ('spoken','spokenSelection'), 'allowedSpokenIds': ('spoken','allowedSpokenSelections')}
    fields = {'subjectRef':'subjectSelection','actor':'actorSelection','target':'targetSelection',
        'spokenContentId':'spokenSelection','spokenIds':'spokenSelections','beatId':'beatSelection',
        'beatIds':'beatSelections','eventId':'spokenSelection','targetEventId':'targetSpokenSelection'}
    def project(row: dict[str, JsonValue]) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for key, value in row.items():
            if key in keys:
                menu, output = keys[key]; candidates = menus.get(menu, [])
                if isinstance(value,str) and value in candidates:
                    result[output] = candidates.index(value)
                elif isinstance(value,list):
                    result[output] = [candidates.index(v) for v in value if isinstance(v,str) and v in candidates]
            elif key == 'fieldPath' and isinstance(value,list):
                result[key] = [fields.get(v,v) if isinstance(v,str) else v for v in value]
            elif value is not None:
                result[key] = value
        return result
    base: dict[str, JsonValue] = {'stage': diagnostic.failure_stage, 'code': diagnostic.code,
        'validator': diagnostic.validator, 'omittedIssueCount': diagnostic.omitted_issue_count,
        'reason': diagnostic.reason, 'missingSubjectId': diagnostic.missing_subject_id,
        'beatId': diagnostic.beat_id, 'spokenId': diagnostic.spoken_id,
        'expectedCoverageRole': diagnostic.expected_coverage_role}
    feedback = project(base)
    feedback['issues'] = [project(object_value(JSON.validate_python(issue.model_dump(mode='json',by_alias=True))))
        for issue in diagnostic.issues]
    # Explicit current menus already appear in author_payload; correction never
    # reintroduces internal identities or supplies another competing inventory.
    if isinstance(request,AuthorRequest) and request.shot:
        feedback['requiredProfessionalDomains'] = [d.value for d in request.shot.professional_domains]
    return feedback
