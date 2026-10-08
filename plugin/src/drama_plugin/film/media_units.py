"""Native Film read views and unit admission, using existing plans and receipts.

No scheduling loop, creative writes, Provider IO, financial terms or reservations.
"""
from __future__ import annotations

import json
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.contracts import Kind
from drama_plugin.execution.contracts import ExecutionOperation, MediaBinding, CreativeMediaReview, TechnicalMediaReview
from drama_plugin.film.contracts import FilmCanon, FilmDirection
from drama_plugin.generation.contracts import GenerationPreparation
from drama_plugin.generation.unit_scope import phase_boundary
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


def unit_for_task(p, cp, task):
    shot = next(p.creative_versions.resolve(r) for r in task.owners.adopted_refs
                if p.creative_versions.resolve(r).kind == Kind.SHOT)
    matches = [u for u in cp.units if (u.scene_id, u.shot_id) == (shot.scope.scene_id, shot.scope.shot_id)]
    if len(matches) != 1:
        raise ValueError('NATIVE_FILM_UNIT_SCOPE_MISMATCH')
    unit = matches[0]
    required = {r for r in unit.refs if p.creative_versions.resolve(r).kind != Kind.PROFESSIONAL}
    actual = {r for r in task.owners.adopted_refs if p.creative_versions.resolve(r).kind != Kind.PROFESSIONAL}
    if actual != required:
        raise ValueError('NATIVE_FILM_UNIT_VERSION_MISMATCH')
    return unit


def phases_for(p, unit):
    original = next(p.creative_versions.resolve(r) for r in unit.refs if
        p.creative_versions.resolve(r).kind == Kind.PROFESSIONAL and
        p.creative_versions.resolve(r).body.domain == 'ACTION')
    return original, original.body.facts['actionPhases']


def child_ids(p, run_id):
    cp = p.film.store.checkpoint(run_id)
    opening = p.source_film_media_opening(run_id)
    return tuple(dict.fromkeys((*( (opening,) if opening else ()), *(cp.scene_media_run_ids or ()))))


def completion(p, child_id):
    with p.ledger.transaction() as db:
        row = db.execute('SELECT operation_ref_json FROM production_operation WHERE run_id=? AND operation_ref_json IS NOT NULL', (child_id,)).fetchone()
    if row is None:
        return None
    ref = ArtifactReference.model_validate_json(row[0])
    cp = p.execution.store.checkpoint(ref)
    if cp.progress.video_ref is None:
        return None
    op = p.execution.store.get(ref, ExecutionOperation)
    media = p.execution.store.get(cp.progress.video_ref, MediaBinding)
    task = p.generation_artifacts.get(op.preparation_ref, GenerationPreparation).task
    return op, cp, media, task


def validate_child_package(p, child_id, unit):
    """Completed media keeps its frozen Package after professional derivation."""
    from drama_plugin.generation.audio import package_scope
    from drama_plugin.runtime.contracts import RuntimeState
    child=p.runtime.store.load(child_id)
    ref=p.gate_findings.inputs(child_id).package_ref
    if child.scope != RuntimeScope(work_id=package_scope(p.production_packages.get(unit.package_ref)).work_id,
                                   scene_id=unit.scene_id,shot_id=unit.shot_id):
        raise ValueError('SCENE_CONTINUATION_SCOPE_MISMATCH')
    if ref == unit.package_ref:
        return ref
    done=completion(p,child_id)
    if child.state != RuntimeState.SUCCEEDED or done is None:
        raise ValueError('SCENE_CONTINUATION_SCOPE_MISMATCH')
    op,_,media,task=done
    prepared=p.generation_artifacts.get(op.preparation_ref,GenerationPreparation)
    frozen=p.generation_artifacts.inputs(child_id).task
    if (op.source_package_ref != ref or prepared.source_package_ref != ref
            or media.source_package_ref != ref or media.scope != child.scope
            or package_scope(p.production_packages.get(ref)) != child.scope
            or task != frozen or prepared.task != frozen):
        raise ValueError('SCENE_CONTINUATION_SCOPE_MISMATCH')
    # Canon/Scene/Shot adoption cannot change under completed media. Only its
    # professional derived version may differ from the current production unit.
    required={r for r in unit.refs if p.creative_versions.resolve(r).kind != Kind.PROFESSIONAL}
    actual={r for r in frozen.owners.adopted_refs if p.creative_versions.resolve(r).kind != Kind.PROFESSIONAL}
    if actual != required:
        raise ValueError('NATIVE_FILM_UNIT_VERSION_MISMATCH')
    return ref


def current_candidate_review(p, child_id, check):
    original = p.execution.store.get(check.progress.video_creative_ref, CreativeMediaReview)
    try:
        ref = ArtifactReference.model_validate(p.ledger.get_index('source-film-candidate-reassessment', child_id))
    except KeyError:
        return original
    current = p.execution.store.get(ref, CreativeMediaReview)
    if (current.supersedes_ref != check.progress.video_creative_ref or current.outcome != 'REVISE'
            or any(getattr(current,k) != getattr(original,k) for k in
                ('run_id','scope','operation_ref','attempt_ref','media','source_package_ref'))):
        raise ValueError('NATIVE_CANDIDATE_REASSESSMENT_SCOPE_MISMATCH')
    return current


def record_candidate_reassessment(p, run_id, child_id, review):
    """Append a concrete Host REVISE without erasing completion or adoption."""
    if child_id not in child_ids(p, run_id) or p.runtime.store.load(child_id).state != 'SUCCEEDED':
        raise ValueError('COMPLETED_NATIVE_FILM_CANDIDATE_REQUIRED')
    done = completion(p, child_id)
    if not done: raise ValueError('RETAINED_MEDIA_REQUIRED')
    _, check, media, _ = done
    if any(r.run_id == child_id and r.source_ref in (check.progress.video_ref, media.canonical_media_ref)
            for r in adoption_receipts(p)):
        raise ValueError('USER_ADOPTED_MEDIA_REASSESSMENT_REQUIRES_USER_DECISION')
    original = p.execution.store.get(check.progress.video_creative_ref, CreativeMediaReview)
    if (review.outcome != 'REVISE' or review.reviewer == 'USER'
            or review.supersedes_ref != check.progress.video_creative_ref
            or any(getattr(review,k) != getattr(original,k) for k in
                ('run_id','scope','operation_ref','attempt_ref','media','source_package_ref'))):
        raise ValueError('NATIVE_CANDIDATE_REASSESSMENT_SCOPE_MISMATCH')
    ref = p.execution.store.put(review)
    p.ledger.put_index('source-film-candidate-reassessment',child_id,ref,scope=media.scope,once=True)
    return ref


def select_working_input(p, run_id, child_id):
    """A reviewed Host candidate is a production input, never user adoption."""
    if child_id not in child_ids(p,run_id) or p.runtime.store.load(child_id).state != 'SUCCEEDED':
        raise ValueError('COMPLETED_NATIVE_FILM_CANDIDATE_REQUIRED')
    done=completion(p,child_id)
    if not done: raise ValueError('RETAINED_MEDIA_REQUIRED')
    _,check,media,_=done
    review=current_candidate_review(p,child_id,check)
    if (review.outcome!='PASS' or review.media!=media.media or review.scope!=media.scope
            or not media.canonical_media_ref):
        raise ValueError('REVIEWED_PERSISTED_NATIVE_INPUT_REQUIRED')
    p.ledger.put_index('source-film-working-input',child_id,check.progress.video_ref,scope=media.scope,once=True)
    return check.progress.video_ref


def boundary_for(p, run_id, unit, phase_index, previous_task=None):
    cp = p.film.store.checkpoint(run_id)
    direction = p.film.store.author(cp.direction_ref, FilmDirection)
    directed = next(d for d in direction.shots if d.shot_id == unit.shot_id and d.scene_id == unit.scene_id)
    action, phases = phases_for(p, unit)
    if not 0 <= phase_index < len(phases):
        raise ValueError('NATIVE_OPERATION_PHASE_OUT_OF_RANGE')
    if previous_task:
        previous_unit = unit_for_task(p, cp, previous_task)
        if previous_unit.shot_id != unit.shot_id:
            if phase_index != 0:
                raise ValueError('NEW_ACTION_MUST_START_WITH_NEW_CONTENT')
            return {'cut':'CUT','match':'MATCH','continuous':'CONTINUE'}[directed.transition]
        if (previous_task.unit.spoken_range and previous_task.unit.spoken_range[1] < previous_task.unit.spoken_range[2]
                and int(previous_task.unit.action_refs[0].path[-2]) == phase_index):
            return 'CONTINUE'
    return phase_boundary(phases, phase_index, directed.shot.model_dump(mode='json', by_alias=True))


def adoption_receipts(p):
    with p.ledger.transaction() as db:
        rows = db.execute("SELECT body_json FROM immutable_artifact WHERE artifact_type='user-decision'").fetchall()
    receipts = [UserDecisionRecord.model_validate_json(r[0]) for r in rows]
    return [r for r in receipts if r.accepted and r.category == 'ADOPTION']


def archive_status(p, work_id, media_refs):
    """Read retained archive receipts; never repeat an observer or remote upload."""
    found = []
    roots = (p.creative_versions.root, p.ledger.path.parent/'subtitle-authority')
    paths = [path for root in roots for path in (root/'objects').glob('*.json')]
    for path in paths:
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict) or raw.get('taskState') != 'ARCHIVED_AND_CLOSED':
            continue
        if raw.get('scope',{}).get('workId') != work_id or 'formalAdoptionRecords' not in raw:
            continue
        sources = [r.get('sourceRef') for r in raw['formalAdoptionRecords']]
        if not any(ref.model_dump(mode='json',by_alias=True) in sources for ref in media_refs):
            continue
        if path.stem != sha256_canonical(sha256_canonical(raw)):
            raise ValueError('ARCHIVE_RECEIPT_HASH_MISMATCH')
        for row in raw['formalAdoptionRecords']:
            decision = p.reviews.user_decision(ArtifactReference.model_validate(row['decisionRef']))
            if not decision.accepted or decision.category != 'ADOPTION' or decision.source_ref.model_dump(mode='json',by_alias=True) != row['sourceRef']:
                raise ValueError('ARCHIVE_ADOPTION_RECEIPT_MISMATCH')
        found.append({k:raw.get(k) for k in ('scope','canonicalReviewMediaRef','userAdoption','russianVerification',
            'translationVerification','remotePersistence','acceptedUncertainties','taskState','archiveRef',
            'subtitleDelivery','reviewMediaHash','subtitleFileHashes','acceptedFindings','revisionDisposition')})
    return found


def production_progress(p, run_id):
    cp, parent = p.film.store.checkpoint(run_id), p.runtime.store.load(run_id)
    canon = p.film.store.author(cp.canon_ref, FilmCanon)
    direction = p.film.store.author(cp.direction_ref, FilmDirection)
    if [(u.scene_id,u.shot_id) for u in cp.units] != [(d.scene_id,d.shot_id) for d in direction.shots]:
        raise ValueError('FILM_PLAN_UNIT_ORDER_MISMATCH')
    receipts = adoption_receipts(p)
    records, refs = [], []
    for child_id in child_ids(p, run_id):
        child = p.runtime.store.load(child_id)
        task = p.generation_artifacts.inputs(child_id).task
        unit = unit_for_task(p, cp, task)
        done = completion(p, child_id)
        selected = task.unit
        _, authored_phases = phases_for(p,unit)
        phase_index = int(selected.action_refs[0].path[-2])
        scene_name = next(s.scene.scene_text for s in canon.scenes if s.scene_id == unit.scene_id)
        item = {'runId':child_id,'sceneId':unit.scene_id,'shotId':unit.shot_id,
            'sceneName':scene_name,'content':authored_phases[phase_index]['action'],
            'entryState':authored_phases[phase_index]['entryState'],
            'phaseIndex':phase_index,'beatIds':list(selected.beat_ids),
            'spokenIds':list(selected.spoken_ids),'generationState':child.state.value,'adoption':'PENDING',
            'plannedOperationDurationMs':task.profile.requested_duration_ms,'actualDurationMs':None,
            'soundVerification':'UNVERIFIED' if selected.spoken_ids else 'NOT_APPLICABLE',
            'inputMode':task.input_mode,'boundary':task.boundary.kind if task.boundary else 'CONTINUE' if task.continuation else 'START',
            'referenceRefs':[r.model_dump(mode='json',by_alias=True) for r in (task.execution_reference_refs or ())]}
        if done:
            op, check, media, _ = done
            ref = check.progress.video_ref; refs.append(ref)
            adopted = any(r.run_id == child_id and r.scope == child.scope and r.source_ref in
                (ref, media.canonical_media_ref) for r in receipts)
            item.update(mediaRef=ref.model_dump(mode='json',by_alias=True),mediaHash=media.media.content_hash,
                canonicalMediaRef=media.canonical_media_ref.model_dump(mode='json',by_alias=True) if media.canonical_media_ref else None,
                adoption='USER_SELECTED' if adopted else 'PENDING',persistence='VERIFIED' if media.canonical_media_ref else 'LOCAL_ONLY')
            try: working=p.ledger.get_index('source-film-working-input',child_id)
            except KeyError: working=None
            item['productionSelection']='USER_SELECTED' if adopted else 'HOST_WORKING_INPUT' if working==ref.model_dump(mode='json',by_alias=True) else 'CANDIDATE_ONLY'
            if check.progress.current_video_technical_ref:
                technical = p.execution.store.get(check.progress.current_video_technical_ref,TechnicalMediaReview)
                item['actualDurationMs'] = technical.observation.duration_ms
            if check.progress.video_creative_ref:
                review = current_candidate_review(p,child_id,check)
                item.update(creativeReviewRef=review.artifact_reference().model_dump(mode='json',by_alias=True),
                    creativeReviewOutcome=review.outcome)
                if item['productionSelection']=='HOST_WORKING_INPUT' and review.outcome!='PASS':
                    item['productionSelection']='REVISION_REQUIRED'
                verified = {s for o in review.observations for s in (o.verified_spoken_ids or ())}
                if selected.spoken_ids and verified == set(selected.spoken_ids): item['soundVerification'] = 'VERIFIED'
        records.append(item)
    scenes, next_unit = [], None
    for scene in canon.scenes:
        shots, assigned_spoken = [], set()
        for unit in [u for u in cp.units if u.scene_id == scene.scene_id]:
            _, phases = phases_for(p,unit)
            assigned_spoken.update(s for phase in phases for s in phase['spokenIds'])
            media = [r for r in records if r['shotId'] == unit.shot_id]
            covered_lines = {s for r in media if r['adoption']=='USER_SELECTED' for s in r['spokenIds']}
            accepted = {i for i,phase in enumerate(phases) if any(r['phaseIndex']==i and r['adoption']=='USER_SELECTED' and r['generationState']=='SUCCEEDED' for r in media) and set(phase['spokenIds'])<=covered_lines}
            production_lines={s for r in media if r.get('productionSelection') in ('USER_SELECTED','HOST_WORKING_INPUT') for s in r['spokenIds']}
            produced={i for i,phase in enumerate(phases) if any(r['phaseIndex']==i and r.get('productionSelection') in ('USER_SELECTED','HOST_WORKING_INPUT') and r['generationState']=='SUCCEEDED' for r in media) and set(phase['spokenIds'])<=production_lines}
            remaining = [{'phaseIndex':i,'beatId':phase['beatId'],'spokenIds':phase['spokenIds'],
                'content':phase['action'],'entryState':phase['entryState']} for i,phase in enumerate(phases)
                if i not in accepted or not set(phase['spokenIds']) <= covered_lines]
            production_remaining=[{'phaseIndex':i,'beatId':phase['beatId'],'spokenIds':phase['spokenIds'],
                'remainingSpokenIds':[s for s in phase['spokenIds'] if s not in production_lines],
                'content':phase['action'],'entryState':phase['entryState']} for i,phase in enumerate(phases) if i not in produced]
            shot = next(p.creative_versions.resolve(r).body for r in unit.refs if p.creative_versions.resolve(r).kind==Kind.SHOT)
            shots.append({'shotId':unit.shot_id,'packageRef':unit.package_ref.model_dump(mode='json',by_alias=True),
                'plannedDurationMs':shot.duration_ms,'actualAdoptedDurationMs':sum(r['actualDurationMs'] or 0 for r in media if r['adoption']=='USER_SELECTED'),
                'writtenContentCovered':not remaining,'adoptedPhases':sorted(accepted),'remaining':remaining,'segments':media,
                'productionContentCovered':not production_remaining,'producedPhases':sorted(produced),'productionRemaining':production_remaining,
                'durationExplanation':'Planning duration and adopted picture duration are separate; remaining content is determined by phase/spoken coverage.'})
            if next_unit is None and production_remaining:
                row = production_remaining[0]
                previous = next((p.generation_artifacts.inputs(r['runId']).task for r in reversed(records) if r.get('productionSelection') in ('USER_SELECTED','HOST_WORKING_INPUT')),None)
                boundary = boundary_for(p,run_id,unit,row['phaseIndex'],previous)
                next_unit = {'sceneId':unit.scene_id,'sceneName':scene.scene.scene_text,'shotId':unit.shot_id,'packageRef':unit.package_ref.model_dump(mode='json',by_alias=True),
                    **row,'boundary':boundary,
                    'referencePolicy':{'start':'IMMEDIATE_OFFICIAL_TAIL' if boundary=='CONTINUE' else 'TARGET_ENTRY_WITHOUT_OLD_FIRST_FRAME',
                        'character':'Authored target identity use; current age face/voice proof remains independently checked.',
                        'space':'Target location design/state; related adopted place sources selected by location, not recency.',
                        'selectionEntry':'select_source_film_references; exact references pin at prepare, never rediscover on recovery.'}}
        unassigned = sorted({line.id for line in scene.scene.dialogue} - assigned_spoken)
        scenes.append({'sceneId':scene.scene_id,'name':scene.scene.scene_text,'writtenContentCovered':bool(shots) and not unassigned and all(s['writtenContentCovered'] for s in shots),
            'productionContentCovered':bool(shots) and not unassigned and all(s['productionContentCovered'] for s in shots),
            'coverageBasis':'USER_ADOPTED_ASSIGNED_PHASES_AND_LINES; actual sound verification is independent',
            'unassignedSpokenIds':unassigned,'shots':shots})
    announcements = [f"Scene {s['sceneId']}: adopted coverage reaches the written Scene end; sound verification remains independent." for s in scenes if s['writtenContentCovered']]
    announcements += [f"Scene {s['sceneId']}: reviewed production candidates cover written content; user adoption and sound verification remain pending." for s in scenes if s['productionContentCovered'] and not s['writtenContentCovered']]
    return {'runId':run_id,'workflowId':parent.workflow_id,'runtimeState':parent.state.value,
        'filmContentComplete':all(s['writtenContentCovered'] for s in scenes),'scenes':scenes,'mediaIndex':records,
        'currentUnit':records[-1] if records else None,'nextUnit':next_unit,'announcements':announcements,
        'archives':archive_status(p,parent.scope.work_id,refs),'subtitlePolicy':'AFTER_SCENE_COMPLETION'}
