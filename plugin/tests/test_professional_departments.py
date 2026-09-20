"""Authority, immutable dependency, continuity and design-only Host regressions."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.professional import (
    CreativeBible, CreativeRecord, DirectorPackage, SceneAssembly, ShotAssembly,
    EntityIdentity,
)
from drama_plugin.professional import (
    registry, dependency_order, bible_pin, validate_bible, validate_package,
    validate_continuity, continuity_at, resolve_entity,
    validate_environment_preservation, decompose_clip_intervals,
    compile_prompt_projection, approval_subject,
)
from drama_plugin.hosts.professional import ProfessionalDepartmentHost

NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)
SOURCE = SourcePin(key='canon:work', kind='CANON', fingerprint=sha256_canonical({'story': 'locked'}))
SCENE_SOURCE = SourcePin(key='canon:S02', kind='CANON', fingerprint=sha256_canonical({'id': 'S02', 'episodeId': 'episode'}))
SHOT_SOURCE = SourcePin(key='canon:shot', kind='CANON', fingerprint=sha256_canonical({'id': 'shot', 'sceneId': 'S02'}))


def baseline():
    artifacts = {SOURCE.key: {'story': 'locked'}}
    current = {SOURCE.key: SOURCE.fingerprint}
    for pin, value in ((SCENE_SOURCE, {'id': 'S02', 'episodeId': 'episode'}), (SHOT_SOURCE, {'id': 'shot', 'sceneId': 'S02'})):
        artifacts[pin.key], current[pin.key] = value, pin.fingerprint
    bibles = {}
    for department in dependency_order():
        bible = CreativeBible(id=department, type=registry()[department].output_contract, work_ref='work',
            scene_refs=('S02', 'S04', 'S05', 'S06', 'S07', 'S08', 'S09'), shot_refs=('shot',),
            source_refs=(SOURCE,), depends_on=tuple(bible_pin(bibles[d]) for d in registry()[department].depends_on),
            created_by_capability=department, status='NOT_REQUIRED', not_required_reason='Fixture explicitly unused.',
            created_at=NOW, updated_at=NOW)
        bibles[department] = bible
        ref = bible_pin(bible)
        artifacts[ref.key] = dump_contract(bible)
        current[ref.key] = ref.fingerprint
    return bibles, artifacts, current


def record(values, *, identity='r', scope='S02', status='DECIDED', limitations=()):
    return CreativeRecord(id=identity, scope_refs=(scope,), values=values,
        provenance='MIGRATED_FROM_R1', source_refs=(SOURCE,), status=status, limitations=limitations)


def with_records(bible, *records):
    return CreativeBible.model_validate({**dump_contract(bible), 'status': 'READY_FOR_REVIEW',
        'notRequiredReason': None, 'content': [dump_contract(r) for r in records]})


def retain(bible, artifacts, current):
    ref = bible_pin(bible)
    artifacts[ref.key] = dump_contract(bible)
    current[ref.key] = ref.fingerprint
    return ref


def rebind(bibles, artifacts, current):
    for department in dependency_order():
        bibles[department] = bibles[department].model_copy(update={'depends_on': tuple(bible_pin(bibles[d]) for d in registry()[department].depends_on)})
        retain(bibles[department], artifacts, current)


def package_fixture(bibles, artifacts, current):
    refs = {k: bible_pin(v) for k, v in bibles.items()}
    scene = SceneAssembly(scene_id='S02', work_ref='work', source_ref=SCENE_SOURCE,
        dramaturgy_ref=refs['scene-development'], characters=('xiang',), environment_ref=refs['environment-design'],
        dialogue_refs=(refs['dialogue-design'],), department_refs={})
    shot = ShotAssembly(shot_id='shot', scene_ref='S02', work_ref='work', source_ref=SHOT_SOURCE,
        dramatic_purpose='locked', subjects=('xiang',), start_state='entry', end_state='exit', department_refs={})
    pins = []
    for key, obj in (('assembly:scene', scene), ('assembly:shot', shot)):
        pin = SourcePin(key=key, kind='DESIGN', fingerprint=sha256_canonical(obj))
        artifacts[pin.key], current[pin.key] = dump_contract(obj), pin.fingerprint
        pins.append(pin)
    return DirectorPackage(id='fixture', work_ref='work', source_refs=(SOURCE,), bible_refs=refs,
        scene_assembly_refs=(pins[0],), shot_assembly_refs=(pins[1],), created_at=NOW, updated_at=NOW)


def test_registry_is_complete_owned_and_acyclic():
    definitions = registry()
    assert len(definitions) == 46
    order = dependency_order()
    for department, definition in definitions.items():
        assert all(order.index(parent) < order.index(department) for parent in definition.depends_on)
        assert definition.can_create == definition.can_modify
        assert definition.output_contract
    assert definitions['character-art'].capability_type == definitions['environment-art'].capability_type == 'SKILL'
    assert 'character-art' not in definitions['director'].can_create
    assert set(definitions['continuity-supervisor'].depends_on) >= {'scene-development', 'character-dramaturgy', 'editorial-design'}


@pytest.mark.parametrize(('department', 'foreign_field'), [
    ('director', 'face_structure'), ('character-art', 'personality'),
    ('environment-art', 'topology'), ('lighting-design', 'material_palette'),
    ('video-model-selection', 'dialogue_text'), ('production-design', 'armor_intent'),
])
def test_department_cannot_write_another_profession(department, foreign_field):
    bibles, artifacts, current = baseline()
    bible = with_records(bibles[department], record({foreign_field: 'unauthorized rewrite'}))
    with pytest.raises(ValueError, match='AUTHORITY'):
        validate_bible(bible, artifacts, current)


@pytest.mark.parametrize(('department', 'field', 'nested'), [
    ('environment-design', 'topology', 'finalCamera'),
    ('environment-design', 'topology', 'music_cue'),
    ('environment-design', 'topology', 'voice_acting'),
    ('environment-design', 'topology', 'costume_design'),
    ('character-art', 'face_structure', 'personality'),
    ('environment-art', 'structural_language', 'topology'),
    ('lighting-design', 'source', 'material_palette'),
    ('director', 'film_grammar', 'face_structure'),
])
def test_cross_department_payload_cannot_hide_inside_owned_field(department, field, nested):
    bibles, artifacts, current = baseline()
    bible = with_records(bibles[department], record({field: {nested: 'hidden foreign design'}}))
    with pytest.raises(ValueError, match='AUTHORITY|CANNOT_OWN'):
        validate_bible(bible, artifacts, current)


def test_provider_controls_cannot_hide_in_creative_bible():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['character-art'], record({'face_structure': {'cfg_scale': 7}}))
    with pytest.raises(ValueError, match='PROVIDER_CONTROLS'):
        validate_bible(bible, artifacts, current)


def test_missing_dependency_cannot_be_filled_by_director():
    bibles, artifacts, current = baseline()
    broken = bibles['environment-art'].model_copy(update={'depends_on': ()})
    with pytest.raises(ValueError, match='DEPENDENCY_SET'):
        validate_bible(broken, artifacts, current)


def test_environment_art_requires_decided_topology():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['environment-art'], record({'environment_ref': 'ENV-04', 'visual_thesis': 'field tent'}))
    with pytest.raises(ValueError, match='DECIDED_TOPOLOGY'):
        validate_bible(bible, artifacts, current)


def test_action_requires_decided_blocking():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['action-choreography'], record({'scene_ref': 'S02', 'ordered_actions': ['grip', 'pull', 'mount']}))
    with pytest.raises(ValueError, match='DECIDED_BLOCKING'):
        validate_bible(bible, artifacts, current)


def test_stale_dependency_and_forged_payload_fail():
    bibles, artifacts, current = baseline()
    ref = bibles['environment-art'].depends_on[0]
    current[ref.key] = '0' * 64
    with pytest.raises(ValueError, match='STALE'):
        validate_bible(bibles['environment-art'], artifacts, current)
    current[ref.key] = ref.fingerprint
    artifacts[ref.key]['workRef'] = 'other'
    with pytest.raises(ValueError, match='CORRUPT'):
        validate_bible(bibles['environment-art'], artifacts, current)


def test_review_inventory_can_expose_uncertainty_but_cannot_claim_approval():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['diegetic-vocal'], record({'historical_uncertainty': 'melody not established'},
        status='UNRESOLVED', limitations=('Historical tune cannot be asserted.',)))
    assert validate_bible(bible, artifacts, current)['status'] == 'READY_FOR_REVIEW'
    with pytest.raises(ValidationError, match='APPROVAL'):
        CreativeBible.model_validate({**dump_contract(bible), 'status': 'APPROVED', 'approvedBy': ['director']})
    with pytest.raises(ValidationError, match='APPROVAL'):
        validate_bible(bible.model_copy(update={'status': 'APPROVED'}), artifacts, current)


def test_approval_receipt_must_bind_exact_content():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['historical-research'], record({'facts': ['source-pinned fact']}))
    receipt = {'kind': 'PROFESSIONAL_CREATIVE_APPROVAL', 'subjectId': bible.id, 'workRef': 'work',
        'decision': 'APPROVE', 'subjectFingerprint': approval_subject(bible), 'approvedBy': ['user:review']}
    ref = SourcePin(key='approval:1', kind='DESIGN', fingerprint=sha256_canonical(receipt))
    artifacts[ref.key] = receipt
    current[ref.key] = ref.fingerprint
    approved = CreativeBible.model_validate({**dump_contract(bible), 'status': 'APPROVED',
        'approvedBy': ['user:review'], 'approvalRefs': [dump_contract(ref)]})
    assert validate_bible(approved, artifacts, current)['artisticApproval'] == 'APPROVED'
    changed = approved.model_copy(update={'content': (record({'facts': ['altered after approval']}),)})
    with pytest.raises(ValueError, match='APPROVAL_RECEIPT'):
        validate_bible(changed, artifacts, current)


def state_record(id, domain, property, state, scene, owner, predecessor=None):
    return record(dict(entity='XiangYu', domain=domain, property=property, state=state,
        effective_from=scene, changed_by=dump_contract(bible_pin(owner)), scene_ref=scene,
        predecessor=predecessor, restored=False, owner_record_id=id,
        owner_state_path=['continuity', 'state']), identity=id, scope=scene)


def bind_state_records(ledger, artifacts, current):
    grouped = {}
    for row in ledger.content:
        grouped.setdefault(row.values['changed_by']['key'], []).append(row)
    refs = {}
    for key, rows in grouped.items():
        owner = CreativeBible.model_validate(artifacts[key])
        owner = with_records(owner, *(record({'continuity': {'state': r.values['state']}},
            identity=r.id, scope=r.values['scene_ref']) for r in rows))
        refs[key] = retain(owner, artifacts, current)
    return ledger.model_copy(update={'content': tuple(r.model_copy(update={'values': {
        **r.values, 'changed_by': dump_contract(refs[r.values['changed_by']['key']])}}) for r in ledger.content)})


def test_damage_and_wound_inherit_across_scenes():
    bibles, artifacts, current = baseline()
    ledger = with_records(bibles['continuity-supervisor'],
        state_record('strap-broken', 'costume', 'right_shoulder_strap', 'broken', 'S02', bibles['costume-design']),
        state_record('strap-secured', 'costume', 'right_shoulder_strap', 'temporarily_secured', 'S04', bibles['costume-design'], 'strap-broken'),
        state_record('waist-wound', 'injury', 'left_waist', 'wounded', 'S07', bibles['look-continuity']))
    ledger = bind_state_records(ledger, artifacts, current)
    scenes = list(ledger.scene_refs)
    assert validate_continuity(ledger, scenes, artifacts, current)['status'] == 'PASS'
    for scene in ('S04', 'S05', 'S06'):
        assert continuity_at(ledger, 'XiangYu', 'costume', 'right_shoulder_strap', scene, scenes).state == 'temporarily_secured'
    for scene in ('S08', 'S09'):
        assert continuity_at(ledger, 'XiangYu', 'injury', 'left_waist', scene, scenes).state == 'wounded'
    reset = state_record('silent-reset', 'costume', 'right_shoulder_strap', 'intact', 'S05', bibles['costume-design'], 'strap-secured')
    changed = ledger.model_copy(update={'content': (*ledger.content[:2], reset, ledger.content[2])})
    changed = bind_state_records(changed, artifacts, current)
    with pytest.raises(ValueError, match='UNEXPLAINED_CONTINUITY_RESTORATION'):
        validate_continuity(changed, scenes, artifacts, current)


def test_continuity_cannot_create_its_own_state_or_skip_predecessor():
    bibles, artifacts, current = baseline()
    wrong = with_records(bibles['continuity-supervisor'], state_record('wrong', 'costume', 'strap', 'broken', 'S02', bibles['director']))
    with pytest.raises(ValueError, match='WRONG_OWNER'):
        validate_continuity(wrong, wrong.scene_refs, artifacts, current)
    orphan = with_records(bibles['continuity-supervisor'], state_record('wrong', 'costume', 'strap', 'broken', 'S02', bibles['costume-design'], 'missing'))
    orphan = bind_state_records(orphan, artifacts, current)
    with pytest.raises(ValueError, match='PREDECESSOR'):
        validate_continuity(orphan, orphan.scene_refs, artifacts, current)


def test_shi_identity_never_name_matches_huanchu():
    shi = EntityIdentity(entity_id='shi', name='石', entity_type='person', historical_status='DRAMATIC_RECONSTRUCTION',
        identity_kind='ORIGINAL', evidence_refs=(SOURCE,), distinct_from=('huanchu',))
    huan = EntityIdentity(entity_id='huanchu', name='桓楚', entity_type='person', historical_status='DOCUMENTED',
        identity_kind='HISTORICAL_PERSON', historical_identity_ref='source:huanchu', evidence_refs=(SOURCE,))
    assert resolve_entity([shi, huan], 'shi') == shi
    with pytest.raises(ValueError, match='MISSING'):
        resolve_entity([shi, huan], '石')
    with pytest.raises(ValidationError, match='FICTIONAL_IDENTITY'):
        EntityIdentity.model_validate({**dump_contract(shi), 'historicalIdentityRef': 'huanchu'})


@pytest.mark.parametrize(('environment', 'field', 'original', 'changed'), [
    ('ENV-04', 'location_type', 'military_tent', 'palace'),
    ('ENV-08', 'physical_constraints', {'boat_capacity': 'small_ferry'}, {'boat_capacity': 'whole_army'}),
])
def test_protected_environment_cannot_change_scale_or_identity(environment, field, original, changed):
    bibles, _, _ = baseline()
    bible = with_records(bibles['environment-design'], record({'environment_ref': environment, field: original}))
    assert validate_environment_preservation(bible, {environment: {field: original}})['status'] == 'PASS'
    broken = with_records(bible, record({'environment_ref': environment, field: changed}))
    with pytest.raises(ValueError, match='LOCKED_ENVIRONMENT_CHANGED'):
        validate_environment_preservation(broken, {environment: {field: original}})


def test_environment_lock_resolves_base_local_and_state_records_without_overwrite():
    bibles, _, _ = baseline()
    base = record({'environment_ref': 'ENV-04', 'location_type': 'military_tent',
        'physical_constraints': {'maximum_occupants': 3}}, identity='base')
    local = record({'environment_ref': 'ENV-04', 'weather': 'night wind'}, identity='local', scope='S04')
    state = record({'environment_ref': 'ENV-04', 'spatial_continuity': {'state': {'exit': 'south'}}}, identity='state', scope='S04')
    duplicate_consistent = record({'environment_ref': 'ENV-04', 'location_type': 'military_tent'}, identity='same')
    locked = {'ENV-04': {'location_type': 'military_tent', 'physical_constraints': {'maximum_occupants': 3}}}
    bible = with_records(bibles['environment-design'], base, local, state, duplicate_consistent)
    assert validate_environment_preservation(bible, locked)['status'] == 'PASS'
    conflict = record({'environment_ref': 'ENV-04', 'location_type': 'palace'}, identity='conflicting-local', scope='S04')
    with pytest.raises(ValueError, match='LOCKED_ENVIRONMENT_CHANGED'):
        validate_environment_preservation(bible.model_copy(update={'content': (*bible.content, conflict)}), locked)


def test_reference_budget_is_three_and_clip_unknown_limit_is_not_executable():
    bibles, artifacts, current = baseline()
    bible = with_records(bibles['reference-strategy'], record({'reference_images': ['a', 'b', 'c', 'd']}))
    with pytest.raises(ValueError, match='LIMIT_THREE'):
        validate_bible(bible, artifacts, current)
    assert decompose_clip_intervals(58, verified_max_seconds=None, candidate_cut_points=[14, 30, 44])['status'] == 'BLOCKED_UNVERIFIED_PROVIDER_LIMIT'
    assert decompose_clip_intervals(58, verified_max_seconds=16, candidate_cut_points=[14, 30, 44], protected_intervals=[(10, 20)])['status'] == 'BLOCKED_INDIVISIBLE_ACTION_OR_DIALOGUE'
    result = decompose_clip_intervals(58, verified_max_seconds=16, candidate_cut_points=[14, 30, 44])
    assert result['status'] == 'PLANNED_NOT_EXECUTABLE'
    assert len(result['clips']) == 4
    assert result['providerCalls'] == 0


def test_host_roundtrip_department_dashboard_and_package(tmp_path: Path):
    bibles, artifacts, current = baseline()
    host = ProfessionalDepartmentHost(tmp_path)
    host.store.put(SCENE_SOURCE.key, artifacts[SCENE_SOURCE.key])
    host.store.put(SHOT_SOURCE.key, artifacts[SHOT_SOURCE.key])
    for department in dependency_order():
        result = host.submit(department, bibles[department], current=current)
        assert result['outputRef'] == dump_contract(bible_pin(bibles[department]))
    refs = {k: bible_pin(b) for k, b in bibles.items()}
    scene = SceneAssembly(scene_id='S02', work_ref='work', source_ref=SCENE_SOURCE,
        dramaturgy_ref=refs['scene-development'], characters=('XiangYu', 'Shi'),
        environment_ref=refs['environment-design'], dialogue_refs=(refs['dialogue-design'],),
        department_refs={'blocking': refs['blocking']})
    shot = ShotAssembly(shot_id='shot', scene_ref='S02', work_ref='work', source_ref=SHOT_SOURCE,
        dramatic_purpose='preserved', subjects=('XiangYu',), start_state='preserved entry', end_state='preserved exit',
        department_refs={'cinematography': refs['cinematography']})
    sref, href = host.retain_assembly(scene), host.retain_assembly(shot)
    for ref, obj in ((sref, scene), (href, shot)):
        current[ref.key] = ref.fingerprint
        artifacts[ref.key] = dump_contract(obj)
    package = DirectorPackage(id='pkg', work_ref='work', source_refs=(SOURCE,), bible_refs=refs,
        scene_assembly_refs=(sref,), shot_assembly_refs=(href,), created_at=NOW, updated_at=NOW)
    result = host.retain_package(package, current=current)
    assert result['productionAuthorized'] is False
    assert result['sceneCount'] == result['shotCount'] == 1
    assert len(host.dashboard(package, current=current)) == 46
    assert all(x['validationStatus'] == 'PASS' for x in host.dashboard(package, current=current))
    assert host.task('environment-art', task='design', available={}, current=current)['status'] == 'BLOCKED'
    with pytest.raises(ValueError, match='AUTHORITY'):
        host.submit('director', bibles['character-art'], current=current)
    with pytest.raises(ValueError, match='NOT_APPROVED'):
        compile_prompt_projection(package, shot, artifacts, current, adapter='generic')


def test_thin_models_cannot_embed_full_department_payload():
    with pytest.raises(ValidationError, match='extra_forbidden'):
        ShotAssembly(shot_id='shot', scene_ref='S02', work_ref='work', source_ref=SOURCE,
            dramatic_purpose='unchanged', subjects=('XiangYu',), start_state='a', end_state='b', department_refs={},
            character_art={'face': 'duplicated'})


def test_structured_state_binds_exact_owner_record_and_event_order():
    bibles, artifacts, current = baseline()
    costume = with_records(bibles['costume-design'],
        record({'continuity': {'state': {'integrity': 'INTACT', 'fullyRepaired': False}}}, identity='entry'),
        record({'continuity': {'state': {'integrity': 'BROKEN', 'fullyRepaired': False}}}, identity='rescue'))
    ref = retain(costume, artifacts, current)
    rows = []
    for i, item in enumerate(costume.content):
        rows.append(record(dict(entity='xiang', domain='costume', property='right_shoulder_strap',
            state=item.values['continuity']['state'], effective_from='S02', effective_from_event='ENTRY' if i == 0 else 'RESCUE_PULL',
            effective_from_phase='AFTER', changed_by=dump_contract(ref), scene_ref='S02',
            predecessor=None if i == 0 else 'state0', owner_record_id=item.id,
            owner_state_path=['continuity', 'state']), identity='state' + str(i)))
    ledger = with_records(bibles['continuity-supervisor'], *rows)
    assert validate_continuity(ledger, ledger.scene_refs, artifacts, current)['status'] == 'PASS'
    state = continuity_at(ledger, 'xiang', 'costume', 'right_shoulder_strap', 'S02', ledger.scene_refs)
    assert state.state['integrity'] == 'BROKEN'
    changed = rows[1].model_copy(update={'values': {**rows[1].values, 'state': {'integrity': 'INTACT'}}})
    with pytest.raises(ValueError, match='DIFFERS_FROM_OWNING'):
        validate_continuity(ledger.model_copy(update={'content': (rows[0], changed)}), ledger.scene_refs, artifacts, current)


def test_pure_compiler_projects_exact_approved_content_without_new_creative_text():
    bibles, artifacts, current = baseline()
    camera = with_records(bibles['cinematography'], record({'camera_height': 'approved shoulder height'}))
    sibling = record({'camera_height': 'different sibling angle'}, identity='sibling').model_copy(update={'scope_refs': ('S02', 'sibling-shot')})
    camera = camera.model_copy(update={'shot_refs': ('shot', 'sibling-shot'), 'content': (*camera.content, sibling)})
    receipt = {'kind': 'PROFESSIONAL_CREATIVE_APPROVAL', 'subjectId': camera.id, 'workRef': 'work',
        'decision': 'APPROVE', 'subjectFingerprint': approval_subject(camera), 'approvedBy': ['user:fixture']}
    approval = SourcePin(key='approval:camera', kind='DESIGN', fingerprint=sha256_canonical(receipt))
    artifacts[approval.key], current[approval.key] = receipt, approval.fingerprint
    camera = CreativeBible.model_validate({**dump_contract(camera), 'status': 'APPROVED',
        'approvedBy': ['user:fixture'], 'approvalRefs': [dump_contract(approval)]})
    bibles['cinematography'] = camera
    retain(camera, artifacts, current)
    # Rebind the immutable downstream fixtures after the camera changed.
    for department in dependency_order():
        bible = bibles[department]
        bible = bible.model_copy(update={'depends_on': tuple(bible_pin(bibles[d]) for d in registry()[department].depends_on)})
        bibles[department] = bible
        retain(bible, artifacts, current)
    refs = {k: bible_pin(b) for k, b in bibles.items()}
    scene = SceneAssembly(scene_id='S02', work_ref='work', source_ref=SCENE_SOURCE,
        dramaturgy_ref=refs['scene-development'], characters=('xiang',), environment_ref=refs['environment-design'],
        dialogue_refs=(refs['dialogue-design'],), department_refs={})
    shot = ShotAssembly(shot_id='shot', scene_ref='S02', work_ref='work', source_ref=SHOT_SOURCE,
        dramatic_purpose='immutable purpose', subjects=('xiang',), start_state='entry', end_state='exit',
        department_refs={'cinematography': refs['cinematography']})
    sref = SourcePin(key='scene:S02', kind='DESIGN', fingerprint=sha256_canonical(scene))
    href = SourcePin(key='shot:shot', kind='DESIGN', fingerprint=sha256_canonical(shot))
    for ref, value in ((sref, scene), (href, shot)):
        artifacts[ref.key], current[ref.key] = dump_contract(value), ref.fingerprint
    package = DirectorPackage(id='pkg', work_ref='work', source_refs=(SOURCE,), bible_refs=refs,
        scene_assembly_refs=(sref,), shot_assembly_refs=(href,), created_at=NOW, updated_at=NOW)
    receipt = {'kind': 'PROFESSIONAL_CREATIVE_APPROVAL', 'subjectId': package.id, 'workRef': 'work',
        'decision': 'APPROVE', 'subjectFingerprint': approval_subject(package), 'approvedBy': ['user:fixture']}
    approval = SourcePin(key='approval:pkg', kind='DESIGN', fingerprint=sha256_canonical(receipt))
    artifacts[approval.key], current[approval.key] = receipt, approval.fingerprint
    package = DirectorPackage.model_validate({**dump_contract(package), 'status': 'APPROVED',
        'approvedBy': ['user:fixture'], 'approvalRefs': [dump_contract(approval)]})
    projected = compile_prompt_projection(package, shot, artifacts, current, adapter='generic')
    assert projected['projection']['cinematography'] == [dump_contract(camera.content[0])]
    assert projected['executable'] is False and projected['providerCalls'] == 0
    with pytest.raises(ValueError, match='SHOT_NOT_PINNED'):
        compile_prompt_projection(package, shot.model_copy(update={'dramatic_purpose': 'new unauthorized intention'}), artifacts, current, adapter='generic')


def test_failed_qa_and_draft_leaf_cannot_report_review_ready(tmp_path):
    bibles, artifacts, current = baseline()
    bibles['historical-qa'] = with_records(bibles['historical-qa'], record({'checks': ['test failure'],
        'deterministic_status': 'FAIL', 'semantic_review_status': 'NOT_OBSERVED'}))
    bibles['prompt-compiler'] = with_records(bibles['prompt-compiler'], record({'projection_fields': ['pending']})).model_copy(update={'status': 'DRAFT'})
    rebind(bibles, artifacts, current)
    package = package_fixture(bibles, artifacts, current)
    result = validate_package(package, artifacts, current)
    assert result['status'] == 'BLOCKED_PROFESSIONAL_REVIEW'
    assert any(x.startswith('QA_FAILED:historical-qa') for x in result['blockers'])
    assert 'DEPARTMENT_DRAFT:prompt-compiler' in result['blockers']
    host = ProfessionalDepartmentHost(tmp_path)
    for bible in bibles.values():
        host.store.put(bible_pin(bible).key, dump_contract(bible))
    for department in ('asset-planning', 'reference-strategy'):
        assert host.task(department, task='plan', available=package.bible_refs, current=current)['status'] == 'BLOCKED'
    dashboard = {row['department']: row for row in host.dashboard(package, current=current)}
    assert dashboard['historical-qa']['status'] == 'FAILED_REVIEW'
    assert dashboard['historical-qa']['contractValidationStatus'] == 'PASS'
    assert dashboard['historical-qa']['validationStatus'] == 'FAIL'
    assert dashboard['reference-strategy']['validationStatus'] == 'BLOCKED'


def test_package_script_scope_and_optional_refs_cannot_escape_validation():
    bibles, artifacts, current = baseline()
    package = package_fixture(bibles, artifacts, current)
    with pytest.raises(ValueError, match='SCRIPT_OR_EPISODE'):
        validate_package(package.model_copy(update={'script_ref': 'other-script'}), artifacts, current)
    sref = package.scene_assembly_refs[0]
    scene = SceneAssembly.model_validate(artifacts[sref.key])
    bad = SourcePin(key='missing', kind='DESIGN', fingerprint='0' * 64)
    scene = scene.model_copy(update={'character_state_refs': (bad,)})
    bad_ref = SourcePin(key=sref.key, kind='DESIGN', fingerprint=sha256_canonical(scene))
    artifacts[sref.key], current[sref.key] = dump_contract(scene), bad_ref.fingerprint
    with pytest.raises(ValueError, match='CHARACTER_STATE_OWNER'):
        validate_package(package.model_copy(update={'scene_assembly_refs': (bad_ref,)}), artifacts, current)


def test_assembly_cannot_cite_different_canonical_object():
    bibles, artifacts, current = baseline()
    package = package_fixture(bibles, artifacts, current)
    ref = package.shot_assembly_refs[0]
    shot = ShotAssembly.model_validate(artifacts[ref.key]).model_copy(update={'source_ref': SOURCE})
    ref = SourcePin(key=ref.key, kind='DESIGN', fingerprint=sha256_canonical(shot))
    artifacts[ref.key], current[ref.key] = dump_contract(shot), ref.fingerprint
    with pytest.raises(ValueError, match='CANONICAL_SOURCE_ID'):
        validate_package(package.model_copy(update={'shot_assembly_refs': (ref,)}), artifacts, current)


def test_character_art_cannot_upgrade_shi_evidence():
    bibles, artifacts, current = baseline()
    entity = EntityIdentity(entity_id='shi', name='石', entity_type='person', historical_status='DRAMATIC_RECONSTRUCTION',
        identity_kind='ORIGINAL', evidence_refs=(SOURCE,), distinct_from=('huanchu',))
    bibles['historical-entity-registry'] = with_records(bibles['historical-entity-registry'], record(entity.model_dump(mode='json')))
    bibles['character-art'] = with_records(bibles['character-art'], record({'character_ref': 'shi', 'historical_status': 'DOCUMENTED'}))
    rebind(bibles, artifacts, current)
    with pytest.raises(ValueError, match='CANNOT_UPGRADE'):
        validate_bible(bibles['character-art'], artifacts, current)


def test_continuity_cannot_invent_state_citing_empty_owner():
    bibles, artifacts, current = baseline()
    ledger = with_records(bibles['continuity-supervisor'], state_record('invented', 'costume', 'strap', 'broken', 'S02', bibles['costume-design']))
    with pytest.raises(ValueError, match='OWNER_STATE_RECORD_MISSING'):
        validate_continuity(ledger, ledger.scene_refs, artifacts, current)
