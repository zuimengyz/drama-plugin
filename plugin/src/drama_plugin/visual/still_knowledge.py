"""Source-only STILL/LIVE_ACTION projection. No prose authoring, IO or providers.

Metadata models describe ordinary mapping receipts, not new creative entities.
The Host supplies current originals; only the existing serializer renders text.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Literal, Mapping, cast

from pydantic import BaseModel, ConfigDict, Field
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.specialized_asset import GlobalVisualStyle, SpecializedAssetBible, CharacterAsset, CostumeAsset, SceneAsset
from drama_plugin.contracts.visual_prompt import Fact, VisualPromptIR
from drama_plugin.specialized_asset import resolve, validate_assets
from drama_plugin.professional import validate_bible

VERSION = 'still-professional-map-v1'
CINE = frozenset('C02 C03 C04 C05 C06 C07 C09 C10 C11 C13 C15 C17 C28 C30 C35 C36'.split())
FACE = frozenset('F01 F02 F03 F04 F05 F06 F07 F08 F09 F10 F11 F12 F13 F14 F15 F16 F18 F20 F23 F24 F25 F27 F29 F30 F31 F32 F33 F34 F35 F36 F37 F38 F39 F40 F54'.split())
CURRENT = frozenset('pose gaze expression lighting composition camera action injury makeup'.split())


class Metadata(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Scope(Metadata):
    work_id: str = Field(min_length=1)
    scene_id: str = Field(min_length=1)
    shot_id: str = Field(min_length=1)
    actors: dict[str, str] = Field(default_factory=dict)  # character id -> approved arc stage


class Leaf(Metadata):
    pin: SourcePin
    pointer: str = Field(pattern=r'^/')


class MappingRow(Metadata):
    mapping_id: str = Field(pattern=r'^[a-zA-Z0-9_-]+$')
    capability_ids: tuple[str, ...] = Field(min_length=1)
    owner: str
    inputs: tuple[Leaf, ...] = Field(min_length=1)
    target: str = Field(pattern=r'^/')
    operation: Literal['COPY_LEAF', 'JOIN_ORDERED_LEAVES', 'SELECT_SCOPED_ITEM'] = 'COPY_LEAF'
    priority: Literal['CRITICAL', 'IMPORTANT', 'SECONDARY'] = 'CRITICAL'
    required: bool = True
    semantic_target: str | None = None  # correction destination's canonical domain, edits only


class Coverage(Metadata):
    capability_id: str
    canonical_field: Leaf
    use_requirement: Literal['REQUIRED_FOR_USE', 'OPTIONAL', 'NOT_OBSERVABLE_FOR_USE']
    evidence_state: Literal['VISIBLE', 'INFERRED', 'UNCONFIRMED']
    semantic_class: Literal['STABLE_IDENTITY', 'CURRENT_STATE', 'IMAGING']


class ReferenceDuty(Metadata):
    entity_key: str
    media_id: str
    version: str
    content_hash: str
    slot: int = Field(ge=1, le=3)
    actor_ids: tuple[str, ...] = ()
    carries: tuple[Literal['face', 'body', 'hair', 'marks', 'costume', 'scene', 'layout', 'prop'], ...] = Field(min_length=1)
    must_not_carry: tuple[str, ...]
    canonical_fields: tuple[Leaf, ...] = Field(min_length=1)
    evidence_state: Literal['VISIBLE', 'INFERRED', 'UNCONFIRMED']
    visibility: str = Field(min_length=1)
    use: str = Field(min_length=1)
    preservation_text: str = Field(min_length=1)


def pointer(value: Any, path: str) -> Any:
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        try:
            value = value[int(part)] if isinstance(value, (list, tuple)) else value[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError('STILL_SOURCE_POINTER_MISSING:' + path) from exc
    return value


def _assign(value: Any, path: str, fact: dict[str, Any]) -> None:
    parent, _, last = path.rpartition('/')
    dest = pointer(value, parent)
    if isinstance(dest, list):
        index = int(last)
        if index == len(dest):
            dest.append(fact)
        else:
            dest[index] = fact
    else:
        dest[last] = fact


def fact_paths(value: Any, prefix: str = '') -> dict[str, dict[str, Any]]:
    if isinstance(value, dict):
        if {'text', 'source', 'priority'} <= set(value):
            return {prefix: value}
        return {p: f for k, v in value.items() for p, f in fact_paths(v, prefix + '/' + k).items()}
    if isinstance(value, list):
        return {p: f for i, v in enumerate(value) for p, f in fact_paths(v, prefix + '/' + str(i)).items()}
    return {}


def validate_imaging(style: GlobalVisualStyle, originals: Mapping[str, Any], current: Mapping[str, str]) -> None:
    if style.imaging_character is None:
        return
    medium = resolve(style.runtime_ref, originals, current)
    if medium.get('medium') != 'LIVE_ACTION' or medium.get('workId') != style.work_id:
        raise ValueError('IMAGING_CHARACTER_STILL_LIVE_ACTION_ONLY')
    for ref in style.imaging_character.source_refs:
        bible = CreativeBible.model_validate(resolve(ref, originals, current))
        if (bible.work_ref != style.work_id or bible.status != 'APPROVED'
                or bible.created_by_capability not in {'director', 'cinematography', 'color-grading'}):
            raise ValueError('IMAGING_CHARACTER_APPROVED_BASIS_REQUIRED')
        validate_bible(bible, originals, current)


# Exact source fields, no caller-selected owner -> arbitrary destination permission.
CAMERA = {'shot_scale_philosophy': 'shot_size', 'spatial_readability': 'readable_details',
          'camera_point_of_view': 'perspective', 'camera_height': 'perspective',
          'camera_distance': 'perspective', 'perspective': 'perspective',
          'subject_hierarchy': 'framing', 'lens_intention': 'depth_cues'}
LIGHT = {'source': 'light_sources', 'motivation': 'light_sources', 'direction': 'light_sources',
         'practical_lights': 'light_sources', 'intensity_relationship': 'contrast', 'contrast': 'contrast',
         'falloff': 'realism', 'visibility_priorities': 'realism', 'day_night_continuity': 'time_of_day'}
ASSET = {'face': 'face', 'surface_state': 'face', 'physical_identity': 'face',
         'age_presentation': 'apparent_age', 'hair': 'hair', 'facial_hair': 'beard',
         'body': 'body_proportions', 'body_proportion': 'body_proportions'}


def _target(path: str) -> str:
    return re.sub(r'/\d+(?=/|$)', '/*', path)


def _leaf(leaf: Leaf, row: MappingRow, scope: Scope, originals: Mapping[str, Any],
          current: Mapping[str, str], subject_ids: list[str]) -> str:
    raw = resolve(leaf.pin, originals, current)
    value = pointer(raw, leaf.pointer)
    if not isinstance(value, str) or not value.strip() or '\n' in value:
        raise ValueError('STILL_MAPPING_REQUIRES_SINGLE_TEXT_LEAF')
    target = _target(row.semantic_target or row.target)
    if row.semantic_target and not re.fullmatch(r'/edit_delta/\d+/target_correction', row.target):
        raise ValueError('STILL_SEMANTIC_TARGET_ONLY_FOR_EDIT_CORRECTION')
    if raw.get('schemaVersion') == 'creative-bible-v1':
        bible = CreativeBible.model_validate(raw)
        if bible.status != 'APPROVED' or bible.work_ref != scope.work_id or bible.created_by_capability != row.owner:
            raise ValueError('STILL_SOURCE_OWNER_OR_APPROVAL')
        validate_bible(bible, originals, current)
        if (bible.scene_refs and scope.scene_id not in bible.scene_refs or
                bible.shot_refs and scope.shot_id not in bible.shot_refs):
            raise ValueError('STILL_SOURCE_SCOPE')
        match = re.fullmatch(r'/content/(\d+)/values/([^/]+)(/.*)?', leaf.pointer)
        if not match:
            raise ValueError('STILL_DECISION_LEAF_REQUIRED')
        record = bible.content[int(match[1])]
        field, tail = match[2], match[3] or ''
        if record.status != 'DECIDED' or not set(record.scope_refs) & {scope.work_id, scope.scene_id, scope.shot_id}:
            raise ValueError('STILL_UNRESOLVED_OR_OUT_OF_SCOPE')
        local_shots = set(record.scope_refs) & set(bible.shot_refs)
        local_scenes = set(record.scope_refs) & set(bible.scene_refs)
        if local_shots and scope.shot_id not in local_shots or local_scenes and scope.scene_id not in local_scenes:
            raise ValueError('STILL_RECORD_SCOPE')
        if record.values.get('scene_ref', scope.scene_id) != scope.scene_id or record.values.get('shot_ref', scope.shot_id) != scope.shot_id:
            raise ValueError('STILL_SOURCE_SCOPE')
        # reason, criteria and constraints are metadata unless an explicit approved
        # Reference Plan preservation decision is selected below.
        if tail and not re.fullmatch(r'/intent(?:/\d+)?', tail) and not (
                row.owner == 'reference-strategy' and field == 'reference_roles'
                and re.fullmatch(r'/\d+/preservation_text', tail)) and not (
                row.owner == 'reference-strategy' and field == 'requirements' and re.fullmatch(r'/preservation/\d+/intent', tail)) and not (
                row.owner == 'visual-continuity-qa' and field == 'findings' and re.fullmatch(r'/\d+/evidence', tail)):
            raise ValueError('STILL_METADATA_NOT_PROVIDER_FACT')
        allowed = False
        if row.owner == 'cinematography':
            allowed = field in CAMERA and target in {'/camera/' + CAMERA[field], '/camera/' + CAMERA[field] + '/*'}
        elif row.owner == 'lighting-design':
            allowed = field in LIGHT and target == '/lighting/' + LIGHT[field]
        elif row.owner in {'color-design', 'color-grading'}:
            allowed = field in {'scene_palettes', 'sequence_palettes', 'character_environment_color_relation',
                               'grade_intention', 'exposure_continuity', 'skin_preservation'} and target in {'/preserve/*', '/secondary_details/*'}
        elif row.owner == 'reference-strategy':
            allowed = field in {'reference_roles', 'requirements'} and bool(tail) and target == '/preserve/*'
        elif row.owner == 'visual-continuity-qa':
            allowed = field == 'findings' and target == '/edit_delta/*/source_issue'
        elif row.owner == 'blocking':
            allowed = field in {'actor_positions', 'actor_movements', 'eye_lines', 'physical_relations', 'physical_contacts', 'spatial_relationships'} and target.startswith('/blocking/')
        elif row.owner in {'action-choreography', 'dramatic-performance-direction'}:
            allowed = (target == '/action/expression' and row.owner == 'dramatic-performance-direction'
                       or target == '/action/current_visible_action' and row.owner == 'action-choreography'
                       or target == '/blocking/contact' and row.owner == 'action-choreography')
        elif row.owner == 'look-continuity':
            allowed = field in {'hair', 'beard', 'skin_condition', 'fatigue', 'dirt', 'blood', 'wounds', 'injury_progression', 'facial_wear'} and target == '/subjects/*/visible_condition'
            if allowed and record.values.get('character_ref') != subject_ids[int(row.target.split('/')[2])]:
                raise ValueError('STILL_CHARACTER_BINDING')
        elif row.owner in {'adaptation-boundary', 'historical-research', 'literary-source-input', 'scene-development'}:
            allowed = target.startswith('/world/') or target == '/lighting/time_of_day'
        elif row.owner == 'prop-design':
            allowed = field in {'appearance', 'scale', 'material', 'continuity_state', 'interaction_requirements'} and target in {'/environment/required_period_objects', '/preserve/*'}
            if record.values.get('scene_refs') and scope.scene_id not in record.values['scene_refs']:
                raise ValueError('STILL_PROP_SCENE_SCOPE')
        elif row.owner == 'character-dramaturgy':
            allowed = target == '/subjects/*/role' and record.values.get('character_ref') == subject_ids[int(row.target.split('/')[2])]
        if not allowed:
            raise ValueError('STILL_FIELD_AUTHORITY_VIOLATION:' + leaf.pointer + '->' + row.target)
    elif raw.get('schemaVersion') == 'specialized-asset-bible-v1':
        asset_bible = SpecializedAssetBible.model_validate(raw)
        if row.owner != 'specialized-asset-design' or asset_bible.work_id != scope.work_id or asset_bible.approval_ref is None:
            raise ValueError('STILL_ASSET_APPROVAL_REQUIRED')
        validate_assets(asset_bible, originals, current)
        match = re.fullmatch(r'/assets/(\d+)/decisions/([^/]+)/text', leaf.pointer)
        if not match:
            raise ValueError('STILL_ASSET_TEXT_REQUIRED')
        asset = asset_bible.assets[int(match[1])]; field = match[2]
        if isinstance(asset, (CharacterAsset, CostumeAsset)):
            if scope.actors.get(asset.character_id) != asset.arc_stage:
                raise ValueError('STILL_CHARACTER_STAGE')
            if not target.startswith('/subjects/*/') or subject_ids[int(row.target.split('/')[2])] != asset.character_id:
                raise ValueError('STILL_CHARACTER_BINDING')
            expected = ASSET.get(field) if asset.kind == 'CHARACTER' else 'costume'
            if target != '/subjects/*/' + str(expected):
                raise ValueError('STILL_STABLE_IDENTITY_CANNOT_OWN_CURRENT_STATE')
        elif isinstance(asset, SceneAsset) and (asset.scene_id != scope.scene_id or not target.startswith('/environment/')):
            raise ValueError('STILL_SCENE_BINDING')
    elif raw.get('schemaVersion') == 'global-visual-style-v1':
        style = GlobalVisualStyle.model_validate(raw)
        validate_imaging(style, originals, current)
        if (style.work_id != scope.work_id or row.owner != 'global-visual-style'
                or target not in {'/preserve/*', '/secondary_details/*'}
                or not re.fullmatch(r'/imagingCharacter/(photographicGenre|captureCharacter|opticalTexture/\d+/(intent|preservationConstraints/\d+))', leaf.pointer)):
            raise ValueError('STILL_IMAGING_SCOPE_OR_FIELD')
    else:
        raise ValueError('STILL_UNSUPPORTED_CREATIVE_SOURCE')
    return value


def make_receipt(*, scope: Scope, source_pins: tuple[SourcePin, ...], rows: tuple[MappingRow, ...],
                 originals: Mapping[str, Any], current: Mapping[str, str], subject_ids: list[str],
                 rule_catalog: dict[str, Any]) -> dict[str, Any]:
    scope = Scope.model_validate(scope.model_dump())
    rows = tuple(MappingRow.model_validate(r.model_dump()) for r in rows)
    if len({p.key for p in source_pins}) != len(source_pins):
        raise ValueError('STILL_DUPLICATE_SOURCE')
    if len({r.mapping_id for r in rows}) != len(rows) or len({r.target for r in rows}) != len(rows):
        raise ValueError('STILL_AMBIGUOUS_MAPPING')
    if set(subject_ids) != set(scope.actors):
        raise ValueError('STILL_ACTOR_SCOPE')
    catalog = {r['capability_id']: r for r in rule_catalog['rules']}
    result = []; atoms = set()
    for row in rows:
        if not set(row.capability_ids) <= CINE | FACE or not set(row.capability_ids) <= set(catalog):
            raise ValueError('STILL_KNOWLEDGE_NOT_ALLOWLISTED')
        if row.operation != 'JOIN_ORDERED_LEAVES' and len(row.inputs) != 1:
            raise ValueError('STILL_COPY_REQUIRES_ONE_LEAF')
        for leaf in row.inputs:
            if leaf.pin not in source_pins:
                raise ValueError('STILL_UNPINNED_SOURCE')
            atom = (leaf.pin.key, leaf.pointer)
            if atom in atoms:
                raise ValueError('STILL_DUPLICATE_FACT_DESTINATION')
            atoms.add(atom)
        if set(row.capability_ids) & ({'C17', 'C35', 'C36'} | {f'F{i:02d}' for i in range(30, 41)}):
            raise ValueError('STILL_QC_KNOWLEDGE_NOT_PROVIDER_FACT')
        text = ' '.join(_leaf(l, row, scope, originals, current, subject_ids) for l in row.inputs)
        if _target(row.target) == '/subjects/*/face':
            fields = [l.pointer.split('/')[-2] for l in row.inputs]
            if fields != sorted(fields, key=lambda f: ['face', 'surface_state', 'physical_identity'].index(f)):
                raise ValueError('STILL_FACE_JOIN_ORDER')
        result.append({**row.model_dump(mode='json'), 'text_hash': sha256_canonical(text),
                       'rule_refs': [{'rule_id': catalog[c]['rule_id'], 'rule_version': catalog[c]['rule_version'],
                                      'rule_hash': catalog[c]['rule_hash']} for c in row.capability_ids]})
    return {'schema_id': VERSION, 'mapping_version': 1, 'scope': scope.model_dump(mode='json'),
            'subject_ids': subject_ids, 'source_pins': [dump_contract(p) for p in source_pins],
            'rule_catalog_digest': sha256_canonical(rule_catalog), 'rows': result,
            'not_projected': ['reason', 'criteria', 'knowledge_provenance', 'coverage', 'evidence_state']}


def project_ir(base: dict[str, Any], receipt: dict[str, Any], receipt_pin: SourcePin,
               originals: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    if receipt_pin.fingerprint != sha256_canonical(receipt) or not receipt_pin.key.startswith('still-professional-map:'):
        raise ValueError('STILL_RECEIPT_PIN')
    ir = deepcopy(base)
    if ir['task']['task_type'] == 'VIDEO' or ir['task']['visual_medium'] != 'LIVE_ACTION':
        raise ValueError('STILL_LIVE_ACTION_ONLY')
    if [s['id'] for s in ir['subjects']] != receipt['subject_ids']:
        raise ValueError('STILL_SUBJECT_ORDER')
    scope = Scope.model_validate(receipt['scope'])
    for raw in receipt['rows']:
        row = MappingRow.model_validate({k: v for k, v in raw.items() if k not in {'text_hash', 'rule_refs'}})
        text = ' '.join(_leaf(l, row, scope, originals, current, receipt['subject_ids']) for l in row.inputs)
        if sha256_canonical(text) != raw['text_hash']:
            raise ValueError('STILL_MAPPING_TEXT_CHANGED')
        source = receipt_pin.key + '@' + receipt_pin.fingerprint + '#rows/' + row.mapping_id
        _assign(ir, row.target, Fact(text=text, source=source, priority=row.priority).model_dump(mode='json'))
    # No unbound side channel into the formal prompt, including preserve/negative.
    actual = fact_paths(ir)
    if set(actual) != {r['target'] for r in receipt['rows']}:
        raise ValueError('STILL_UNMAPPED_FACTS')
    return VisualPromptIR.model_validate(ir).model_dump(mode='json')


def check_binding(spec: Any) -> None:
    if not spec.prompt_ir or spec.prompt_normalization:
        raise ValueError('STILL_PROFESSIONAL_IR_REQUIRED')
    ir = VisualPromptIR.model_validate(spec.prompt_ir)
    if ir.task.task_type == 'VIDEO' or ir.task.visual_medium != 'LIVE_ACTION':
        raise ValueError('STILL_LIVE_ACTION_ONLY')
    pins = [p for p in spec.professional_sources if p.key.startswith('still-professional-map:')]
    if len(pins) != 1 or len({p.key for p in spec.professional_sources}) != len(spec.professional_sources):
        raise ValueError('STILL_EXACT_RECEIPT_REQUIRED')
    prefix = pins[0].key + '@' + pins[0].fingerprint + '#rows/'
    facts = fact_paths(ir.model_dump(mode='json'))
    if any(not f['source'].startswith(prefix) for f in facts.values()):
        raise ValueError('STILL_INVALID_FACT_SOURCE')
    if {a.entity_key for a in spec.actors} != {s.id for s in ir.subjects}:
        raise ValueError('STILL_ACTOR_SCOPE')
    if any(a.identity != next(s.face.text for s in ir.subjects if s.id == a.entity_key) for a in spec.actors):
        raise ValueError('STILL_ACTOR_IDENTITY_DIVERGES')


def validate_reference_plan(spec: Any, receipt: dict[str, Any], originals: Mapping[str, Any], current: Mapping[str, str]) -> None:
    scope = Scope.model_validate(receipt['scope'])
    duties: list[tuple[ReferenceDuty, str, str]] = []
    coverage: list[Coverage] = []
    preservations: list[tuple[dict[str, Any], str, str]] = []
    for raw in receipt['source_pins']:
        pin = SourcePin.model_validate(raw); data = resolve(pin, originals, current)
        if data.get('createdByCapability') != 'reference-strategy':
            continue
        bible = CreativeBible.model_validate(data)
        if bible.status != 'APPROVED' or bible.work_ref != scope.work_id:
            raise ValueError('STILL_REFERENCE_APPROVAL')
        validate_bible(bible, originals, current)
        for i, record in enumerate(bible.content):
            if record.status != 'DECIDED' or scope.shot_id not in record.scope_refs:
                continue
            for j, duty in enumerate(record.values.get('reference_roles', [])):
                duties.append((ReferenceDuty.model_validate(duty), pin.key, f'/content/{i}/values/reference_roles/{j}/preservation_text'))
            requirements = record.values.get('requirements', {})
            coverage.extend(Coverage.model_validate(c) for c in requirements.get('face_coverage', []))
            for j, item in enumerate(requirements.get('preservation', [])):
                preservations.append((item, pin.key, f'/content/{i}/values/requirements/preservation/{j}/intent'))
    if len(duties) != len(spec.references):
        raise ValueError('STILL_REFERENCE_DUTIES_REQUIRED')
    for duty, key, path in duties:
        if duty.slot > len(spec.references):
            raise ValueError('STILL_REFERENCE_SLOT_CHANGED')
        ref = spec.references[duty.slot - 1]
        if (ref.entity_key, ref.media_id, ref.version, ref.content_hash) != (duty.entity_key, duty.media_id, duty.version, duty.content_hash):
            raise ValueError('STILL_REFERENCE_SLOT_CHANGED')
        allowed = {'CHARACTER': {'face', 'body', 'hair', 'marks'}, 'COSTUME': {'costume'}, 'SCENE': {'scene', 'layout'}, 'PROP': {'prop'}}[ref.kind]
        if not set(duty.carries) <= allowed or set(duty.must_not_carry) != CURRENT:
            raise ValueError('STILL_REFERENCE_CURRENT_STATE_LEAKAGE')
        if duty.evidence_state != 'VISIBLE':
            raise ValueError('STILL_REFERENCE_UNCONFIRMED')
        expected = set(spec.reference_members.get(ref.entity_key, (ref.entity_key,))) if ref.kind == 'CHARACTER' else set(duty.actor_ids)
        if set(duty.actor_ids) != expected or not set(duty.actor_ids) <= set(scope.actors):
            raise ValueError('STILL_REFERENCE_ACTOR_BINDING')
        if not any(l['pin']['key'] == key and l['pointer'] == path and r['target'].startswith('/preserve/') for r in receipt['rows'] for l in r['inputs']):
            raise ValueError('STILL_REFERENCE_DUTY_NOT_CONSUMED')
        for leaf in duty.canonical_fields:
            data = resolve(leaf.pin, originals, current); pointer(data, leaf.pointer)
            match = re.fullmatch(r'/assets/(\d+)/decisions/([^/]+)/text', leaf.pointer)
            if ref.kind == 'PROP':
                prop_match = re.fullmatch(r'/content/(\d+)/values/(appearance|scale|material|continuity_state|interaction_requirements)(/intent)?', leaf.pointer)
                if (data.get('createdByCapability') != 'prop-design' or not prop_match
                        or data['content'][int(prop_match[1])]['values'].get('prop_id') != ref.asset_id
                        or not any(leaf.model_dump(mode='json') == l for r in receipt['rows'] for l in r['inputs'])):
                    raise ValueError('STILL_REFERENCE_PROP_AUTHORITY')
                continue
            if not match or data.get('schemaVersion') != 'specialized-asset-bible-v1':
                raise ValueError('STILL_REFERENCE_CANONICAL_ASSET_REQUIRED')
            asset = data['assets'][int(match[1])]
            carry_fields = {'face': {'face'}, 'body': {'body', 'body_proportion'}, 'hair': {'hair', 'facial_hair'},
                            'marks': {'physical_identity'}, 'costume': set(asset['decisions']),
                            'scene': set(asset['decisions']), 'layout': {'spatial_hierarchy', 'interior_structure'}, 'prop': set()}
            if (match[2] not in set().union(*(carry_fields[c] for c in duty.carries))
                    or asset['kind'] != ref.kind
                    or (ref.entity_key not in spec.reference_members and asset['id'] != ref.asset_id)
                    or asset.get('characterId') and asset['characterId'] not in duty.actor_ids):
                raise ValueError('STILL_REFERENCE_CARRY_AUTHORITY')
            if not any(leaf.model_dump(mode='json') == l for r in receipt['rows'] for l in r['inputs']):
                raise ValueError('STILL_REFERENCE_CARRY_UNMAPPED')
    if len({d.slot for d, _, _ in duties}) != len(duties):
        raise ValueError('STILL_REFERENCE_DUPLICATE_SLOT')
    for c in coverage:
        if c.capability_id not in FACE:
            raise ValueError('STILL_FACE_COVERAGE_CAPABILITY')
        if c.semantic_class != 'STABLE_IDENTITY':
            raise ValueError('STILL_MIXED_IDENTITY_LEAF_RETURN_TO_OWNER')
        if c.use_requirement == 'REQUIRED_FOR_USE':
            if c.evidence_state == 'UNCONFIRMED' or not any(c.canonical_field.model_dump(mode='json') == l for r in receipt['rows'] for l in r['inputs']):
                raise ValueError('STILL_REQUIRED_FACE_COVERAGE_MISSING')
            projected = [r for r in receipt['rows'] if c.canonical_field.model_dump(mode='json') in r['inputs']]
            if not any(r['required'] for r in projected):
                preserved = any(c.canonical_field.model_dump(mode='json') in item.get('canonical_fields', [])
                    and any(r['required'] and r['target'].startswith('/preserve/') and
                            any(l['pin']['key'] == key and l['pointer'] == path for l in r['inputs']) for r in receipt['rows'])
                    for item, key, path in preservations)
                if not preserved:
                    raise ValueError('STILL_REQUIRED_FACE_PRESERVATION_MISSING')
    face_leaves = [l for r in receipt['rows'] if _target(r['target']) in {'/subjects/*/face', '/subjects/*/apparent_age', '/subjects/*/hair', '/subjects/*/beard'} for l in r['inputs']]
    if any(not any(c.canonical_field.model_dump(mode='json') == l for c in coverage) for l in face_leaves):
        raise ValueError('STILL_FACE_SEMANTIC_COVERAGE_REQUIRED')


def replay(spec: Any, receipt: dict[str, Any], originals: Mapping[str, Any], current: Mapping[str, str],
           rule_catalog: dict[str, Any]) -> None:
    check_binding(spec)
    pins = tuple(SourcePin.model_validate(p) for p in receipt['source_pins'])
    receipt_pin = next(p for p in spec.professional_sources if p.key.startswith('still-professional-map:'))
    if set((p.key, p.kind, p.fingerprint) for p in spec.professional_sources) != set((p.key, p.kind, p.fingerprint) for p in (*pins, receipt_pin)):
        raise ValueError('STILL_SOURCE_PIN_SET')
    if receipt['scope']['shot_id'] != spec.shot_id:
        raise ValueError('STILL_SHOT_SCOPE')
    rows = tuple(MappingRow.model_validate({k: v for k, v in r.items() if k not in {'text_hash', 'rule_refs'}}) for r in receipt['rows'])
    expected = make_receipt(scope=Scope.model_validate(receipt['scope']), source_pins=pins, rows=rows,
        originals=originals, current=current, subject_ids=receipt['subject_ids'], rule_catalog=rule_catalog)
    if expected != receipt:
        raise ValueError('STILL_RECEIPT_CHANGED')
    if project_ir(spec.prompt_ir, receipt, receipt_pin, originals, current) != spec.prompt_ir:
        raise ValueError('STILL_IR_FACT_CHANGED')
    validate_reference_plan(spec, receipt, originals, current)
    # Every explicitly required atom must actually survive the unchanged serializer.
    from drama_plugin.visual.prompt_ir import compile_ir
    compiled = compile_ir(spec.prompt_ir, provider_family=spec.prompt_ir['task']['provider_family'])
    retained = {r['source'] for r in compiled['retained']}
    for row in receipt['rows']:
        locator = receipt_pin.key + '@' + receipt_pin.fingerprint + '#rows/' + row['mapping_id']
        if row['required'] and locator not in retained:
            raise ValueError('STILL_REQUIRED_FACT_NOT_CONSUMED:' + row['target'])
    # A nonempty Work imaging choice cannot disappear through an unsupported path.
    for pin in pins:
        raw = originals[pin.key]
        if raw.get('schemaVersion') == 'global-visual-style-v1' and raw.get('imagingCharacter'):
            imaging = raw['imagingCharacter']
            required = [f'/imagingCharacter/{k}' for k in ('photographicGenre', 'captureCharacter') if imaging.get(k)]
            for i, texture in enumerate(imaging['opticalTexture']):
                required += [f'/imagingCharacter/opticalTexture/{i}/intent']
                required += [f'/imagingCharacter/opticalTexture/{i}/preservationConstraints/{j}' for j in range(len(texture['preservationConstraints']))]
            mapped = {l['pointer'] for r in receipt['rows'] for l in r['inputs'] if l['pin']['key'] == pin.key}
            if not set(required) <= mapped:
                raise ValueError('STILL_IMAGING_CHARACTER_NOT_CONSUMED')


# Existing categories and repair owners only. QA observes; it never edits a source.
QC = {
    'QC-CAMERA': ('CAMERA', 'cinematography'), 'QC-IDENTITY': ('IDENTITY', 'specialized-asset-design'),
    'QC-COSTUME': ('COSTUME', 'specialized-asset-design'), 'QC-MATERIAL': ('COSMETIC', 'lighting-design'),
    'QC-CONTACT': ('BLOCKING', 'blocking'), 'QC-LIGHT-MOTIVATION': ('COSMETIC', 'lighting-design'),
    'QC-LIGHT-DIRECTION': ('COSMETIC', 'lighting-design'), 'QC-COLOR': ('COSMETIC', 'color-grading'),
    'QC-READABILITY': ('CAMERA', 'cinematography'), 'QC-CONTACT-SHADOW': ('COSMETIC', 'lighting-design'),
    'QC-INTEGRATION': ('CONTINUITY', 'shot-production'), 'QC-REFERENCE-LEAKAGE': ('CONTINUITY', 'reference-strategy'),
    'QC-FACE-GEOMETRY': ('IDENTITY', 'specialized-asset-design'), 'QC-AGE-DRIFT': ('IDENTITY', 'specialized-asset-design'),
    'QC-BEAUTIFICATION-DRIFT': ('IDENTITY', 'specialized-asset-design'), 'QC-SKIN-RESPONSE': ('COSMETIC', 'lighting-design'),
    'QC-EYES-TEETH': ('ANATOMY', 'shot-production'), 'QC-EAR-INTEGRITY': ('ANATOMY', 'shot-production'),
    'QC-JAW-CHIN': ('IDENTITY', 'specialized-asset-design'), 'QC-HAIRLINE-EDGE': ('CONTINUITY', 'look-continuity'),
    'QC-STABLE-MARKS': ('IDENTITY', 'specialized-asset-design'),
}


class Observation(Metadata):
    criterion_id: str
    criterion_version: Literal[1] = 1
    actor: str = Field(min_length=1)
    arc_stage: str = Field(min_length=1)
    requirement: Leaf
    media_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    reference_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    region: str = Field(min_length=1)
    use: str = Field(min_length=1)
    visible: bool
    applicable: bool = True
    comparison: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    status: Literal['PASS', 'FAIL', 'UNKNOWN']
    impact: str = Field(min_length=1)
    root_cause_hypothesis: str = Field(min_length=1)
    confidence: Literal['LOW', 'MEDIUM', 'HIGH']
    repair_owner: str
    severity: Literal['MAJOR', 'MINOR'] | None = None
    remedy: Literal['REGENERATE', 'POSTPROCESS', 'ACCEPT'] = 'ACCEPT'
    preserve_scope: str = Field(min_length=1)


def observation_review(*, attempt_id: str, output_hash: str, reviewer: str, evidence_ref: str,
                       observations: tuple[Observation, ...], originals: Mapping[str, Any],
                       current: Mapping[str, str]) -> dict[str, Any]:
    """Validate manual observations and project into existing Review and QA values.

    No image classifier, subjective CG score, new disposition or retry executor.
    """
    from drama_plugin.visual.production import Review, Finding, CATEGORIES, _review_status
    checks: dict[str, Literal['PASS', 'FAIL', 'UNKNOWN']] = {}
    findings = []; routes = []; normalized = []
    for item in observations:
        item = Observation.model_validate(item.model_dump())
        if item.criterion_id not in QC:
            raise ValueError('STILL_UNKNOWN_QC_CRITERION')
        identity = item.criterion_id + ':' + item.actor
        if identity in checks:
            raise ValueError('STILL_DUPLICATE_QC_OBSERVATION')
        requirement = resolve(item.requirement.pin, originals, current)
        pointer(requirement, item.requirement.pointer)
        if requirement.get('schemaVersion') == 'specialized-asset-bible-v1':
            asset_bible = SpecializedAssetBible.model_validate(requirement)
            if asset_bible.approval_ref is None:
                raise ValueError('STILL_QC_APPROVED_REQUIREMENT')
            validate_assets(asset_bible, originals, current)
            match = re.match(r'/assets/(\d+)/', item.requirement.pointer)
            if not match:
                raise ValueError('STILL_QC_ASSET_REQUIREMENT')
            asset = asset_bible.assets[int(match[1])]
            if isinstance(asset, (CharacterAsset, CostumeAsset)) and (asset.character_id, asset.arc_stage) != (item.actor, item.arc_stage):
                raise ValueError('STILL_QC_CHARACTER_STAGE')
        elif requirement.get('schemaVersion') == 'creative-bible-v1':
            bible = CreativeBible.model_validate(requirement)
            if bible.status != 'APPROVED':
                raise ValueError('STILL_QC_APPROVED_REQUIREMENT')
            validate_bible(bible, originals, current)
        else:
            raise ValueError('STILL_QC_APPROVED_REQUIREMENT')
        if item.repair_owner not in {QC[item.criterion_id][1], 'shot-production', 'prompt-compiler',
                'specialized-asset-design', 'reference-strategy', 'look-continuity', 'lighting-design',
                'color-grading', 'blocking', 'dramatic-performance-direction', 'cinematography'}:
            raise ValueError('STILL_QA_CANNOT_CREATE_REPAIR_OWNER')
        if item.media_hash and item.media_hash != output_hash:
            raise ValueError('STILL_QC_WRONG_OUTPUT')
        status = item.status if item.media_hash and item.visible else 'UNKNOWN'
        if item.criterion_id == 'QC-REFERENCE-LEAKAGE' and not item.reference_hash:
            status = 'UNKNOWN'
        normalized.append({**item.model_dump(mode='json'), 'status': status})
        if not item.applicable:
            continue
        if status == 'FAIL':
            if item.severity is None:
                raise ValueError('STILL_QC_IMPACT_SEVERITY_REQUIRED')
            findings.append(Finding(category=cast(CATEGORIES, QC[item.criterion_id][0]), severity=item.severity,
                evidence=evidence_ref + '#' + identity + ': ' + item.observation + '; impact: ' + item.impact,
                remedy=item.remedy))
            checks[identity] = 'FAIL' if item.severity == 'MAJOR' else 'PASS'
            routes.append({'finding': identity, 'owner': item.repair_owner, 'hypothesis': item.root_cause_hypothesis,
                           'confidence': item.confidence, 'preserve_scope': item.preserve_scope})
        else:
            checks[identity] = status
    if not checks:
        raise ValueError('STILL_QC_NO_APPLICABLE_OBSERVATIONS')
    review = Review(attempt_id=attempt_id, output_hash=output_hash, reviewer=reviewer,
                    evidence=evidence_ref, checks=checks, findings=tuple(findings))
    review_status = _review_status(review)
    return {'review': review.model_dump(mode='json'), 'status': review_status, 'observations': normalized,
            'qa_values': {'checks': checks, 'deterministic_status': 'PASS',
                'semantic_review_status': 'FAIL' if review_status == 'FAIL' else 'NOT_OBSERVED' if review_status == 'PENDING_REVIEW' else 'PASS',
                'findings': [f.model_dump(mode='json') for f in findings], 'evidence_refs': [evidence_ref], 'owner_routes': routes}}
