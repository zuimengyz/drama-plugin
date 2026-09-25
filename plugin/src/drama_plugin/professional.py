"""Professional department registry, authority gates and deterministic assembly.

The functions in this module do not write story, invent missing designs, invoke
an LLM or call a production provider. A Host supplies each department's work.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, cast
import re

from drama_plugin.specialized_asset import FORWARDED_DEPARTMENTS
from drama_plugin.contracts.base import dump_contract, sha256_canonical, canonical_json
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.contracts.professional import (
    CreativeBible, DepartmentDefinition, DirectorPackage, SceneAssembly,
    ShotAssembly, ContinuityState, EntityIdentity,
)

# Fields are professional ownership boundaries, not instructions to fill every
# slot. Scene/shot/entity/environment refs are explicit relationships only.
_SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    ('runtime-visual-medium', 'MovieVisualMedium', 'MODULE', '', 'medium configuration_source'),
    ('global-visual-style', 'GlobalVisualStyle', 'MODULE', 'runtime-visual-medium', 'realism render_stylization material_philosophy lighting_philosophy readability consistency imaging_character'),
    ('specialized-asset-design', 'SpecializedAssetBible', 'SKILL', 'runtime-visual-medium global-visual-style character-dramaturgy scene-development director adaptation-boundary', 'assets'),
    ('historical-research', 'Historical Source Bible', 'SKILL', '', 'sources facts timeline geography participants military_relationships confidence uncertainty'),
    ('historical-entity-registry', 'Historical Entity Bible', 'MODULE', 'historical-research', 'entity_id name entity_type historical_status identity_kind historical_identity_ref evidence_refs distinct_from'),
    ('adaptation-boundary', 'Adaptation Boundary Bible', 'SKILL', 'historical-research historical-entity-registry', 'claim historical_status source_basis reconstruction_boundary excluded_with_reason uncertainty'),
    ('story-architecture', 'Story Bible', 'SKILL', 'adaptation-boundary', 'premise theme protagonist dramatic_question acts sequences escalation climax ending'),
    ('character-dramaturgy', 'Character Bible', 'SKILL', 'story-architecture historical-entity-registry', 'character_ref personality objective internal_conflict relationships dramatic_function character_arc historical_authority arc_stage behavior_pattern social_position emotional_state performance_state'),
    ('scene-development', 'Scene Beat Bible', 'SKILL', 'story-architecture character-dramaturgy', 'scene_ref scene_purpose conflict beats reversal emotional_change information_change causality'),
    ('dialogue-design', 'Dialogue Bible', 'SKILL', 'scene-development character-dramaturgy', 'line_id scene_ref dialogue_text subtext historical_register speaker listener continuity'),
    ('director', 'Director Vision Bible', 'SKILL', 'story-architecture scene-development adaptation-boundary', 'cinematic_interpretation narrative_emphasis film_grammar visual_hierarchy performance_philosophy rhythm_philosophy restraint_principles climax_philosophy ending_philosophy editorial_intent'),
    ('character-art', 'Character Art Bible', 'SKILL', 'director adaptation-boundary character-dramaturgy', 'character_ref historical_status visual_archetype apparent_age height_impression body_proportion body_mass shoulder_waist_ratio face_structure jaw eyes brows nose skin hair facial_hair silhouette dominant_visual_traits secondary_traits screen_presence realistic_route cg_route camera_readable_features continuity_anchors forbidden_appearance phase_ii_reference_requirements'),
    ('costume-design', 'Costume Bible', 'SKILL', 'director adaptation-boundary character-dramaturgy character-art', 'character_ref costume_identity rank_distinction garment_construction_intent armor_intent materials layering wear damage stage_variants continuity'),
    ('look-continuity', 'Look Continuity Bible', 'SKILL', 'character-art costume-design scene-development', 'character_ref hair beard skin_condition fatigue dirt blood wounds injury_progression facial_wear continuity'),
    ('environment-design', 'Environment Bible', 'SKILL', 'director adaptation-boundary scene-development', 'environment_ref location_identity location_type parent_location_id macro_geography terrain topology entrances exits routes zones line_of_sight scale physical_constraints ground_condition weather spatial_continuity'),
    ('environment-art', 'Environment Art Bible', 'SKILL', 'director adaptation-boundary environment-design', 'environment_ref visual_thesis historical_visual_basis architectural_language structural_language shape_language silhouette mass_distribution material_palette surface_character wear damage age weathering visual_density hero_set_features secondary_visual_features scene_identity character_environment_contrast cg_route realistic_route visual_continuity_anchors forbidden_visuals phase_ii_reference_requirements'),
    ('set-decoration', 'Set Dressing Bible', 'SKILL', 'environment-design environment-art', 'environment_ref living_traces daily_use_objects military_clutter storage placement_density used_unused_areas smoke_marks footprints discarded_objects lived_in_state continuity'),
    ('prop-design', 'Prop Bible', 'SKILL', 'adaptation-boundary scene-development environment-design', 'prop_id appearance scale material function owner scene_refs continuity_state interaction_requirements'),
    ('animal-design', 'Animal Mount Bible', 'SKILL', 'director adaptation-boundary character-dramaturgy prop-design', 'animal_ref identity appearance distinguishing_features tack scale fatigue dirt continuity interaction_constraints'),
    ('production-design', 'Production Design Alignment', 'AGGREGATOR', 'character-art costume-design look-continuity environment-art set-decoration prop-design animal-design', 'alignment_findings visual_cohesion conflicts owner_routes resolution_refs'),
    ('scene-layout', 'Scene Layout Bible', 'SKILL', 'environment-design scene-development prop-design', 'scene_ref zones character_positions movement_lanes army_placement action_object_placement'),
    ('blocking', 'Blocking Bible', 'SKILL', 'scene-layout scene-development', 'scene_ref beat_ref actor_positions actor_movements eye_lines handoffs entrances exits physical_relations'),
    ('dramatic-performance-direction', 'Performance Bible', 'SKILL', 'blocking character-dramaturgy dialogue-design director', 'scene_ref beat_ref line_ref character_ref objective immediate_intention emotional_state restraint gestures micro_actions reactions listener_performance breathing_behavior physical_state'),
    ('action-choreography', 'Action Bible', 'SKILL', 'blocking prop-design dramatic-performance-direction animal-design', 'scene_ref action_id participants ordered_actions body_mechanics contact_constraints causality outcome continuity'),
    ('battle-crowd-choreography', 'Battle Crowd Bible', 'SKILL', 'environment-design historical-entity-registry action-choreography', 'scene_ref army_movement formation_change cavalry_movement infantry_movement crowd_reaction retreat pursuit group_timing local_global_reaction causal_order'),
    ('cinematography', 'Camera Bible', 'SKILL', 'director scene-layout dramatic-performance-direction action-choreography', 'scene_ref camera_point_of_view shot_scale_philosophy perspective lens_intention camera_height camera_distance camera_movement spatial_readability subject_hierarchy'),
    ('lighting-design', 'Lighting Bible', 'SKILL', 'environment-art cinematography', 'scene_ref environment_ref source motivation direction intensity_relationship contrast falloff visibility_priorities practical_lights day_night_continuity'),
    ('color-design', 'Color Script', 'SKILL', 'director environment-art lighting-design production-design', 'film_color_arc sequence_palettes scene_palettes character_environment_color_relation emotional_color_progression'),
    ('shot-design', 'Shot Bible', 'SKILL', 'cinematography blocking action-choreography', 'shot_ref scene_ref purpose subjects coverage start_state end_state transition_relationship duration_intention'),
    ('voice-direction', 'Voice Bible', 'SKILL', 'dialogue-design dramatic-performance-direction', 'line_ref scene_ref character_ref intention listener pace breath pause emphasis restraint interruption overlap'),
    ('voice-identity', 'Voice Identity Bible', 'SKILL', 'character-dramaturgy voice-direction', 'character_ref voice_identity timbre age_impression vocal_weight stability cross_scene_identity'),
    ('diegetic-vocal', 'Vocal Performance Bible', 'SKILL', 'dialogue-design adaptation-boundary voice-direction', 'scene_ref text_ref vocal_form dramatic_function vocal_intention collective_relation historical_uncertainty reconstruction_boundary continuity'),
    ('sound-design', 'Sound Bible', 'SKILL', 'environment-design action-choreography', 'scene_ref environment_ref ambience foley weapon_sound horse_sound distance acoustic_space foreground_background_relationship silence_design sound_action_alignment'),
    ('music-direction', 'Music Bible', 'SKILL', 'director', 'score_cues no_music_zones entrance exit escalation performance_priority dialogue_priority climax_relationship'),
    ('editorial-design', 'Editorial Bible', 'SKILL', 'shot-design dramatic-performance-direction sound-design music-direction', 'scene_ref shot_ref cut_points holds reaction_duration temporal_compression montage scene_transitions rhythm pacing'),
    ('vfx-planning', 'VFX Bible', 'SKILL', 'shot-design environment-art battle-crowd-choreography', 'scene_ref shot_ref crowd_extension distant_army smoke_dust_enhancement environment_extension compositing_requirements historical_limits'),
    ('color-grading', 'Grade Bible', 'SKILL', 'color-design lighting-design', 'grade_intention exposure_continuity tonal_range skin_preservation delivery_constraints'),
    ('graphics-design', 'Graphics Bible', 'SKILL', 'historical-entity-registry director', 'first_appearance_name_tags titles captions chapter_cards date_location_graphics typography placement'),
    ('continuity-supervisor', 'Continuity Ledger', 'AGGREGATOR', 'historical-research historical-entity-registry adaptation-boundary story-architecture character-dramaturgy scene-development dialogue-design director character-art costume-design look-continuity environment-design environment-art set-decoration prop-design animal-design production-design scene-layout blocking dramatic-performance-direction action-choreography battle-crowd-choreography cinematography lighting-design color-design shot-design voice-direction voice-identity diegetic-vocal sound-design music-direction editorial-design vfx-planning color-grading graphics-design', 'entity domain property state effective_from effective_until effective_from_event effective_until_event effective_from_phase effective_until_phase effective_until_shot_ref changed_by scene_ref shot_ref predecessor restored restoration_ref owner_record_id owner_state_path'),
    ('historical-qa', 'Historical QA', 'VALIDATOR', 'adaptation-boundary historical-entity-registry character-dramaturgy continuity-supervisor', 'checks deterministic_status semantic_review_status findings evidence_refs owner_routes'),
    ('visual-continuity-qa', 'Visual Continuity QA', 'VALIDATOR', 'continuity-supervisor production-design lighting-design', 'checks deterministic_status semantic_review_status findings evidence_refs owner_routes'),
    ('performance-qa', 'Performance QA', 'VALIDATOR', 'blocking action-choreography dramatic-performance-direction continuity-supervisor', 'checks deterministic_status semantic_review_status findings evidence_refs owner_routes'),
    ('av-alignment-qa', 'AV Alignment QA', 'VALIDATOR', 'dialogue-design voice-direction sound-design dramatic-performance-direction shot-design continuity-supervisor', 'checks deterministic_status semantic_review_status findings evidence_refs owner_routes'),
    ('spatial-continuity-qa', 'Spatial Continuity QA', 'VALIDATOR', 'environment-design scene-layout blocking cinematography continuity-supervisor', 'checks deterministic_status semantic_review_status findings evidence_refs owner_routes'),
    ('asset-planning', 'Asset Manifest', 'SKILL', 'historical-qa visual-continuity-qa performance-qa av-alignment-qa spatial-continuity-qa', 'asset_id asset_kind source_design_refs required_variants production_need phase_ii_requirements'),
    ('reference-strategy', 'Reference Plan', 'SKILL', 'asset-planning shot-design', 'shot_ref input_mode reference_images reference_roles start_frame_ref end_frame_ref reference_video_ref requirements unresolved_capability'),
    ('clip-decomposition', 'Generation Clip Plan', 'SKILL', 'reference-strategy editorial-design', 'shot_ref clips continuity_handoffs total_seconds provider_limit_seconds feasibility unresolved_capability'),
    ('video-model-selection', 'Video Route Policy', 'SKILL', 'clip-decomposition', 'fitness quality cost provider_capability route_candidates verified_capabilities unresolved_capability'),
    ('prompt-compiler', 'Prompt Compiler Contract', 'MODULE', 'video-model-selection reference-strategy clip-decomposition', 'approved_input_refs projection_fields adapter_contract unresolved_capability'),
)


def _specs(source_type: str) -> tuple[tuple[str, str, str, str, str], ...]:
    if source_type == 'HISTORICAL':
        return _SPECS
    if source_type != 'LITERARY':
        raise ValueError('UNSUPPORTED_CREATIVE_SOURCE_TYPE')
    # Only historical upstream assumptions change. Professional execution owners remain.
    replacements = {'historical-research': 'literary-source-input',
        'historical-entity-registry': 'literary-source-input',
        'adaptation-boundary': 'literary-source-input', 'historical-qa': 'literary-source-qa'}
    rows = [('literary-source-input', 'Literary Screenplay Input Bible', 'MODULE', '', 'source_package screenplay_input')]
    for identity, output, kind, deps, fields in _SPECS:
        if identity in {'historical-research', 'historical-entity-registry', 'adaptation-boundary'}:
            continue
        deps = ' '.join(dict.fromkeys(replacements.get(d, d) for d in deps.split()))
        identity = replacements.get(identity, identity)
        if identity == 'literary-source-qa':
            output = 'Literary Source QA'
        fields = fields.replace('historical_status', 'source_identity').replace('historical_authority', 'source_authority')
        fields = fields.replace('historical_visual_basis', 'source_visual_basis').replace('historical_register', 'source_register')
        fields = fields.replace('historical_uncertainty', 'source_uncertainty').replace('historical_limits', 'source_limits')
        if identity == 'character-art':
            fields += ' arc_continuity_boundaries'
        rows.append((identity, output, kind, deps, fields))
    return tuple(rows)


def registry(source_type: str = 'HISTORICAL') -> dict[str, DepartmentDefinition]:
    result: dict[str, DepartmentDefinition] = {}
    specs = _specs(source_type)
    for identity, output, kind, deps, fields in specs:
        owned = tuple(fields.split())
        result[identity] = DepartmentDefinition(
            department_id=identity, name=output, capability_type=cast(Literal['SKILL', 'MODULE', 'VALIDATOR', 'AGGREGATOR'], kind),
            authority_scope=owned, output_contract=output, depends_on=tuple(deps.split()),
            consumed_by=tuple(row[0] for row in specs if identity in row[3].split()),
            can_create=owned, can_modify=owned,
            cannot_modify=('other_department_content', 'canonical_story', 'canonical_dialogue', 'historical_evidence_upgrade' if source_type == 'HISTORICAL' else 'literary_source_or_adaptation_rewrite'),
            skill_code=identity if kind == 'SKILL' or identity == 'production-design' else None,
            rationale=('Independent professional creative judgment and revision boundary.' if kind == 'SKILL' or identity == 'production-design'
                else 'Deterministic identity/index/projection; no new creative judgment.' if kind == 'MODULE'
                else 'Aggregates source-owned state without creative authority.' if kind == 'AGGREGATOR'
                else 'Independent deterministic checks with separately reported semantic observation.'),
        )
    for identity, validator in {'runtime-visual-medium': 'SpecializedAssetHost.bind_movie',
            'global-visual-style': 'SpecializedAssetHost.save_style',
            'specialized-asset-design': 'specialized_asset.validate_assets'}.items():
        result[identity] = result[identity].model_copy(update={'validator': validator})
    for identity in FORWARDED_DEPARTMENTS:
        result[identity] = result[identity].model_copy(update={
            'authority_owner': 'specialized-asset-design', 'deprecated_forward_to': 'specialized-asset-design',
            'can_create': (), 'can_modify': (), 'skill_code': 'specialized-asset-design',
            'rationale': 'Read-only legacy design view. New concrete design is owned by SpecializedAssetBible.'})
    return result


def dependency_order(source_type: str = 'HISTORICAL') -> tuple[str, ...]:
    definitions = registry(source_type)
    ordered: list[str] = []
    remaining = set(definitions)
    while remaining:
        ready = sorted(k for k in remaining if set(definitions[k].depends_on) <= set(ordered))
        if not ready:
            raise ValueError('PROFESSIONAL_DEPENDENCY_CYCLE_OR_UNKNOWN_DEPARTMENT')
        ordered.extend(ready)
        remaining.difference_update(ready)
    return tuple(ordered)


def bible_pin(bible: CreativeBible) -> SourcePin:
    return SourcePin(key='bible:' + bible.id, kind='DESIGN', fingerprint=sha256_canonical(bible))


def _fresh(ref: SourcePin, current: Mapping[str, str]) -> None:
    if current.get(ref.key) != ref.fingerprint:
        raise ValueError('STALE_OR_MISSING_SOURCE:' + ref.key)


def _read(ref: SourcePin, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> Any:
    _fresh(ref, current)
    if ref.key not in artifacts or sha256_canonical(artifacts[ref.key]) != ref.fingerprint:
        raise ValueError('MISSING_OR_CORRUPT_ARTIFACT:' + ref.key)
    return artifacts[ref.key]


_FORBIDDEN_ENVIRONMENT_KEYS = frozenset({'final_camera', 'camera', 'music_cue', 'voice_acting', 'costume_design', 'lighting', 'sound'})
_PROVIDER_KEYS = frozenset({'seed', 'seedance_request', 'comfy_request', 'workflow_json', 'provider_prompt', 'negative_prompt', 'sampler', 'cfg_scale'})


def _nested_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        normalized = {re.sub(r'(?<!^)(?=[A-Z])', '_', str(key)).lower() for key in value}
        return normalized | {key for child in value.values() for key in _nested_keys(child)}
    if isinstance(value, (list, tuple)):
        return {key for child in value for key in _nested_keys(child)}
    return set()


def approval_subject(artifact: CreativeBible | DirectorPackage) -> str:
    body = dump_contract(artifact)
    for key in ('status', 'approvedBy', 'approvalRefs', 'updatedAt'):
        body.pop(key, None)
    return sha256_canonical(body)


def _validate_approvals(artifact: CreativeBible | DirectorPackage, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> None:
    for ref in artifact.approval_refs:
        receipt = _read(ref, artifacts, current)
        if not isinstance(receipt, dict) or receipt.get('kind') != 'PROFESSIONAL_CREATIVE_APPROVAL' or receipt.get('subjectId') != artifact.id or receipt.get('workRef') != artifact.work_ref or receipt.get('decision') != 'APPROVE' or receipt.get('subjectFingerprint') != approval_subject(artifact) or set(receipt.get('approvedBy', ())) != set(artifact.approved_by):
            raise ValueError('APPROVAL_RECEIPT_NOT_BOUND_TO_EXACT_CREATIVE_CONTENT')


def _inherited_entity(identity: str, dependencies: Sequence[CreativeBible], artifacts: Mapping[str, Any], current: Mapping[str, str]) -> EntityIdentity:
    queue = list(dependencies)
    seen: set[str] = set()
    matches: dict[str, EntityIdentity] = {}
    while queue:
        bible = queue.pop()
        if bible.id in seen:
            continue
        seen.add(bible.id)
        if bible.created_by_capability == 'historical-entity-registry':
            for record in bible.content:
                entity = EntityIdentity.model_validate(record.values)
                if entity.entity_id == identity:
                    matches[record.id] = entity
        queue.extend(CreativeBible.model_validate(_read(ref, artifacts, current)) for ref in bible.depends_on)
    if len(matches) != 1:
        raise ValueError('CREATIVE_CHARACTER_REQUIRES_EXACT_HISTORICAL_ENTITY_REF')
    return next(iter(matches.values()))


def validate_bible(bible: CreativeBible, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    """Validate one department's ownership and pinned upstreams, never fill gaps."""
    bible = CreativeBible.model_validate(dump_contract(bible))
    definitions = registry(bible.source_type)
    if bible.created_by_capability not in definitions:
        raise ValueError('UNKNOWN_PROFESSIONAL_DEPARTMENT')
    definition = definitions[bible.created_by_capability]
    if bible.created_by_capability in {'runtime-visual-medium', 'global-visual-style', 'specialized-asset-design'} and bible.status != 'NOT_REQUIRED':
        raise ValueError('TYPED_VISUAL_CONTRACT_REQUIRED')
    if bible.type != definition.output_contract:
        raise ValueError('DEPARTMENT_OUTPUT_TYPE_MISMATCH')
    for ref in (*bible.source_refs, *bible.continuity_refs, *bible.approval_refs):
        _fresh(ref, current)
    _validate_approvals(bible, artifacts, current)
    upstream: dict[str, CreativeBible] = {}
    for ref in bible.depends_on:
        other = CreativeBible.model_validate(_read(ref, artifacts, current))
        if other.source_type != bible.source_type:
            raise ValueError('CROSS_SOURCE_DEPARTMENT_DEPENDENCY')
        if ref != bible_pin(other) or other.work_ref != bible.work_ref or (other.script_ref and bible.script_ref and other.script_ref != bible.script_ref) or (other.episode_ref and bible.episode_ref and other.episode_ref != bible.episode_ref):
            raise ValueError('DEPENDENCY_IDENTITY_OR_SCOPE_MISMATCH')
        if other.created_by_capability in upstream:
            raise ValueError('DUPLICATE_DEPARTMENT_DEPENDENCY')
        upstream[other.created_by_capability] = other
        if bible.status in ('READY_FOR_REVIEW', 'APPROVED') and other.status == 'DRAFT':
            raise ValueError('DEPARTMENT_DEPENDENCY_NOT_READY:' + other.created_by_capability)
    if set(upstream) != set(definition.depends_on):
        raise ValueError('DEPARTMENT_DEPENDENCY_SET_MISMATCH:' + bible.created_by_capability)
    if bible.source_type == 'LITERARY':
        _validate_literary_department(bible, artifacts, current)
    scopes = {bible.work_ref, *bible.scene_refs, *bible.shot_refs}
    scopes.update(x for x in (bible.script_ref, bible.episode_ref) if x)
    for record in bible.content:
        allowed_fields = (definition.authority_scope if bible.created_by_capability in FORWARDED_DEPARTMENTS
                          and record.provenance in {'MIGRATED_FROM_R1', 'SPECIALIZED_ASSET_PROJECTION'} else definition.can_create)
        if not set(record.values) <= set(allowed_fields):
            raise ValueError('DEPARTMENT_AUTHORITY_VIOLATION:' + ','.join(sorted(set(record.values) - set(definition.can_create))))
        if not set(record.scope_refs) <= scopes:
            raise ValueError('RECORD_SCOPE_OUTSIDE_BIBLE')
        for ref in record.source_refs:
            _fresh(ref, current)
        if record.provenance == 'SPECIALIZED_ASSET_PROJECTION':
            from drama_plugin.contracts.specialized_asset import SpecializedAssetBible
            from drama_plugin.specialized_asset import validate_assets, department_values
            source = [ref for ref in record.source_refs if ref.key == 'specialized-assets:' + bible.work_ref]
            if len(source) != 1 or bible.created_by_capability not in FORWARDED_DEPARTMENTS:
                raise ValueError('SPECIALIZED_ASSET_VIEW_SOURCE_REQUIRED')
            asset_bible = SpecializedAssetBible.model_validate(_read(source[0], artifacts, current))
            validate_assets(asset_bible, artifacts, current)
            if record.values != department_values(asset_bible, record.id, bible.created_by_capability, artifacts, current):
                raise ValueError('SPECIALIZED_ASSET_VIEW_CHANGED')
        keys = _nested_keys(record.values)
        if bible.created_by_capability not in ('video-model-selection', 'prompt-compiler') and keys & _PROVIDER_KEYS:
            raise ValueError('PROVIDER_CONTROLS_IN_CREATIVE_BIBLE')
        if bible.created_by_capability == 'environment-design' and keys & _FORBIDDEN_ENVIRONMENT_KEYS:
            raise ValueError('ENVIRONMENT_FUNCTION_CANNOT_OWN_OTHER_DEPARTMENTS')
        forbidden_nested = {'environment-art': {'topology', 'routes', 'entrances', 'exits', 'final_camera'},
            'character-art': {'personality', 'dialogue_text', 'character_arc', 'costume_design', 'voice_identity'},
            'lighting-design': {'architectural_language', 'material_palette', 'topology', 'costume_design'},
            'director': {'face_structure', 'armor_intent', 'ordered_actions', 'camera_height', 'provider_prompt', 'literary_analysis', 'rights_status', 'historical_research', 'philosophical_core', 'adaptation_contract', 'source_package', 'screenplay_input'},
            'video-model-selection': {'dialogue_text', 'character_arc', 'ordered_actions', 'face_structure'}}
        if keys & forbidden_nested.get(bible.created_by_capability, set()):
            raise ValueError('NESTED_DEPARTMENT_AUTHORITY_VIOLATION')
        if bible.created_by_capability == 'historical-entity-registry':
            entity_identity = EntityIdentity.model_validate(record.values)
            for evidence_ref in entity_identity.evidence_refs:
                _fresh(evidence_ref, current)
        if bible.created_by_capability == 'character-art' and 'historical_status' in record.values:
            entity = _inherited_entity(str(record.values.get('character_ref', '')), list(upstream.values()), artifacts, current)
            if record.values['historical_status'] != entity.historical_status:
                raise ValueError('CREATIVE_DEPARTMENT_CANNOT_UPGRADE_OR_RECLASSIFY_EVIDENCE')
        if bible.created_by_capability == 'character-dramaturgy' and 'historical_authority' in record.values:
            if not isinstance(record.values['historical_authority'], bool):
                raise ValueError('HISTORICAL_AUTHORITY_MUST_BE_EXPLICIT_BOOLEAN')
            entity = _inherited_entity(str(record.values.get('character_ref', '')), list(upstream.values()), artifacts, current)
            if record.values['historical_authority'] and entity.identity_kind != 'HISTORICAL_PERSON':
                raise ValueError('ORIGINAL_CHARACTER_CANNOT_CLAIM_HISTORICAL_AUTHORITY')
        if bible.created_by_capability == 'continuity-supervisor':
            state = ContinuityState.model_validate(record.values)
            _fresh(state.changed_by, current)
            if state.restoration_ref:
                _fresh(state.restoration_ref, current)
        if bible.created_by_capability == 'environment-art' and record.status == 'DECIDED':
            environment = record.values.get('environment_ref')
            candidates = [r for r in upstream['environment-design'].content if r.values.get('environment_ref') == environment and r.status == 'DECIDED']
            if not candidates or not any({'topology', 'zones'} <= set(r.values) for r in candidates):
                raise ValueError('ENVIRONMENT_ART_REQUIRES_DECIDED_TOPOLOGY')
        if bible.created_by_capability == 'action-choreography' and record.status == 'DECIDED':
            scene = record.values.get('scene_ref')
            candidates = [r for r in upstream['blocking'].content if r.values.get('scene_ref') == scene and r.status == 'DECIDED']
            if not candidates or not any({'actor_positions', 'actor_movements'} <= set(r.values) for r in candidates):
                raise ValueError('ACTION_REQUIRES_DECIDED_BLOCKING')
        if bible.created_by_capability == 'reference-strategy':
            images = record.values.get('reference_images', [])
            if not isinstance(images, list):
                raise ValueError('REFERENCE_IMAGES_MUST_BE_LIST')
        if bible.created_by_capability == 'clip-decomposition':
            validate_clip_plan(record.values)
        if definition.capability_type == 'VALIDATOR':
            if record.values.get('semantic_review_status') not in ('PASS', 'FAIL', 'NOT_OBSERVED', 'NOT_REQUIRED'):
                raise ValueError('QA_SEMANTIC_OBSERVATION_MUST_BE_EXPLICIT')
            if record.values.get('semantic_review_status') == 'PASS' and not record.values.get('evidence_refs'):
                raise ValueError('SEMANTIC_QA_REQUIRES_REVIEW_EVIDENCE')
    return {'department': definition.department_id, 'validationStatus': 'PASS',
            'status': bible.status, 'outputRef': dump_contract(bible_pin(bible)),
            'artisticApproval': 'APPROVED' if bible.status == 'APPROVED' else 'NOT_APPROVED',
            'providerCalls': 0}


def validate_clip_plan(values: Mapping[str, Any]) -> None:
    """A creative split is not proof a provider can generate it."""
    import math
    clips = values.get('clips', [])
    if not isinstance(clips, list):
        raise ValueError('CLIPS_MUST_BE_ORDERED_LIST')
    limit = values.get('provider_limit_seconds')
    if limit is None and values.get('feasibility') == 'VERIFIED':
        raise ValueError('UNKNOWN_PROVIDER_LIMIT_CANNOT_BE_VERIFIED')
    cursor = 0.0
    for clip in clips:
        if not isinstance(clip, dict) or not {'id', 'start_seconds', 'end_seconds'} <= set(clip):
            raise ValueError('CLIP_REQUIRES_ID_AND_RANGE')
        start, end = clip['start_seconds'], clip['end_seconds']
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not all(map(math.isfinite, (start, end))) or start != cursor or end <= start:
            raise ValueError('CLIP_RANGE_GAP_OVERLAP_OR_INVALID')
        if limit is not None and end - start > limit:
            raise ValueError('CLIP_EXCEEDS_VERIFIED_PROVIDER_LIMIT')
        cursor = end
    if clips and cursor != values.get('total_seconds'):
        raise ValueError('CLIPS_DO_NOT_PRESERVE_SHOT_DURATION')


def resolve_entity(entities: Sequence[EntityIdentity], entity_id: str) -> EntityIdentity:
    """Exact stable identity only. Names never cause an implicit historical merge."""
    matches = [e for e in entities if e.entity_id == entity_id]
    if len(matches) != 1:
        raise ValueError('ENTITY_ID_MISSING_OR_AMBIGUOUS')
    return matches[0]


def validate_continuity(bible: CreativeBible, scene_order: Sequence[str], artifacts: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    if bible.created_by_capability != 'continuity-supervisor':
        raise ValueError('EXPECTED_CONTINUITY_LEDGER')
    positions = {s: i for i, s in enumerate(scene_order)}
    seen: dict[str, ContinuityState] = {}
    heads: dict[tuple[str, str, str], str] = {}
    damaged: dict[tuple[str, str, str], bool] = {}
    domain_owners = {'character': 'character-dramaturgy', 'character_art': 'character-art', 'costume': 'costume-design', 'hair': 'look-continuity', 'makeup': 'look-continuity', 'injury': 'look-continuity', 'prop': 'prop-design', 'weapon': 'prop-design', 'animal': 'animal-design', 'environment': 'environment-design', 'set_dressing': 'set-decoration', 'spatial': 'blocking', 'lighting': 'lighting-design', 'color': 'color-design', 'time': 'scene-development', 'weather': 'environment-design', 'army_strength': 'battle-crowd-choreography', 'audio': 'sound-design'}
    for record in bible.content:
        state = ContinuityState.model_validate(record.values)
        if state.effective_from not in positions or state.scene_ref != state.effective_from:
            raise ValueError('CONTINUITY_SCENE_SCOPE_INVALID')
        if state.effective_until and (state.effective_until not in positions or positions[state.effective_until] < positions[state.effective_from]):
            raise ValueError('CONTINUITY_INTERVAL_INVALID')
        owner = CreativeBible.model_validate(_read(state.changed_by, artifacts, current))
        if owner.created_by_capability != domain_owners.get(state.domain) or owner.work_ref != bible.work_ref:
            raise ValueError('CONTINUITY_CHANGE_WRONG_OWNER')
        if state.owner_record_id or state.owner_state_path:
            selected = [r for r in owner.content if r.id == state.owner_record_id]
            if len(selected) != 1 or not state.owner_state_path:
                raise ValueError('CONTINUITY_OWNER_STATE_RECORD_MISSING')
            if state.scene_ref not in selected[0].scope_refs and bible.work_ref not in selected[0].scope_refs:
                raise ValueError('CONTINUITY_OWNER_STATE_SCOPE_MISMATCH')
            owned: Any = selected[0].values
            try:
                for part in state.owner_state_path:
                    owned = owned[int(part)] if isinstance(owned, list) else owned[part]
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise ValueError('CONTINUITY_OWNER_STATE_PATH_INVALID') from error
            if owned != state.state:
                raise ValueError('CONTINUITY_STATE_DIFFERS_FROM_OWNING_DEPARTMENT')
        key = (state.entity, state.domain, state.property)
        previous = heads.get(key)
        if state.predecessor != previous:
            raise ValueError('CONTINUITY_PREDECESSOR_MISMATCH')
        if previous and positions[seen[previous].effective_from] > positions[state.effective_from]:
            raise ValueError('CONTINUITY_STATE_TRAVELS_BACKWARDS')
        if state.restoration_ref and state.restoration_ref != state.changed_by:
            raise ValueError('RESTORATION_MUST_BE_EVIDENCED_BY_STATE_OWNER')
        # Restoring a persisted damaged/injured state must be explicit, not a
        # new unrelated scene snapshot which silently resets the entity.
        state_text = state.state if isinstance(state.state, str) else canonical_json(state.state)
        structured_repair = isinstance(state.state, dict) and (state.state.get('integrity') == 'INTACT' or state.state.get('fullyRepaired') is True or state.state.get('fully_repaired') is True or state.state.get('injury') in ('NONE', 'HEALED'))
        if damaged.get(key) and (structured_repair or re.fullmatch(r'intact|healthy|repaired|完好|痊愈|修复', state_text, re.I)) and not state.restored:
            raise ValueError('UNEXPLAINED_CONTINUITY_RESTORATION')
        if state.restored:
            damaged[key] = False
        elif re.search(r'broken|injured|wound|damaged|shallow_cut|existing_cut|破损|断裂|受伤', state_text, re.I):
            damaged[key] = True
        seen[record.id] = state
        heads[key] = record.id
    return {'status': 'PASS', 'stateCount': len(seen), 'domains': sorted({x.domain for x in seen.values()})}


def continuity_at(bible: CreativeBible, entity: str, domain: str, property: str, scene: str, scene_order: Sequence[str]) -> ContinuityState | None:
    """Scene-end view; latest authored event in that scene wins, not entry state."""
    positions = {s: i for i, s in enumerate(scene_order)}
    if scene not in positions:
        raise ValueError('UNKNOWN_CONTINUITY_SCENE')
    matches = [ContinuityState.model_validate(r.values) for r in bible.content]
    active = [s for s in matches if (s.entity, s.domain, s.property) == (entity, domain, property) and positions[s.effective_from] <= positions[scene] and (s.effective_until is None or positions[scene] <= positions[s.effective_until])]
    return max(enumerate(active), key=lambda pair: (positions[pair[1].effective_from], pair[0]))[1] if active else None


def validate_environment_preservation(bible: CreativeBible, locked: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Compare explicitly locked functional facts; do not guess visual semantics.

    Example locks are ENV-04 location_type=military_tent and ENV-08
    physical_constraints.boat_capacity=single_small_ferry. Free prose remains a
    separately evidenced semantic review, never silently treated as a test.
    """
    if bible.created_by_capability != 'environment-design':
        raise ValueError('EXPECTED_FUNCTIONAL_ENVIRONMENT_BIBLE')
    records: dict[str, list[dict[str, Any]]] = {}
    for record in bible.content:
        environment_ref = record.values.get('environment_ref')
        if isinstance(environment_ref, str) and record.status != 'NOT_REQUIRED':
            records.setdefault(environment_ref, []).append(record.values)
    for environment, fields in locked.items():
        if environment not in records:
            raise ValueError('LOCKED_ENVIRONMENT_MISSING')
        for key, expected in fields.items():
            # A reusable location, local weather delta and continuity event may
            # share identity. Only records actually supplying the locked field
            # participate; every supplier must agree, irrespective of order/id.
            providers = [values[key] for values in records[environment] if key in values]
            if key not in registry()['environment-design'].authority_scope or not providers or any(value != expected for value in providers):
                raise ValueError('LOCKED_ENVIRONMENT_CHANGED:' + environment + ':' + key)
    return {'status': 'PASS', 'lockedEnvironmentCount': len(locked)}


def decompose_clip_intervals(total_seconds: float, *, verified_max_seconds: float | None,
                             candidate_cut_points: Sequence[float], protected_intervals: Sequence[tuple[float, float]] = ()) -> dict[str, Any]:
    """Bounded planning using owner-approved cut points, never arbitrary cuts."""
    import math
    if not math.isfinite(total_seconds) or total_seconds <= 0:
        raise ValueError('INVALID_SHOT_DURATION')
    if verified_max_seconds is None:
        return {'status': 'BLOCKED_UNVERIFIED_PROVIDER_LIMIT', 'clips': [], 'providerCalls': 0}
    if not math.isfinite(verified_max_seconds) or verified_max_seconds <= 0:
        raise ValueError('INVALID_VERIFIED_PROVIDER_LIMIT')
    if any(not 0 <= start < end <= total_seconds for start, end in protected_intervals):
        raise ValueError('INVALID_PROTECTED_INTERVAL')
    if any(not math.isfinite(point) or not 0 < point < total_seconds for point in candidate_cut_points):
        raise ValueError('INVALID_EDITORIAL_CUT_POINT')
    allowed = sorted({0.0, total_seconds, *(p for p in candidate_cut_points if not any(a < p < b for a, b in protected_intervals))})
    cursor = 0.0
    clips: list[dict[str, Any]] = []
    while cursor < total_seconds:
        endpoints = [p for p in allowed if cursor < p <= cursor + verified_max_seconds]
        if not endpoints:
            return {'status': 'BLOCKED_INDIVISIBLE_ACTION_OR_DIALOGUE', 'clips': [], 'providerCalls': 0}
        end = max(endpoints)
        clips.append({'id': 'clip-' + str(len(clips) + 1), 'start_seconds': cursor, 'end_seconds': end})
        cursor = end
    return {'status': 'PLANNED_NOT_EXECUTABLE', 'clips': clips, 'providerCalls': 0}


def validate_package(package: DirectorPackage, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    package = DirectorPackage.model_validate(dump_contract(package))
    if set(package.bible_refs) != set(registry(package.source_type)):
        raise ValueError('DIRECTOR_PACKAGE_DEPARTMENT_SET_MISMATCH')
    for ref in (*package.source_refs, *package.approval_refs):
        _fresh(ref, current)
    _validate_approvals(package, artifacts, current)
    rows = []
    blockers: list[str] = []
    for department in dependency_order(package.source_type):
        ref = package.bible_refs[department]
        bible = CreativeBible.model_validate(_read(ref, artifacts, current))
        if bible.source_type != package.source_type:
            raise ValueError('CROSS_SOURCE_DIRECTOR_PACKAGE')
        if ref != bible_pin(bible) or bible.created_by_capability != department or bible.work_ref != package.work_ref:
            raise ValueError('DIRECTOR_PACKAGE_WRONG_OWNER_OR_WORK')
        if (package.script_ref is not None and bible.script_ref != package.script_ref) or (package.episode_ref is not None and bible.episode_ref != package.episode_ref):
            raise ValueError('DIRECTOR_PACKAGE_SCRIPT_OR_EPISODE_MISMATCH')
        rows.append(validate_bible(bible, artifacts, current))
        if bible.status == 'DRAFT':
            blockers.append('DEPARTMENT_DRAFT:' + department)
        if registry(package.source_type)[department].capability_type == 'VALIDATOR':
            for record in bible.content:
                if record.values.get('deterministic_status') in ('FAIL', 'BLOCKED') or record.values.get('semantic_review_status') == 'FAIL':
                    blockers.append('QA_FAILED:' + department + ':' + record.id)
        if package.status == 'APPROVED' and bible.status not in ('APPROVED', 'NOT_REQUIRED'):
            raise ValueError('APPROVED_PACKAGE_CONTAINS_UNAPPROVED_DEPARTMENT')
    scenes: list[str] = []
    shots: list[str] = []
    for ref in package.scene_assembly_refs:
        assembly = SceneAssembly.model_validate(_read(ref, artifacts, current))
        _validate_assembly(assembly, package, artifacts, current)
        scenes.append(assembly.scene_id)
    for ref in package.shot_assembly_refs:
        shot = ShotAssembly.model_validate(_read(ref, artifacts, current))
        _validate_assembly(shot, package, artifacts, current)
        if shot.scene_ref not in scenes:
            raise ValueError('SHOT_ASSEMBLY_MISSING_SCENE')
        shots.append(shot.shot_id)
    if not scenes or len(set(scenes)) != len(scenes) or len(set(shots)) != len(shots):
        raise ValueError('ASSEMBLY_SCOPE_MISSING_OR_DUPLICATE')
    continuity = CreativeBible.model_validate(_read(package.bible_refs['continuity-supervisor'], artifacts, current))
    continuity_result = validate_continuity(continuity, scenes, artifacts, current)
    return {'status': 'BLOCKED_PROFESSIONAL_REVIEW' if blockers else 'READY_FOR_PHASE_I_R2_USER_REVIEW', 'blockers': blockers, 'departments': rows, 'continuity': continuity_result,
            'sceneCount': len(scenes), 'shotCount': len(shots), 'productionAuthorized': False, 'providerCalls': 0}


def _validate_assembly(assembly: SceneAssembly | ShotAssembly, package: DirectorPackage, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> None:
    if assembly.work_ref != package.work_ref:
        raise ValueError('ASSEMBLY_WORK_MISMATCH')
    canonical = _read(assembly.source_ref, artifacts, current)
    expected_id = assembly.scene_id if isinstance(assembly, SceneAssembly) else assembly.shot_id
    if assembly.source_ref.kind != 'CANON' or not isinstance(canonical, dict) or canonical.get('id') != expected_id:
        raise ValueError('ASSEMBLY_CANONICAL_SOURCE_ID_MISMATCH')
    if isinstance(assembly, SceneAssembly) and package.episode_ref is not None and canonical.get('episodeId', canonical.get('episode_id')) != package.episode_ref:
        raise ValueError('ASSEMBLY_CANONICAL_EPISODE_MISMATCH')
    if isinstance(assembly, ShotAssembly) and canonical.get('sceneId', canonical.get('scene_id')) != assembly.scene_ref:
        raise ValueError('ASSEMBLY_CANONICAL_SCENE_MISMATCH')
    bindings = dict(assembly.department_refs)
    scope = assembly.scene_id if isinstance(assembly, SceneAssembly) else assembly.shot_id
    if isinstance(assembly, SceneAssembly):
        bindings.update({'scene-development': assembly.dramaturgy_ref, 'environment-design': assembly.environment_ref})
        if any(r != package.bible_refs['dialogue-design'] for r in assembly.dialogue_refs):
            raise ValueError('SCENE_DIALOGUE_OWNER_MISMATCH')
        for ref in assembly.character_state_refs:
            if ref != package.bible_refs['continuity-supervisor']:
                raise ValueError('SCENE_CHARACTER_STATE_OWNER_MISMATCH')
            bindings['continuity-supervisor'] = ref
    else:
        for ref in assembly.generation_clip_refs:
            if ref != package.bible_refs['clip-decomposition']:
                raise ValueError('SHOT_GENERATION_CLIP_OWNER_MISMATCH')
            bindings['clip-decomposition'] = ref
    for department, ref in bindings.items():
        if package.bible_refs.get(department) != ref:
            raise ValueError('ASSEMBLY_DEPARTMENT_OWNER_MISMATCH')
        bible = CreativeBible.model_validate(_read(ref, artifacts, current))
        if isinstance(assembly, SceneAssembly) and bible.scene_refs and scope not in bible.scene_refs:
            raise ValueError('ASSEMBLY_BIBLE_SCOPE_MISMATCH')
        if isinstance(assembly, ShotAssembly) and bible.shot_refs and scope not in bible.shot_refs:
            raise ValueError('ASSEMBLY_BIBLE_SCOPE_MISMATCH')


def compile_prompt_projection(package: DirectorPackage, shot: ShotAssembly, artifacts: Mapping[str, Any], current: Mapping[str, str], *, adapter: str) -> dict[str, Any]:
    """Pure projection of approved exact refs. No creative text or provider calls."""
    review = validate_package(package, artifacts, current)
    if review['blockers']:
        raise ValueError('CREATIVE_PACKAGE_QA_BLOCKED')
    if package.status != 'APPROVED':
        raise ValueError('CREATIVE_PACKAGE_NOT_APPROVED')
    if adapter not in ('seedance', 'comfy', 'generic'):
        raise ValueError('UNKNOWN_PROMPT_ADAPTER')
    if not any(ref.fingerprint == sha256_canonical(shot) and _read(ref, artifacts, current) == dump_contract(shot) for ref in package.shot_assembly_refs):
        raise ValueError('SHOT_NOT_PINNED_IN_APPROVED_DIRECTOR_PACKAGE')
    _validate_assembly(shot, package, artifacts, current)
    projected: dict[str, Any] = {}
    for department, ref in shot.department_refs.items():
        bible = CreativeBible.model_validate(_read(ref, artifacts, current))
        if bible.status != 'APPROVED':
            raise ValueError('DEPARTMENT_NOT_APPROVED_FOR_PROJECTION')
        selected = []
        for record in bible.content:
            explicit_shots = set(record.scope_refs) & set(bible.shot_refs)
            if (shot.shot_id in explicit_shots if explicit_shots else shot.scene_ref in record.scope_refs or bible.work_ref in record.scope_refs):
                selected.append(dump_contract(record))
        projected[department] = selected
    return {'adapter': adapter, 'shotId': shot.shot_id, 'sourceRefs': {k: dump_contract(v) for k, v in shot.department_refs.items()},
            'projection': projected, 'executable': False, 'providerCalls': 0,
            'status': 'CREATIVE_PROJECTION_ONLY_PROVIDER_ADAPTER_REQUIRED'}


def _validate_literary_department(bible: CreativeBible, artifacts: Mapping[str, Any], current: Mapping[str, str]) -> None:
    from drama_plugin.creative_source import verify_screenplay_input
    queue = [bible]
    seen: set[str] = set()
    roots: dict[str, Any] = {}
    while queue:
        node = queue.pop()
        if node.id in seen:
            continue
        seen.add(node.id)
        if node.source_type != 'LITERARY':
            raise ValueError('CROSS_SOURCE_DEPARTMENT_DEPENDENCY')
        if node.created_by_capability == 'literary-source-input':
            if len(node.content) != 1 or node.content[0].status != 'DECIDED':
                raise ValueError('LITERARY_ROOT_REQUIRES_ONE_COMPILED_INPUT')
            record = node.content[0]
            compiled = verify_screenplay_input(record.values['source_package'], record.values['screenplay_input'])
            if compiled.source_type != 'LITERARY' or compiled.package_ref not in node.source_refs:
                raise ValueError('LITERARY_ROOT_SOURCE_PIN_MISMATCH')
            _fresh(compiled.package_ref, current)
            roots[compiled.package_ref.fingerprint] = compiled
        queue.extend(CreativeBible.model_validate(_read(r, artifacts, current)) for r in node.depends_on)
    if len(roots) != 1:
        raise ValueError('ONE_RECONCILED_LITERARY_ROOT_REQUIRED')
    compiled = next(iter(roots.values()))
    if bible.created_by_capability in ('character-dramaturgy', 'character-art'):
        states = compiled.resolved_input['characterArc']['states']
        for record in bible.content:
            char = record.values.get('character_ref')
            if char and char not in {s['characterId'] for s in states}:
                raise ValueError('CHARACTER_OUTSIDE_LITERARY_SOURCE')
            if bible.created_by_capability == 'character-art' and record.status == 'DECIDED':
                boundaries = [{'arcStage': state['arcStage'], 'visualContinuityBoundary': state['visualContinuityBoundary']} for state in states if state['characterId'] == char]
                if not boundaries or record.values.get('arc_continuity_boundaries') != boundaries:
                    raise ValueError('CHARACTER_ART_MUST_CONSUME_ARC_BOUNDARIES')
            for field in ('source_identity', 'source_authority'):
                if field in record.values:
                    unit = next((u for u in compiled.resolved_input['analysis']['units'] if u['id'] == char), None)
                    if unit is None or record.values[field] != {'sourceUnitId': char, 'origin': unit['origin']}:
                        raise ValueError('LITERARY_IDENTITY_CANNOT_RECLASSIFY_SOURCE')
            if 'character_arc' in record.values and record.values['character_arc'] != [s for s in states if s['characterId'] == char]:
                raise ValueError('CHARACTER_ARC_REQUIRES_UPSTREAM_REVISION')
