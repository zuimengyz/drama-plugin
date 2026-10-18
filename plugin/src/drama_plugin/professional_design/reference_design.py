"""Deterministic asset-original inheritance for Target reference artwork.

The artist supplies remaining view/state, not replacement asset art. Reuses
existing design leaves and VisualPromptIR; no second prompt or art schema.
"""
from typing import Any
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.visual_prompt import VisualPromptIR, Lighting
from drama_plugin.visual.frame_request import FrameSpec

SUBJECT = {'roleLabel': 'role', 'apparentAge': 'apparent_age',
           'identity': 'face', 'face': 'face', 'hair': 'hair',
           'body': 'body_proportions', 'costume': 'costume'}
ENVIRONMENT = {'architecture': 'architecture', 'topology': 'topology',
               'workArea': 'required_period_objects', 'construction': 'required_period_objects'}
SURFACES = {'material', 'materials', 'scale', 'geometry'}
INTERNAL = {'sourceBoundary', 'characterPackage', 'rationale', 'reason'}
SOURCE_PREFIX = 'asset-design/'


class DesignCompletionRequired(ValueError):
    """Recoverable author work; the Host completes the original and resumes."""


def design_leaves(design: dict[str, Any]) -> dict[str, str]:
    """Never silently discard an unknown author field or stringify a package."""
    result = {}
    for key, value in design.items():
        if key in INTERNAL:
            continue
        if key == 'referenceLighting':
            if not isinstance(value, dict) or set(value) != set(Lighting.model_fields):
                raise DesignCompletionRequired('REFERENCE_DESIGN_LIGHTING_FIELDS_REQUIRED')
            for leaf, text in value.items():
                result[key + '.' + leaf] = text
        elif key in SUBJECT or key in ENVIRONMENT or key in SURFACES or key == 'proof':
            result[key] = value
        else:
            raise DesignCompletionRequired('REFERENCE_DESIGN_UNMAPPED_FIELD:' + key)
    if not result:
        raise DesignCompletionRequired('REFERENCE_DESIGN_VISIBLE_FACTS_REQUIRED')
    for key, value in result.items():
        if not isinstance(value, str) or not value.strip() or '\n' in value:
            raise DesignCompletionRequired('REFERENCE_DESIGN_OBSERVABLE_TEXT_REQUIRED:' + key)
    for a, b in (('face', 'identity'), ('construction', 'workArea'), ('material', 'materials')):
        if a in result and b in result:
            raise DesignCompletionRequired('REFERENCE_DESIGN_AMBIGUOUS_FIELDS:' + a + ':' + b)
    return result


def selected_leaves(item: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    leaves = design_leaves(item['design'])
    origins = {key: item['designRef']['fingerprint'] for key in leaves}
    if item.get('inheritedDesign'):
        if not item.get('inheritedDesignRef'):
            raise ValueError('INHERITED_ASSET_DESIGN_REFERENCE_REQUIRED')
        parent = design_leaves(item['inheritedDesign'])
        # Alternative spellings have one authority, even across a variation.
        for a, b in (('face', 'identity'), ('construction', 'workArea'), ('material', 'materials')):
            if a in leaves or b in leaves:
                parent.pop(a, None); parent.pop(b, None)
        # A prior proof's temporary view/light is not the variation's intent.
        parent = {k: v for k, v in parent.items()
                  if k != 'proof' and not k.startswith('referenceLighting.')}
        for key, value in parent.items():
            if key not in leaves:
                leaves[key] = value
                origins[key] = item['inheritedDesignRef']['fingerprint']
    return leaves, origins


def inherit_design(frame: FrameSpec, item: dict[str, Any]) -> FrameSpec:
    """Replace author rewordings with exact selected leaves, then reseal IR."""
    if frame.prompt_ir is None:
        raise ValueError('REFERENCE_FRAME_REQUIRES_EXISTING_PROMPT_IR')
    leaves, origins = selected_leaves(item)
    ir = VisualPromptIR.model_validate(frame.prompt_ir).model_dump(mode='json')
    subject = item.get('subjectId')
    if item['assetType'] == 'CHARACTER':
        if (len(ir['subjects']) != 1 or len(frame.actors) != 1
                or ir['subjects'][0]['id'] != subject or frame.actors[0].entity_key != subject):
            raise ValueError('REFERENCE_SINGLE_SELECTED_IDENTITY_REQUIRED')
    elif any(key in SUBJECT for key in leaves):
        raise DesignCompletionRequired('REFERENCE_DESIGN_SUBJECT_FIELDS_ON_NON_CHARACTER')
    def fact(key: str) -> dict[str, str]:
        return dict(text=leaves[key], priority='CRITICAL', scope='CURRENT',
                    source=SOURCE_PREFIX + origins[key] + '/' + key)
    # Rebuild asset-owned facts, not the artist's distinct current relationships.
    # Their source locators already passed the Fact contract; this handoff does
    # not infer authority or resolve semantic conflicts from descriptive prose.
    texts = set(leaves.values())
    authored_preserve = [f for f in ir['preserve']
        if f['scope'] == 'CURRENT' and f['priority'] == 'CRITICAL'
        and not f['source'].startswith(SOURCE_PREFIX) and f['text'] not in texts]
    ir['preserve'] = []
    for key in leaves:
        if key in SUBJECT:
            ir['subjects'][0][SUBJECT[key]] = fact(key)
        elif key in ENVIRONMENT:
            ir['environment'][ENVIRONMENT[key]] = fact(key)
        elif key == 'proof':
            ir['camera']['framing'] = fact(key)
        elif key.startswith('referenceLighting.'):
            ir['lighting'][key.split('.')[1]] = fact(key)
        else:
            ir['preserve'].append(fact(key))
    for authored in authored_preserve:
        if authored not in ir['preserve']:
            ir['preserve'].append(authored)
    for group in ('secondary_details', 'continuity'):
        ir[group] = [f for f in ir[group] if f['text'] not in texts]
    if ir['edit_delta'] and not ir['preserve']:
        ir['preserve'] = [dict(text='Preserve the supplied image outside the explicit edit regions.',
            priority='CRITICAL', scope='CURRENT', source='reference-proof-preservation')]
    data = frame.model_dump(mode='json', exclude={'prompt_ir'})
    if item['assetType'] == 'CHARACTER':
        data['actors'][0]['identity'] = ir['subjects'][0]['face']['text']
        data['actors'][0]['costume'] = ir['subjects'][0]['costume']['text']
    if 'proof' in leaves:
        data['composition'] = leaves['proof']
    spec = FrameSpec.model_validate(data)
    ir['source_fingerprint'] = sha256_canonical(spec.model_dump(mode='json', exclude={'prompt_ir'}))
    return spec.model_copy(update={'prompt_ir': VisualPromptIR.model_validate(ir).model_dump(mode='json')})


def verify_design_delivery(compiled: dict[str, Any], item: dict[str, Any]) -> None:
    """Check actual retained projection and final wire before a new dispatch."""
    record = compiled['prompt_ir_compilation']
    prompt = compiled['request']['body']['prompt']
    leaves, origins = selected_leaves(item)
    for key, text in leaves.items():
        source = SOURCE_PREFIX + origins[key] + '/' + key
        rows = [r for r in record['retained'] if r['source'] == source]
        if len(rows) != 1 or rows[0]['text'] != text or text not in prompt:
            raise DesignCompletionRequired('REFERENCE_DESIGN_NOT_DELIVERED:' + key)
