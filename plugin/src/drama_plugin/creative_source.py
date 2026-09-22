"""Creative-source control plane and compiler. No LLM, provider or rights inference.

Semantic decisions are authored/reviewed by the named skills. Structural checks
verify their references, review freshness and scope before deterministic projection.
"""
from __future__ import annotations

import hashlib
import runpy
from pathlib import Path
from typing import Any

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creative_source import (
    CompileSourceRequest, HistoricalPackage, LiteraryPackage, RightsGate,
    ScreenplayInput, SourceMapEntry, CreativeSourceType,
)
from drama_plugin.contracts.source_pin import SourcePin

HISTORICAL_PIPELINE = ('historical-research', 'historical-scope', 'historical-spine',
    'historical-actor-hierarchy', 'narrative-authority', 'protagonist', 'story-architecture')
LITERARY_PIPELINE = ('literary-source-analysis', 'philosophical-core',
    'literary-adaptation', 'dramatic-compression', 'literature-to-cinema')
# One canonical preference; Skills consume this projection, never a word blacklist.
THEME_EXPRESSION_ORDER = ('CHARACTER_CHOICE', 'ACTION', 'CONSEQUENCE', 'PERFORMANCE',
    'SPATIAL_RELATION', 'OBJECT_MOTIF', 'VISUAL_COMPOSITION', 'SOUND', 'SILENCE',
    'DIALOGUE', 'EXPLICIT_EXPLANATION')


def route(source_type: CreativeSourceType) -> tuple[str, ...]:
    if source_type == 'HISTORICAL':
        return HISTORICAL_PIPELINE
    if source_type == 'LITERARY':
        return LITERARY_PIPELINE
    raise ValueError('UNSUPPORTED_CREATIVE_SOURCE_TYPE')


def _unique(values: Any, label: str) -> None:
    items = list(values)
    if len(items) != len(set(items)):
        raise ValueError('DUPLICATE_' + label)


def _subset(values: Any, known: Any, label: str) -> None:
    if not set(values) <= set(known):
        raise ValueError('DANGLING_' + label)


def review_subjects(p: LiteraryPackage) -> dict[str, Any]:
    return {
        'literary-source-analysis': {'artifacts': [dump_contract(a) for a in p.artifacts],
            'sourceArtifactId': p.source_artifact_id, 'anchors': [dump_contract(a) for a in p.anchors],
            'analysis': dump_contract(p.analysis)},
        'philosophical-core': dump_contract(p.philosophical_core),
        'literary-adaptation': {'adaptation': dump_contract(p.adaptation), 'compression': dump_contract(p.compression)},
        'literature-to-cinema': dump_contract(p.cinema),
        'character-dramaturgy': dump_contract(p.character_arc),
    }


def review_hashes(p: LiteraryPackage) -> dict[str, str]:
    # Every stage review binds the full upstream semantics, preventing stale approvals
    # after a source, interpretation or adaptation change, even if IDs stay the same.
    subjects = review_subjects(p)
    foundation = subjects['literary-source-analysis']
    philosophy = subjects['philosophical-core']
    adaptation = subjects['literary-adaptation']
    return {k: sha256_canonical({'subject': v, 'upstream':
        [] if k == 'literary-source-analysis' else [foundation] if k == 'philosophical-core'
        else [foundation, philosophy] if k == 'literary-adaptation'
        else [foundation, philosophy, adaptation]}) for k, v in subjects.items()}


def validate_literary(p: LiteraryPackage) -> None:
    artifacts = {a.id: a for a in p.artifacts}
    _unique((a.id for a in p.artifacts), 'ARTIFACT')
    if p.source_artifact_id not in artifacts:
        raise ValueError('MISSING_DESIGNATED_SOURCE')
    if [a.id for a in p.artifacts if a.role == 'SOURCE_OF_TRUTH'] != [p.source_artifact_id]:
        raise ValueError('ONE_DESIGNATED_SOURCE_OF_TRUTH_REQUIRED')
    if artifacts[p.source_artifact_id].kind not in {'ORIGINAL_TEXT', 'TRANSLATION', 'EDITION'}:
        raise ValueError('MODERN_ADAPTATION_CANNOT_BECOME_SOURCE_TRUTH')
    for a in p.artifacts:
        if hashlib.sha256(a.text.encode()).hexdigest() != a.text_sha256:
            raise ValueError('SOURCE_ARTIFACT_HASH_MISMATCH')
        if a.derived_from:
            _subset([a.derived_from], artifacts, 'PARENT_ARTIFACT')
            seen = {a.id}
            parent: str | None = a.derived_from
            while parent:
                if parent in seen:
                    raise ValueError('ARTIFACT_DERIVATION_CYCLE')
                seen.add(parent)
                if parent not in artifacts:
                    raise ValueError('DANGLING_PARENT_ARTIFACT')
                parent = artifacts[parent].derived_from
    anchors = {a.id: a for a in p.anchors}
    _unique((a.id for a in p.anchors), 'ANCHOR')
    for anchor in p.anchors:
        if anchor.artifact_id != p.source_artifact_id:
            raise ValueError('REFERENCE_CONTAMINATES_SOURCE_TRUTH')
        text = artifacts[anchor.artifact_id].text
        if not 0 <= anchor.start < anchor.end <= len(text) or text[anchor.start:anchor.end] != anchor.quote:
            raise ValueError('SOURCE_ANCHOR_QUOTE_MISMATCH')
    units = {u.id: u for u in p.analysis.units}
    _unique((u.id for u in p.analysis.units), 'SOURCE_UNIT')
    characters = {u.id for u in p.analysis.units if u.kind == 'CHARACTER'}
    for u in p.analysis.units:
        _subset(u.anchor_ids, anchors, 'UNIT_ANCHOR')
        _subset(u.supports, units, 'INTERPRETATION_SUPPORT')
        _subset(u.character_ids, characters, 'CHARACTER')
        if u.origin == 'SOURCE_FACT' and any(units[s].origin != 'SOURCE_FACT' for s in u.supports):
            raise ValueError('INTERPRETATION_CANNOT_UPGRADE_TO_SOURCE_FACT')
        if u.origin == 'INTERPRETATION' and (not u.supports or any(units[s].origin != 'SOURCE_FACT' for s in u.supports)):
            raise ValueError('INTERPRETATION_REQUIRES_SOURCE_FACT_SUPPORT')
    categories = {'CHARACTER', 'RELATIONSHIP', 'EVENT', 'POV', 'CHRONOLOGY', 'NARRATOR', 'SETTING',
        'OBJECT', 'MOTIF', 'IMAGE', 'INTERNAL_STATE', 'ARC', 'CONFLICT', 'SCENE', 'STRUCTURE'}
    present = {u.kind for u in p.analysis.units}
    if present | set(p.analysis.absent_categories) != categories or present & set(p.analysis.absent_categories):
        raise ValueError('ANALYSIS_CATEGORY_COVERAGE_REQUIRED')
    _unique(p.analysis.event_order, 'EVENT_ORDER')
    if set(p.analysis.event_order) != {u.id for u in p.analysis.units if u.kind == 'EVENT'}:
        raise ValueError('EVENT_ORDER_MUST_COVER_SOURCE_EVENTS')
    _subset(p.philosophical_core.source_unit_ids, units, 'PHILOSOPHY_SOURCE')
    preserve = p.adaptation.preserved
    protected = set(preserve.must_keep + preserve.core_relationships + preserve.core_events)
    _subset(protected, units, 'PRESERVED_UNIT')
    if any(units[u].kind != 'EVENT' for u in preserve.core_events) or any(units[u].kind != 'RELATIONSHIP' for u in preserve.core_relationships):
        raise ValueError('PRESERVATION_CATEGORY_MISMATCH')
    decisions = {d.id: d for d in p.adaptation.decisions}
    _unique((d.id for d in p.adaptation.decisions), 'ADAPTATION_DECISION')
    covered: set[str] = set()
    for d in p.adaptation.decisions:
        _subset(d.source_unit_ids, units, 'DECISION_SOURCE')
        if d.operation not in p.adaptation.permitted_changes:
            raise ValueError('OPERATION_OUTSIDE_ADAPTATION_CONTRACT')
        if d.operation == 'REMOVE' and protected & set(d.source_unit_ids):
            raise ValueError('CANNOT_REMOVE_PRESERVED_SOURCE')
        if d.operation == 'MERGE' and len(set(d.source_unit_ids)) < 2:
            raise ValueError('MERGE_REQUIRES_MULTIPLE_SOURCE_UNITS')
        covered.update(d.source_unit_ids)
    if covered != set(units):
        raise ValueError('UNACCOUNTED_SOURCE_UNIT_REQUIRES_ADAPTATION_DECISION')
    mappings = {m.decision_id: m for m in p.compression.mappings}
    _unique((m.decision_id for m in p.compression.mappings), 'COMPRESSION_DECISION')
    if set(mappings) != set(decisions):
        raise ValueError('COMPRESSION_MUST_MAP_EVERY_DECISION')
    for key, m in mappings.items():
        _unique(m.destination_ids, 'DESTINATION')
        if (decisions[key].operation == 'REMOVE') != (not m.destination_ids):
            raise ValueError('REMOVAL_HAS_NO_DESTINATION_OTHER_DECISIONS_REQUIRE_ONE')
    _unique((e.id for e in p.cinema.expressions), 'CINEMA_EXPRESSION')
    expressed = set()
    for e in p.cinema.expressions:
        _subset([e.decision_id], decisions, 'CINEMA_DECISION')
        _subset([e.destination_id], mappings[e.decision_id].destination_ids, 'CINEMA_DESTINATION')
        if set(e.channels) & {'VOICE_OVER', 'EXPLICIT_EXPLANATION'} and not e.explicitness_exception:
            raise ValueError('EXPLICIT_THEME_OR_VOICE_OVER_REQUIRES_DIRECTOR_CHOICE')
        if e.explicitness_exception:
            _subset(e.explicitness_exception.source_unit_ids, decisions[e.decision_id].source_unit_ids, 'EXPLICITNESS_SOURCE')
        expressed.add((e.decision_id, e.destination_id))
    if expressed != {(m.decision_id, dest) for m in p.compression.mappings for dest in m.destination_ids}:
        raise ValueError('CINEMA_MUST_REALIZE_ALL_COMPRESSION_DESTINATIONS')
    _unique(((s.character_id, s.arc_stage) for s in p.character_arc.states), 'CHARACTER_ARC_STAGE')
    for s in p.character_arc.states:
        _subset([s.character_id], characters, 'ARC_CHARACTER')
        _subset(s.source_unit_ids, units, 'ARC_SOURCE')
        if s.origin == 'ADAPTATION_INVENTION':
            if s.adaptation_decision_id is None or s.adaptation_decision_id not in decisions:
                raise ValueError('INVENTED_ARC_REQUIRES_ADAPTATION_DECISION')
            _subset(s.source_unit_ids, decisions[s.adaptation_decision_id].source_unit_ids, 'ARC_DECISION_SOURCE')
        elif s.adaptation_decision_id is not None:
            raise ValueError('ADAPTATION_DECISION_CANNOT_BE_LABELLED_SOURCE_OR_INTERPRETATION')
        if s.origin == 'SOURCE_FACT' and any(units[u].origin != 'SOURCE_FACT' for u in s.source_unit_ids):
            raise ValueError('ARC_INTERPRETATION_CANNOT_UPGRADE_SOURCE')
    if {s.character_id for s in p.character_arc.states} != characters:
        raise ValueError('CHARACTER_ARC_COVERAGE_REQUIRED')
    _unique((r.authority for r in p.reviews), 'REVIEW_AUTHORITY')
    expected = review_hashes(p)
    if {r.authority for r in p.reviews} != set(expected):
        raise ValueError('MISSING_SPECIALIST_REVIEW')
    for r in p.reviews:
        if r.status != 'APPROVED' or r.subject_hash != expected[r.authority]:
            raise ValueError('UNAPPROVED_OR_STALE_SPECIALIST_REVIEW:' + r.authority)


def rights_gate(p: LiteraryPackage, jurisdiction: str, intended_use: str) -> RightsGate:
    reasons = []
    for a in p.artifacts:
        if a.role != 'SOURCE_OF_TRUTH':
            continue  # Aesthetic research confers no copying/adaptation rights.
        r = a.rights
        if intended_use == 'STUDY':
            continue  # This is structure inspection, explicitly not production authorization.
        if r.status in {'UNKNOWN', 'RESTRICTED'}:
            reasons.append(a.id + ':' + r.status)
        if jurisdiction not in r.jurisdictions:
            reasons.append(a.id + ':JURISDICTION_NOT_RECORDED')
        if not (r.evidence and r.asserted_by and r.basis):
            reasons.append(a.id + ':RIGHTS_EVIDENCE_REQUIRED')
        required = {'ADAPTATION', 'COMMERCIAL_PRODUCTION'} if intended_use == 'COMMERCIAL_PRODUCTION' else {'ADAPTATION'}
        if not required <= set(r.permitted_uses):
            reasons.append(a.id + ':USE_OUTSIDE_RECORDED_SCOPE')
        if r.status == 'LICENSED' and not r.license_scope:
            reasons.append(a.id + ':LICENSE_SCOPE_REQUIRED')
    return RightsGate(authorized=intended_use != 'STUDY' and not reasons, jurisdiction=jurisdiction,
        intended_use=intended_use, reasons=tuple(reasons), artifact_ids=(p.source_artifact_id,))  # type: ignore[arg-type]


def _historical(p: HistoricalPackage, plugin_root: Path) -> None:
    required = ('historicalScope', 'historicalSpine', 'historicalActorHierarchy', 'narrativeAuthority', 'protagonist', 'storyArchitecture')
    if any(not p.work_content.get(k) for k in required):
        raise ValueError('HISTORICAL_FOUNDATION_REQUIRED')
    if p.work_content.get('creativeSourceType', 'HISTORICAL') != 'HISTORICAL' or 'literaryPackage' in p.work_content:
        raise ValueError('LITERARY_CANNOT_ROUTE_THROUGH_HISTORICAL')
    if p.incubation_bible.get('creativeSourceType', 'HISTORICAL') != 'HISTORICAL' or 'literaryPackage' in p.incubation_bible:
        raise ValueError('LITERARY_CANNOT_ROUTE_THROUGH_HISTORICAL')
    checker = runpy.run_path(str(plugin_root / 'skills/cinematic-screenplay-incubation/scripts/check_incubation.py'))['check']
    errors = checker(p.incubation_bible)
    if errors:
        raise ValueError('HISTORICAL_REVIEW_FAILED:' + ';'.join(errors))


def compile_source(request: CompileSourceRequest | dict[str, Any], *, plugin_root: Path | None = None) -> ScreenplayInput:
    request = CompileSourceRequest.model_validate(dump_contract(request) if isinstance(request, CompileSourceRequest) else request)
    p = request.source
    ref = SourcePin(key='creative-source:' + p.id, kind='CANON', fingerprint=sha256_canonical(p))
    if isinstance(p, HistoricalPackage):
        _historical(p, plugin_root or Path(__file__).resolve().parents[2])
        return ScreenplayInput(source_type='HISTORICAL', package_ref=ref, pipeline=route('HISTORICAL'),
            resolved_input={'workContent': p.work_content, 'incubationBible': p.incubation_bible},
            source_map=tuple(SourceMapEntry(target='historicalGrounding.claims.' + c['id'],
                origin='ADAPTATION_INVENTION' if c['certainty'] == 'Dramatic Reconstruction' else 'SOURCE_FACT' if c['certainty'] == 'Confirmed' else 'INTERPRETATION',
                layer='SOURCE_FACT' if c['certainty'] == 'Confirmed' else 'ADAPTATION_CONTRACT' if c['certainty'] == 'Dramatic Reconstruction' else 'INTERPRETATION', owner='historical-research',
                source_ref=ref, source_path='/incubationBible/historicalGrounding/claims/' + str(i), anchor_ids=tuple(c['evidence']))
                for i, c in enumerate(p.incubation_bible['historicalGrounding']['claims'])))
    validate_literary(p)
    gate = rights_gate(p, request.jurisdiction, request.intended_use)
    if request.intended_use != 'STUDY' and not gate.authorized:
        raise ValueError('RIGHTS_GATE_BLOCKED:' + ';'.join(gate.reasons))
    units = {u.id: u for u in p.analysis.units}
    decisions = {d.id: d for d in p.adaptation.decisions}
    rows: list[SourceMapEntry] = []
    def add(target: str, origin: Any, layer: Any, owner: str, path: str, ids: Any, decision: str | None = None) -> None:
        anchors = tuple(dict.fromkeys(a for u in ids for a in units[u].anchor_ids))
        rows.append(SourceMapEntry(target=target, origin=origin, layer=layer, owner=owner,
            source_ref=ref, source_path=path, anchor_ids=anchors, decision_id=decision))
    for i, u in enumerate(p.analysis.units):
        add('analysis:' + u.id, u.origin, u.origin, p.analysis.authority, '/analysis/units/' + str(i), [u.id])
    add('philosophicalCore', 'INTERPRETATION', 'INTERPRETATION', p.philosophical_core.authority,
        '/philosophicalCore', p.philosophical_core.source_unit_ids)
    for i, d in enumerate(p.adaptation.decisions):
        add('decision:' + d.id, d.origin, 'ADAPTATION_CONTRACT', p.adaptation.authority,
            '/adaptation/decisions/' + str(i), d.source_unit_ids, d.id)
    for i, m in enumerate(p.compression.mappings):
        add('compression:' + m.decision_id, 'ADAPTATION_INVENTION', 'DRAMATIC_COMPRESSION', p.compression.authority,
            '/compression/mappings/' + str(i), decisions[m.decision_id].source_unit_ids, m.decision_id)
    for i, e in enumerate(p.cinema.expressions):
        add(e.destination_id + ':' + e.id, 'ADAPTATION_INVENTION', 'LITERATURE_TO_CINEMA', p.cinema.authority,
            '/cinema/expressions/' + str(i), decisions[e.decision_id].source_unit_ids, e.decision_id)
        if e.explicitness_exception:
            add('director:' + e.id, 'ADAPTATION_INVENTION', 'DIRECTOR_DECISION', 'director',
                '/cinema/expressions/' + str(i) + '/explicitnessException', e.explicitness_exception.source_unit_ids, e.decision_id)
    for i, s in enumerate(p.character_arc.states):
        add('arc:' + s.character_id + ':' + s.arc_stage, s.origin, 'CHARACTER_ARC', p.character_arc.authority,
            '/characterArc/states/' + str(i), s.source_unit_ids, s.adaptation_decision_id)
    return ScreenplayInput(source_type='LITERARY', package_ref=ref, pipeline=route('LITERARY'), source_map=tuple(rows),
        rights_gate=gate, resolved_input={'analysis': dump_contract(p.analysis), 'philosophicalCore': dump_contract(p.philosophical_core),
            'adaptation': dump_contract(p.adaptation), 'compression': dump_contract(p.compression),
            'cinema': dump_contract(p.cinema), 'characterArc': dump_contract(p.character_arc),
            'themeExpressionOrder': list(THEME_EXPRESSION_ORDER)})


def verify_screenplay_input(source: Any, compiled: Any) -> ScreenplayInput:
    result = ScreenplayInput.model_validate(compiled)
    gate = result.rights_gate
    request = CompileSourceRequest(source=source, jurisdiction=gate.jurisdiction if gate else 'UNSPECIFIED',
        intended_use=gate.intended_use if gate else 'STUDY')
    current = compile_source(request)
    if dump_contract(current) != dump_contract(result):
        raise ValueError('SCREENPLAY_INPUT_STALE_OR_TAMPERED')
    return current


def validate_work_content(content: dict[str, Any], previous: dict[str, Any] | None = None) -> None:
    from drama_plugin.production_language import validate_work_language
    validate_work_language(content, previous)
    kind = content.get('creativeSourceType', 'HISTORICAL')
    route(kind)
    if previous and previous.get('creativeSourceType', 'HISTORICAL') != kind:
        raise ValueError('CREATIVE_SOURCE_TYPE_IMMUTABLE')
    if kind == 'LITERARY':
        if not content.get('literaryPackage') or not content.get('screenplayInput'):
            raise ValueError('LITERARY_REQUIRES_COMPILED_UPSTREAM_PACKAGE')
        if content['literaryPackage'].get('sourceType') != 'LITERARY':
            raise ValueError('LITERARY_PACKAGE_TYPE_MISMATCH')
        verify_screenplay_input(content['literaryPackage'], content['screenplayInput'])
    elif 'literaryPackage' in content or content.get('screenplayInput', {}).get('sourceType') == 'LITERARY':
        raise ValueError('LITERARY_CANNOT_BYPASS_SOURCE_DISCRIMINATOR')


def validate_script_content(work: dict[str, Any], script: dict[str, Any]) -> None:
    validate_work_content(work)
    if work.get('creativeSourceType', 'HISTORICAL') == 'LITERARY':
        if script.get('screenplayInput') != work['screenplayInput']:
            raise ValueError('SCRIPT_MUST_CONSUME_CURRENT_SCREENPLAY_INPUT')
    elif script.get('screenplayInput', {}).get('sourceType') == 'LITERARY':
        raise ValueError('SCRIPT_SOURCE_TYPE_MISMATCH')


def production_gate(content: dict[str, Any], jurisdiction: str | None) -> None:
    validate_work_content(content)
    if content.get('creativeSourceType', 'HISTORICAL') != 'LITERARY':
        return
    if not jurisdiction:
        raise ValueError('PRODUCTION_JURISDICTION_REQUIRED')
    p = LiteraryPackage.model_validate(content['literaryPackage'])
    gate = rights_gate(p, jurisdiction, 'COMMERCIAL_PRODUCTION')
    if not gate.authorized:
        raise ValueError('RIGHTS_GATE_BLOCKED:' + ';'.join(gate.reasons))
