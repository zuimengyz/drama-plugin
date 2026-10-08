"""Select relevant adopted sources by identity/place, never by latest output.

Uses existing character/location contracts. Selection is not a face/voice proof.
"""
from __future__ import annotations

from drama_plugin.creative_engine.contracts import Kind
from drama_plugin.contracts.location_design import SceneLocationBinding
from drama_plugin.generation.sources import child
from drama_plugin.production.references import ReferenceExecutionBinding
from drama_plugin.production_design import resolve_location_design
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.film.media_units import production_progress, completion, current_candidate_review
from drama_plugin.contracts.base import sha256_canonical


def professional(p, unit, domain):
    return next(p.creative_versions.resolve(r) for r in unit.refs if
        p.creative_versions.resolve(r).kind == Kind.PROFESSIONAL and p.creative_versions.resolve(r).body.domain == domain)


def observed_identity_ages(facts):
    """Observed positive age clauses only; a forbidden age is not current age."""
    import re
    from drama_plugin.generation.unit_scope import labels, AGES
    if not facts.get('identityObservationSource'):
        return set()
    positive = [part for part in re.split(r'[。；;.]', str(facts.get('identityConstraints','')))
                if not re.match(r'\s*(?:不|勿|禁止|不得|不能|never\b|not\b|do not\b)', part, re.I)]
    return labels(' '.join(positive),AGES)


def location_context(p, unit):
    world = professional(p, unit, 'WORLD')
    raw = world.body.facts.get('locationBinding')
    if raw is None:
        return {'status':'DESIGN_ONLY','locationId':None,'base':None,'localOverride':None}
    binding = SceneLocationBinding.model_validate(raw)
    pin = binding.location_ref.artifact_ref
    body = p.creative_versions.objects.read_ref(pin)
    resolved = resolve_location_design(binding,scene_id=unit.scene_id,
        current={pin.key:pin.fingerprint},artifacts={pin.key:body})
    return {'status':'RESOLVED_DESIGN','locationId':binding.location_ref.location_id,**resolved}


def select_references(p, run_id, unit, selection, *, register=False):
    progress = production_progress(p,run_id)
    package = p.production_packages.get(unit.package_ref)
    scope = RuntimeScope(work_id=package.scope.work.artifact_ref,scene_id=unit.scene_id,shot_id=unit.shot_id)
    subjects, world = professional(p,unit,'SUBJECTS'), professional(p,unit,'WORLD')
    from drama_plugin.creative_engine.sources import NativeCreativeSources
    native = NativeCreativeSources(p.creative_versions,unit.refs,p.execution_references)
    subject_source = native.project(subjects)
    world_source = native.project(world)
    active_rows = {int(f.reference.path[2]) for f in selection.fact_refs
        if f.domain == 'SUBJECTS' and f.reference.path[1:2] == ('presentSubjects',)}
    subject_ids = {r['id'] for i,r in enumerate(subjects.body.facts['presentSubjects']) if i in active_rows}
    target_location = location_context(p,unit)
    from drama_plugin.generation.unit_scope import project_scoped_value
    setting_ref = world_source.reference('content','setting')
    target_location.update(designSourceRef=setting_ref.model_dump(mode='json',by_alias=True),
        currentSetting=project_scoped_value(selection.execution_context,setting_ref,world.body.facts['setting']),
        currentTime=project_scoped_value(selection.execution_context,world_source.reference('content','time'),world.body.facts.get('time')),
        currentWeather=project_scoped_value(selection.execution_context,world_source.reference('content','weather'),world.body.facts.get('weather')))
    chosen, bindings, candidates, narrative_sources, excluded_sources, seen = [], [], [], [], [], set()
    from drama_plugin.generation.unit_scope import labels, AGES
    def entry_ages(ref):
        source=native.project(native.exact_projection(ref))
        if source.reference(*ref.path)!=ref:raise ValueError('REFERENCE_AGE_SOURCE_MISMATCH')
        value=source.body
        for key in ref.path:value=value[int(key)] if isinstance(value,list) else value[key]
        return labels(str(value),AGES)
    target_ages=entry_ages(selection.start_ref)
    if not target_ages:
        target_ages=observed_identity_ages(subjects.body.facts)
    # Qualified current-Scene evidence precedes older same-person imagery;
    # location matching below still selects the relevant historical place.
    for record in sorted(progress['mediaIndex'], key=lambda r:r['sceneId'] != unit.scene_id):
        if record.get('productionSelection') not in ('USER_SELECTED','HOST_WORKING_INPUT'): continue
        source_unit = next(u for u in p.film.store.checkpoint(run_id).units if u.shot_id == record['shotId'])
        op, check, media, source_task = completion(p,record['runId'])
        # An expired original URL remains provenance, but is not a usable
        # execution input. Do not keep selecting it ahead of a qualified later
        # candidate or send its already observed download failure again.
        from drama_plugin.execution.contracts import ProviderReceipt
        from urllib.parse import urlsplit,parse_qs
        from datetime import datetime,timezone,timedelta
        receipt=p.execution.store.get(media.receipt_ref,ProviderReceipt)
        params={k.lower():v[0] for k,v in parse_qs(urlsplit(receipt.result.locator).query).items()}
        stamp,ttl=params.get('x-tos-date'),params.get('x-tos-expires')
        if stamp and ttl and ttl.isdigit() and datetime.strptime(stamp,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)+timedelta(seconds=int(ttl))<=datetime.now(timezone.utc):
            narrative_sources.append({'sourceRunId':record['runId'],'contentHash':media.media.content_hash,
                'purpose':'RETAINED_SOURCE_PROVENANCE','providerInput':False,'reason':'OFFICIAL_DELIVERY_EXPIRED'})
            continue
        review = current_candidate_review(p,record['runId'],check)
        if review.outcome != 'PASS':
            # Accepting flawed picture for this edit does not qualify the whole
            # video (including its flawed background/group) as a model input.
            excluded_sources.append({'sourceRunId':record['runId'],'contentHash':media.media.content_hash,
                'reviewRef':review.artifact_reference().model_dump(mode='json',by_alias=True),
                'reason':'ACCEPTED_PICTURE_DOES_NOT_QUALIFY_KNOWN_REVISE_AS_EXECUTION_REFERENCE'})
            continue
        # The media proves only the subjects in its frozen production unit,
        # not every age/group declared in a whole-Shot SUBJECTS original.
        source_rows = {int(f.reference.path[2]) for f in source_task.unit.fact_refs
            if f.domain == 'SUBJECTS' and f.reference.path[1:2] == ('presentSubjects',)}
        source_subjects = {r['id'] for i,r in enumerate(professional(p,source_unit,'SUBJECTS').body.facts['presentSubjects'])
            if i in source_rows}
        duties, authorities = [], []
        common = sorted(subject_ids & source_subjects)
        fresh = [s for s in common if ('CHARACTER',s) not in seen]
        source_ages=entry_ages(source_task.unit.start_ref)
        if not source_ages:
            frozen_subjects=next(p.creative_versions.resolve(r) for r in source_task.owners.adopted_refs
                if p.creative_versions.resolve(r).kind == Kind.PROFESSIONAL
                and p.creative_versions.resolve(r).body.domain == 'SUBJECTS')
            source_ages=observed_identity_ages(frozen_subjects.body.facts)
        age_mismatch = bool(target_ages and source_ages and source_ages != target_ages
            or target_ages & {'child','youth'} and source_ages != target_ages)
        if fresh and age_mismatch:
            # A same-person narrative reference is not a qualified cross-age
            # portrait. Keep its provenance without sending that face as an
            # executable visual input. Other applicable spatial duties survive.
            narrative_sources.append({'sourceRunId':record['runId'],'contentHash':media.media.content_hash,
                'subjectIds':fresh,'sourceStateRef':source_task.unit.start_ref.model_dump(mode='json',by_alias=True),
                'targetStateRef':selection.start_ref.model_dump(mode='json',by_alias=True),
                'purpose':'NARRATIVE_CHARACTER_IDENTITY','providerInput':False,
                'reason':'CURRENT_AGE_FACE_MEDIA_UNVERIFIED','sourceAges':sorted(source_ages),'targetAges':sorted(target_ages)})
            fresh=[]
        if fresh and 'identityConstraints' in subjects.body.facts:
            use_ref = subject_source.reference('content','identityConstraints')
            duties = [dict(role='CHARACTER',necessity='PREFERRED',subject='+'.join(fresh),
                purpose='Narrative character identity only; current age, costume, pose, light and location come from the target design.')]
            authorities.append(use_ref)
        source_location = location_context(p,source_unit)
        same_place = (target_location['locationId'] is not None and source_location['locationId']==target_location['locationId']
                      and source_location['locationRef']==target_location['locationRef'])
        if same_place and ('LOCATION',target_location['locationId']) not in seen:
            location_use = world_source.reference('content','locationBinding')
            if not duties: use_ref = location_use
            authorities.append(location_use)
            duties.append(dict(role='LOCATION',necessity='PREFERRED',subject=target_location['locationId'],
                purpose='Space structure only; apply the target Scene location override, action and lighting state.'))
        if not duties: continue
        semantics = tuple('identity' if d['role']=='CHARACTER' else 'environment' for d in duties)
        from drama_plugin.execution.contracts import TechnicalMediaReview
        probe = p.execution.store.get(check.progress.current_video_technical_ref,TechnicalMediaReview).observation
        use_identity=sha256_canonical({'stateRef':selection.start_ref.model_dump(mode='json',by_alias=True),
            'useRef':use_ref.model_dump(mode='json',by_alias=True),
            'authorityRefs':[r.model_dump(mode='json',by_alias=True) for r in authorities],'duties':duties})
        binding = ReferenceExecutionBinding(binding_id='reuse-'+media.media.content_hash[:20]+'-'+use_identity[:20],
            version=1,scope=scope,source_scope=media.scope,use_ref=use_ref,state_ref=selection.start_ref,
            media=dict(media_id=media.canonical_media_ref.artifact_ref,version=str(media.canonical_media_ref.version or 1),
                content_hash=media.media.content_hash,kind='video',semantics=tuple(sorted(set(semantics))),
                duration=(record['actualDurationMs'] or 0)/1000,width=probe.width,height=probe.height,
                review_ref=check.progress.video_creative_ref.artifact_ref),
            duties=tuple(duties),subject_ids=tuple(fresh) if duties[0]['role']=='CHARACTER' else (),role='REFERENCE',
            authorization_scope='ADOPTED_PRODUCTION_INPUT',authority_refs=tuple(authorities),
            location_binding=world.body.facts['locationBinding'] if any(d['role']=='LOCATION' for d in duties) else None)
        candidates.append(binding)
        if register: bindings.append(p.execution_references.register(binding))
        chosen.append({'sourceRunId':record['runId'],'sourceScope':media.scope.model_dump(mode='json',by_alias=True),
            'targetScope':scope.model_dump(mode='json',by_alias=True),'mediaId':binding.media.media_id,
            'contentHash':binding.media.content_hash,'purposes':[d['role'] for d in duties],
            'useRef':use_ref.model_dump(mode='json',by_alias=True), 'stateRef':selection.start_ref.model_dump(mode='json',by_alias=True),
            'inputRole':'REFERENCE','faceAgeSuitability':'UNVERIFIED','voiceIdentity':'UNVERIFIED',
            'excludedSourceState':['opening action','camera progress','pose','costume state','light/time state','spoken content']})
        for d in duties:
            for subject in d['subject'].split('+'): seen.add((d['role'],subject))
    character_packages = []
    for subject, raw in subjects.body.facts.get('characterPackageBindings',{}).items():
        if subject not in subject_ids: continue
        from drama_plugin.characters.repository import CharacterRepository
        from drama_plugin.contracts.character_package import CharacterPackageRef
        resolved = CharacterRepository(p.config.character_repository_root).resolve_character_package(
            CharacterPackageRef.model_validate(raw),consumer='shot-production',purpose='PRODUCTION')
        character_packages.append({k:resolved[k] for k in ('characterId','characterPackageRef','characterPackageVersion','checksum','status')})
    scene = next(p.creative_versions.resolve(r) for r in unit.refs if p.creative_versions.resolve(r).kind == Kind.SCENE)
    speakers = {line.speaker for line in scene.body.dialogue if line.id in selection.spoken_ids}
    return {'bindings':tuple(bindings),'candidates':tuple(candidates),'selected':chosen,'narrativeIdentitySources':narrative_sources,'excludedSources':excluded_sources,'location':target_location,'characterPackages':character_packages,
        'voice':{'speakerIds':sorted(speakers),'visibleSubjectIds':sorted(subject_ids),
            'visibleStateRef':selection.start_ref.model_dump(mode='json',by_alias=True),
            'delivery':'VOICE_OVER' if selection.execution_context and selection.execution_context.voice_over_ref else 'AUTHORED_SPEECH',
            'authorityRef':selection.execution_context.voice_over_ref.model_dump(mode='json',by_alias=True) if selection.execution_context and selection.execution_context.voice_over_ref else None,
            'voiceMedia':None,'voiceIdentityVerification':'UNVERIFIED'},
        'missingEvidence':['CURRENT_AGE_FACE_MEDIA_UNVERIFIED','VOICE_IDENTITY_UNVERIFIED']}
