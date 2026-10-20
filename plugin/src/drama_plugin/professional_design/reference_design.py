"""Deterministic asset-original inheritance for Target reference artwork.

The artist supplies remaining view/state, not replacement asset art. Reuses
existing design leaves and VisualPromptIR; no second prompt or art schema.
"""
import re
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
COMPOSITION_SOURCE = 'reference-artwork/composition'


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


def _screen_edges(text: str) -> list[tuple[str, str]]:
    """Only explicit same-object frame edges, never room/world left-right.

    These bounded assertions can prove a conflict; absence cannot establish
    semantic compatibility of arbitrary prose. The reference author owns that.
    """
    edges = []
    for match in re.finditer(
        r'([^，。；：;:,.!?！？\n]{1,40}?)(?:留在|位于|置于|在)画面([左右])(?:侧边缘|边缘|缘)', text):
        subject = match[1].strip()
        if not re.search(r'不|勿|未|无|别|禁止|避免|并非|如果|若|或者|或是', subject):
            edges.append((subject, match[2]))
    for match in re.finditer(
        r'(?i)\b([a-z][a-z -]{0,39}?)\s+(?:at|on)\s+(?:the\s+)?'
        r'(left|right)\s+(?:edge\s+of\s+(?:the\s+)?frame|frame\s+edge)\b', text):
        subject = re.sub(r'^(?:the|a|an)\s+', '', match[1].lower())
        if not re.search(r'\b(?:no|not|never|without|avoid|unless|if|either|or)\b', subject):
            edges.append((subject, '左' if match[2].lower() == 'left' else '右'))
    return edges


def _check_view_conflicts(views: dict[str, str]) -> None:
    # Reuse the existing author-completion path for a directly evidenced
    # contradiction. This is not a general prose parser or a new Runtime gate.
    rows = [(path, subject, side) for path, text in views.items()
            for subject, side in _screen_edges(text)]
    for i, (path, subject, side) in enumerate(rows):
        for other_path, other, other_side in rows[i + 1:]:
            if subject == other and side != other_side:
                raise DesignCompletionRequired('REFERENCE_VIEW_CONFLICT:' + path + ':' + other_path)


def inherit_design(frame: FrameSpec, item: dict[str, Any]) -> FrameSpec:
    """Inherit asset facts without replacing the reference artist's view."""
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
    composition = frame.composition
    old_framing = ir['camera']['framing']
    known_proofs = [(SOURCE_PREFIX + item['designRef']['fingerprint'] + '/proof',
                     item['design'].get('proof'))]
    if item.get('inheritedDesignRef') and item.get('inheritedDesign'):
        known_proofs.append((SOURCE_PREFIX + item['inheritedDesignRef']['fingerprint'] + '/proof',
                             item['inheritedDesign'].get('proof')))
    generated_framing = (old_framing['source'], old_framing['text']) in known_proofs
    if generated_framing and 'proof' in leaves:
        # A prior deterministic proof is not a new author's viewing choice.
        # Refresh only this system-owned fact, preserving sealed old requests.
        if composition == old_framing['text']:
            composition = leaves['proof']
        ir['camera']['framing'] = fact('proof')
    # Review the authored boundaries before any line-break serialization;
    # otherwise a line-start sound/control label could disappear as a boundary.
    from drama_plugin.visual.payload_scope import review_text
    review_text(composition, 'IMAGE')
    _check_view_conflicts({'composition': composition, 'camera.framing': ir['camera']['framing']['text'],
                          **({'selected.proof': leaves['proof']} if 'proof' in leaves else {})})
    # Rebuild asset-owned facts, not the artist's distinct current relationships.
    # Their source locators already passed the Fact contract; this handoff does
    # not infer authority or resolve semantic conflicts from descriptive prose.
    texts = set(leaves.values())
    authored_preserve = [f for f in ir['preserve']
        if f['scope'] == 'CURRENT' and f['priority'] == 'CRITICAL'
        and not f['source'].startswith(SOURCE_PREFIX)
        and f['source'] != COMPOSITION_SOURCE and f['text'] not in texts]
    ir['preserve'] = []
    for key in leaves:
        if key in SUBJECT:
            ir['subjects'][0][SUBJECT[key]] = fact(key)
        elif key in ENVIRONMENT:
            ir['environment'][ENVIRONMENT[key]] = fact(key)
        elif key == 'proof':
            # Preserve the selected proof exactly once, alongside the artist's
            # more specific current view rather than overwriting that view.
            if ir['camera']['framing'] != fact(key):
                ir['preserve'].append(fact(key))
        elif key.startswith('referenceLighting.'):
            ir['lighting'][key.split('.')[1]] = fact(key)
        else:
            ir['preserve'].append(fact(key))
    for authored in authored_preserve:
        if authored not in ir['preserve']:
            ir['preserve'].append(authored)
    if ir['edit_delta'] and not ir['preserve']:
        preservation = (
            'Preserve selected identity, costume, materials and physical layout according to each reference duty.'
            if ir['task']['task_type'] == 'REFERENCE_EDIT'
            else 'Preserve the supplied image outside the explicit edit regions.')
        ir['preserve'] = [dict(text=preservation,
            priority='CRITICAL', scope='CURRENT', source='reference-proof-preservation')]
    # FrameSpec permits wrapped prose; Fact uses a single line. Preserve the
    # authored Frame verbatim and only serialize its line breaks as spaces.
    composition_text = ' '.join(composition.splitlines())
    if composition_text not in texts and composition_text != ir['camera']['framing']['text']:
        # Top-level composition is authored observable artwork, not a second
        # camera design. Carry it unchanged through the existing executable IR
        # so an attention relation is not reduced to mere object readability.
        ir['preserve'].append(dict(text=composition_text, priority='CRITICAL', scope='CURRENT',
                                   source=COMPOSITION_SOURCE))
    for group in ('secondary_details', 'continuity'):
        ir[group] = [f for f in ir[group] if f['text'] not in texts]
    data = frame.model_dump(mode='json', exclude={'prompt_ir'})
    if item['assetType'] == 'CHARACTER':
        data['actors'][0]['identity'] = ir['subjects'][0]['face']['text']
        data['actors'][0]['costume'] = ir['subjects'][0]['costume']['text']
    data['composition'] = composition
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
