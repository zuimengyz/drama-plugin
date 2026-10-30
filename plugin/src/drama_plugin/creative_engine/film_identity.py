"""Selected readable world/look originals on the existing screenplay handoff.

No discovery index, defaults, production adoption or Runtime state. Scene state
is prose, including deliberate aesthetic exceptions, not a second Scene model.
"""
from copy import deepcopy
from typing import Any

from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.source_pin import SourcePin

SCHEMA = 'selected-film-identity-v1'


def selection_changes(before, after):
    """Host-readable receipt only; never author context or production authority."""
    def pins(packet):
        selected = (packet or {}).get('filmIdentity', {})
        rows = {name: row['ref'] for name, row in selected.get('originals', {}).items()}
        rows.update({'scene:' + sid: row['ref'] for sid, row in selected.get('scenes', {}).items()})
        return rows

    old, new = pins(before), pins(after)
    return {'mode': 'COMPLETE_SNAPSHOT', 'formalAdoption': False, 'references': {
        name: {'change': ('RETAINED' if old.get(name) == new.get(name) else
                          'ADDED' if name not in old else 'REMOVED' if name not in new else 'REPLACED'),
               'before': old.get(name), 'after': new.get(name)}
        for name in sorted(old.keys() | new.keys())}}

AUTHOR_GUIDANCE = """
Read selected filmIdentity world, look, sourceAnalysis and current scene prose when supplied,
alongside any selected structured filmLook. Preserve their exact selection, unknowns and
distinction between source fact, historical inference and adaptation choice. Publication
date is not story date. Distinguish era, season/story date, time of day, elapsed time and
changing practical/natural light. A scene's authored exception changes the applicable
look, not the historical facts or the baseline for other scenes. Stylization need not be
naturalistic. Realize this scene's place, camera/actor/source positions, material/color
relations and sound/time in existing Shot intentions and department execution facts;
do not send the entire world/look prose or Knowledge to generation prompts.
"""


def bind_identity(workshop, *, work_id: str, scene_id: str | None,
                  world_ref: SourcePin | None, look_ref: SourcePin | None,
                  analysis_ref: SourcePin | None, scene_state_refs: dict[str, SourcePin] | None,
                  reason: str) -> dict[str, Any]:
    """Replace one complete selection; never merge historical look versions."""
    if not reason.strip():
        raise ValueError('World/look selection requires a Host reason')
    if scene_id is not None and set(scene_state_refs or {}) - {scene_id}:
        raise ValueError('Scene state selection scope mismatch')

    def original(ref):
        from drama_plugin.creative_engine.screenplay import ContextOriginal
        body = workshop._read(ref, 'screenplay-context-v1')
        ContextOriginal.model_validate({k: v for k, v in body.items() if k != 'schemaVersion'})
        if body['workId'] != work_id:
            raise ValueError('Film identity original work mismatch')
        return {'ref': dump_contract(ref), 'original': body}

    body = {'schemaVersion': SCHEMA, 'workId': work_id, 'sceneId': scene_id,
            'selectedBy': 'HOST', 'selectionReason': reason, 'formalAdoption': False,
            'originals': {name: original(ref) for name, ref in
                          [('world', world_ref), ('look', look_ref), ('sourceAnalysis', analysis_ref)] if ref},
            'scenes': {sid: original(ref) for sid, ref in (scene_state_refs or {}).items()}}
    ref = workshop.objects.put('selected-film-identity:' + work_id, body)
    return {'ref': dump_contract(ref), **body}


def resolve_identity(workshop, context, *, work_id: str, scene_id: str | None):
    selected = (context or {}).get('filmIdentity')
    if not selected:
        return None  # Historical inputs do not acquire a new requirement.
    body = workshop.objects.read_ref(SourcePin.model_validate(selected['ref']))
    if (body != {k: v for k, v in selected.items() if k != 'ref'}
            or body.get('schemaVersion') != SCHEMA or body.get('workId') != work_id
            or body.get('sceneId') not in (None, scene_id)):
        raise ValueError('Film identity selection or scope mismatch')
    for row in [*body['originals'].values(), *body['scenes'].values()]:
        original = workshop._read(SourcePin.model_validate(row['ref']), 'screenplay-context-v1')
        if original != row['original'] or original['workId'] != work_id:
            raise ValueError('Film identity original mismatch')
    return deepcopy(selected)


def identity_view(context, scene_id: str | None = None) -> dict[str, Any]:
    selected = (context or {}).get('filmIdentity')
    if not selected:
        return {}

    def prose(row):
        return {**{k: v for k, v in row['original'].items()
                   if k not in {'schemaVersion', 'workId'}},
                'contentFingerprint': row['ref']['fingerprint']}

    return {'selectionFingerprint': selected['ref']['fingerprint'],
            'selectedBy': selected['selectedBy'], 'selectionReason': selected['selectionReason'],
            'formalAdoption': selected['formalAdoption'],
            **{k: prose(v) for k, v in selected['originals'].items()},
            'scenes': {sid: prose(row) for sid, row in selected['scenes'].items()
                       if scene_id is None or sid == scene_id}}


def narrative_inputs(workshop, context, *, work_id: str, scene_id: str | None = None):
    """Resolve explicit pins before authorship; bind new meaning to cache basis."""
    professional = workshop.professional_context(context, work_id=work_id, scene_id=scene_id)
    looks = professional['filmLook']
    if context.get('filmIdentity') and 'look' in context['filmIdentity']['originals'] and looks:
        raise ValueError('Select prose Film Look or structured Film Look, not competing baselines')
    extra = {}
    if context.get('filmIdentity'):
        extra['filmIdentityFingerprint'] = context['filmIdentity']['ref']['fingerprint']
    if looks:
        extra['filmLookFingerprints'] = [row['ref']['fingerprint'] for row in looks]
    return identity_view(context), [row['design'] for row in looks], extra
