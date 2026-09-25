"""Resolve originals, validate authority, compile decisions. Never author missing input."""
from typing import Any, Mapping
from .contracts.base import dump_contract, sha256_canonical
from .contracts.source_pin import SourcePin
from .contracts.professional import CreativeBible
from .contracts.specialized_asset import (MovieVisualMedium, GlobalVisualStyle,
    SpecializedAssetBible, DramaturgyInput, CharacterAsset, CostumeAsset, SceneAsset)
from .contracts.visual_medium import VisualMediumIntent
from .contracts.character_prompt import CharacterPromptFact, StructuredCharacterFacts, FactDomain
from .visual_medium import compile_character_art, compile_visual_medium, DECLARATION, LIVE, CG

FORWARDED_DEPARTMENTS = frozenset({'character-art', 'costume-design',
    'environment-design', 'environment-art', 'set-decoration'})

# Old downstream contracts keep stable field names; there is only one author.
VIEW_FIELDS = {
    'character-art': ('CHARACTER', {'face': 'face_structure', 'body': 'body_mass',
        'age_presentation': 'apparent_age', 'hair': 'hair', 'facial_hair': 'facial_hair',
        'physical_identity': 'visual_archetype', 'body_proportion': 'body_proportion',
        'surface_state': 'skin', 'visible_life_history': 'dominant_visual_traits',
        'occupational_physical_traits': 'secondary_traits', 'visual_continuity': 'continuity_anchors'}),
    'costume-design': ('COSTUME', {'garment_structure': 'garment_construction_intent',
        'layering': 'layering', 'material': 'materials', 'wear': 'wear',
        'maintenance_state': 'stage_variants', 'social_class_expression': 'rank_distinction',
        'occupation_expression': 'costume_identity', 'continuity': 'continuity'}),
    'environment-design': ('SCENE', {'architecture': 'location_identity',
        'spatial_hierarchy': 'zones', 'interior_structure': 'topology',
        'social_function': 'location_type', 'environment_continuity': 'spatial_continuity'}),
    'environment-art': ('SCENE', {'architecture': 'architectural_language',
        'surface_material': 'material_palette', 'wear': 'wear', 
        'period_visible_details': 'historical_visual_basis', 'environment_continuity': 'visual_continuity_anchors'}),
    'set-decoration': ('SCENE', {'furniture': 'daily_use_objects', 'lived_in_state': 'lived_in_state',
        'wear': 'living_traces', 'environment_continuity': 'continuity'}),
}


def department_values(bible: SpecializedAssetBible, asset_id: str, department: str,
                      originals: Mapping[str, Any] | None = None, current: Mapping[str, str] | None = None) -> dict[str, Any]:
    kind, fields = VIEW_FIELDS[department]
    asset = next((a for a in bible.assets if a.id == asset_id and a.kind == kind), None)
    if asset is None:
        raise ValueError('SPECIALIZED_ASSET_VIEW_KIND_MISMATCH')
    values: dict[str, Any] = {fields[key]: decision.text for key, decision in asset.decisions.items() if key in fields}
    if not values:
        raise ValueError('UPSTREAM_INFORMATION_REQUIRED: asset lacks fields for this view')
    values['environment_ref' if isinstance(asset, SceneAsset) else 'character_ref'] = (
        asset.scene_id if isinstance(asset, SceneAsset) else asset.character_id)
    if department == 'environment-art' and originals is not None and current is not None:
        world = resolve(asset.world.bible_ref, originals, current)
        if world.get('sourceType') == 'LITERARY' and 'historical_visual_basis' in values:
            values['source_visual_basis'] = values.pop('historical_visual_basis')
    if department == 'character-art' and originals is not None and current is not None:
        original = resolve(asset.dramaturgy.bible_ref, originals, current)
        if original.get('sourceType') == 'LITERARY':
            narrative = upstream(asset.dramaturgy, {'character-dramaturgy'}, bible.work_id, originals, current)
            states = narrative.get('character_arc')
            if not isinstance(states, list) or not states:
                raise ValueError('UPSTREAM_INFORMATION_REQUIRED: literary character arc')
            values['arc_continuity_boundaries'] = [
                {'arcStage': state['arcStage'], 'visualContinuityBoundary': state['visualContinuityBoundary']}
                for state in states if state['characterId'] == values['character_ref']]
    return values


def resolve(ref: SourcePin, originals: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    value = originals.get(ref.key)
    if value is None or sha256_canonical(value) != ref.fingerprint or current.get(ref.key) != ref.fingerprint:
        raise ValueError('UPSTREAM_INFORMATION_REQUIRED: missing, stale or changed original ' + ref.key)
    return dict(value)


def upstream(link: DramaturgyInput, owners: set[str], work_id: str,
             originals: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    bible = CreativeBible.model_validate(resolve(link.bible_ref, originals, current))
    if bible.work_ref != work_id or bible.created_by_capability not in owners or bible.status != 'APPROVED':
        raise ValueError('UPSTREAM_INFORMATION_REQUIRED: approved scoped authority required')
    from .professional import validate_bible
    validate_bible(bible, originals, current)
    rows = [row for row in bible.content if row.id == link.record_id and row.status == 'DECIDED']
    if len(rows) != 1 or any(field not in rows[0].values or not rows[0].values[field] for field in link.constraint_fields):
        raise ValueError('UPSTREAM_INFORMATION_REQUIRED: original constraint fields required')
    return rows[0].values


def validate_assets(bible: SpecializedAssetBible, originals: Mapping[str, Any],
                    current: Mapping[str, str]) -> tuple[MovieVisualMedium, GlobalVisualStyle]:
    # Revalidate even model_copy / mutable model objects at every public boundary.
    bible = SpecializedAssetBible.model_validate(dump_contract(bible))
    source_types = {CreativeBible.model_validate(resolve(link.bible_ref, originals, current)).source_type
        for asset in bible.assets for link in (asset.dramaturgy, asset.director, asset.world)}
    if len(source_types) != 1:
        raise ValueError('CROSS_SOURCE_SPECIALIZED_ASSET_INPUT')
    if bible.approval_ref is not None:
        review = resolve(bible.approval_ref, originals, current)
        subject = dump_contract(bible, exclude={'approval_ref'})
        if (review.get('kind') != 'SPECIALIZED_ASSET_REVIEW' or review.get('decision') != 'APPROVE'
                or review.get('workId') != bible.work_id or not review.get('reviewer')
                or review.get('subjectFingerprint') != sha256_canonical(subject)
                or set(review.get('checkedBoundaries', ())) != {'DRAMATURGY', 'DIRECTOR_INTENT', 'SOURCE_WORLD', 'GLOBAL_STYLE'}):
            raise ValueError('SPECIALIZED_ASSET_APPROVAL_NOT_BOUND_TO_DESIGN')
    medium = MovieVisualMedium.model_validate(resolve(bible.runtime_ref, originals, current))
    style = GlobalVisualStyle.model_validate(resolve(bible.style_ref, originals, current))
    if medium.work_id != bible.work_id or style.work_id != bible.work_id or style.runtime_ref != bible.runtime_ref:
        raise ValueError('MOVIE_VISUAL_AUTHORITY_MISMATCH')
    if (medium.medium == 'CG') != (style.render_stylization is not None):
        raise ValueError('RENDER_STYLIZATION_MEDIUM_MISMATCH')
    if medium.medium == 'LIVE_ACTION' and style.realism != 'NATURALISTIC':
        raise ValueError('LIVE_ACTION_REQUIRES_NATURALISTIC_BOUNDARY')
    if style.imaging_character is not None:
        from .visual.still_knowledge import validate_imaging
        validate_imaging(style, originals, current)
    for asset in bible.assets:
        upstream(asset.director, {'director'}, bible.work_id, originals, current)
        upstream(asset.world, {'adaptation-boundary', 'historical-research', 'literary-source-input'},
                 bible.work_id, originals, current)
        owners = {'scene-development', 'story-architecture'} if isinstance(asset, SceneAsset) else {'character-dramaturgy'}
        values = upstream(asset.dramaturgy, owners, bible.work_id, originals, current)
        if isinstance(asset, (CharacterAsset, CostumeAsset)):
            if values.get('character_ref') != asset.character_id or values.get('arc_stage') != asset.arc_stage:
                raise ValueError('CHARACTER_DRAMATURGY_STAGE_MISMATCH')
            if not {'behavior_pattern', 'social_position'} <= set(asset.dramaturgy.constraint_fields):
                raise ValueError('UPSTREAM_INFORMATION_REQUIRED: behavioral and social constraints')
        elif values.get('scene_ref') != asset.scene_id:
            raise ValueError('SCENE_DRAMATURGY_SCOPE_MISMATCH')
        permitted = (asset.director.bible_ref, asset.dramaturgy.bible_ref, asset.world.bible_ref)
        for decision in asset.decisions.values():
            if asset.dramaturgy.bible_ref not in decision.source_refs or any(ref not in permitted for ref in decision.source_refs):
                raise ValueError('ASSET_DECISION_REQUIRES_OWN_DRAMATURGY_SOURCE')
            # Source fields are medium-neutral. Compiler alone adds rendering semantics.
            if any(pattern.search(decision.text) for pattern in (DECLARATION, LIVE, CG)):
                raise ValueError('ASSET_CANNOT_OVERRIDE_RUNTIME_MEDIUM')
    return medium, style


def compile_asset(bible: SpecializedAssetBible, asset_id: str, originals: Mapping[str, Any],
                  current: Mapping[str, str], *, casting_mode: str = 'DESIGN_NEUTRAL') -> dict[str, Any]:
    medium, style = validate_assets(bible, originals, current)
    asset = next((a for a in bible.assets if a.id == asset_id), None)
    if asset is None:
        raise ValueError('UNKNOWN_SPECIALIZED_ASSET')
    intent = VisualMediumIntent.model_validate({
        'visualMedium': 'CINEMATIC_CG' if medium.medium == 'CG' else 'LIVE_ACTION_PHOTOREAL',
        'characterTreatment': 'NATURAL', 'realismLevel': style.realism, 'castingMode': casting_mode,
        **({'renderStylization': style.render_stylization,
            'renderStylizationSource': bible.style_ref.key, 'presentationMode': 'LOOKDEV_NEUTRAL'} if medium.medium == 'CG' else {})})
    bible_ref = SourcePin(key='specialized-assets:' + bible.work_id, kind='DIRECTION', fingerprint=sha256_canonical(bible))
    facts = []
    source_map: list[dict[str, Any]] = []
    for field, decision in asset.decisions.items():
        domain: FactDomain = ('groom' if field in {'hair', 'facial_hair'} else
                  'skin' if field == 'surface_state' else 'form')
        facts.append(CharacterPromptFact(id=asset.id + '.' + field, domain=domain,
            text=decision.text, sources=(bible_ref.key + '#' + asset.id + '.' + field,)))
        source_map.append({'layer': 'ASSET_DESIGN', 'ref': dump_contract(bible_ref),
            'assetId': asset.id, 'field': field, 'text': decision.text, 'reason': decision.reason,
            'upstream': [dump_contract(ref) for ref in decision.source_refs]})
    if isinstance(asset, CharacterAsset):
        compiled = compile_character_art(intent, StructuredCharacterFacts(facts=tuple(facts)))
        prompt = compiled['prompt']
    else:
        # Scene/costume are not human characters: consume only the shared material policy.
        compiled = {}
        prompt = '\n'.join([compile_visual_medium(intent)['materials'], *(d.text for d in asset.decisions.values())])
    global_text = ('Material behavior remains physically credible. ' +
        ('Light follows motivated sources. ' if style.lighting_philosophy == 'MOTIVATED' else 'Light serves the approved expressive intent. ') +
        'Preserve authored identity and cross-asset visual consistency.')
    director_values = upstream(asset.director, {'director'}, bible.work_id, originals, current)
    director_text = '\n'.join(str(director_values[field]) for field in asset.director.constraint_fields)
    if any(pattern.search(director_text) for pattern in (DECLARATION, LIVE, CG)):
        raise ValueError('DIRECTOR_CANNOT_OVERRIDE_RUNTIME_MEDIUM')
    prompt += '\n' + global_text + '\nDirector constraints: ' + director_text
    for layer, ref, fields in (
        ('RUNTIME_MEDIUM', bible.runtime_ref, ['medium', 'configurationSource']),
        ('GLOBAL_STYLE', bible.style_ref, ['realism', 'renderStylization', 'materialPhilosophy', 'lightingPhilosophy', 'readability', 'consistency']),
        ('DRAMATURGY', asset.dramaturgy.bible_ref, list(asset.dramaturgy.constraint_fields)),
        ('DIRECTOR_INTENT', asset.director.bible_ref, list(asset.director.constraint_fields)),
        ('SOURCE_WORLD', asset.world.bible_ref, list(asset.world.constraint_fields)),
    ):
        if layer == 'GLOBAL_STYLE' and style.imaging_character is not None:
            fields = [*fields, 'imagingCharacter']
        source_map.append({'layer': layer, 'ref': dump_contract(ref), 'fields': fields})
    return {'schemaVersion': 'specialized-asset-compilation-v1', 'workId': bible.work_id,
        'assetId': asset_id, 'medium': medium.medium, 'castingMode': casting_mode,
        'prompt': prompt, 'promptFingerprint': sha256_canonical(prompt), 'sourceMap': source_map,
        'assetBible': dump_contract(bible), 'legacyMediumCompilation': compiled,
        'creativeAuthority': 'specialized-asset-design', 'productionAuthorized': False}


def provider_projection(receipt: dict[str, Any], originals: Mapping[str, Any], current: Mapping[str, str]) -> dict[str, Any]:
    """No provider default, enhancer or style appendix. Replay before projecting."""
    expected = compile_asset(SpecializedAssetBible.model_validate(receipt['assetBible']),
        receipt['assetId'], originals, current, casting_mode=receipt['castingMode'])
    if receipt != expected:
        raise ValueError('SPECIALIZED_ASSET_COMPILATION_CHANGED')
    style = GlobalVisualStyle.model_validate(resolve(SpecializedAssetBible.model_validate(receipt['assetBible']).style_ref, originals, current))
    if style.imaging_character is not None:
        raise ValueError('IMAGING_CHARACTER_REQUIRES_STILL_PROFESSIONAL_CONSUMER')
    from .visual.payload_scope import asset_payload
    scoped = asset_payload(receipt)
    return {'prompt': scoped['prompt'], 'promptFingerprint': sha256_canonical(scoped['prompt']),
        'scope_review': scoped['scope_review'],
        'medium': receipt['medium'], 'promptEnhancement': 'DISABLED',
        'compilationFingerprint': sha256_canonical(receipt), 'productionAuthorized': False}
