"""Bounded projection of existing phase/place/age scopes; no creative authoring.

Legacy prose is split into exact owner spans. Unknown facts are retained; explicit
other-place/age events stay background. Typed beat/location/subject scopes win.
"""
from __future__ import annotations

import re
from drama_plugin.generation.contracts import ScopedFact, UnitExecutionContext
from drama_plugin.generation.sources import child
from drama_plugin.production.contracts import DomainReference

PLACES = {
    'school': r'school\w*|学校|校园',
    'university': r'universit\w*|大学',
    'street': r'street\w*|urban|city crowd|街道|空街',
    'room': r'attic|armchair|fifth.floor|\broom\b|阁楼|房间|扶手椅',
    'forest': r'forest|grove|树林|森林',
    'coast': r'coast|shore|island|海岸|岛屿',
    'space': r'outer space|cosmos|太空',
}
AGES = {'child': r'\bboy\b|child\w*|schoolchild|少年|童年',
        'youth': r'\byoung\b|\byouth\b|university|青年',
        'adult': r'\badult\b|adulthood|成年'}


def labels(text, vocabulary):
    return {key for key, pattern in vocabulary.items() if re.search(pattern, text, re.I)}


def phase_labels(phase):
    text = str(phase.get('entryState', ''))
    return labels(text, PLACES), labels(text, AGES)


def phase_boundary(phases, index, shot):
    phase = phases[index]
    explicit = phase.get('transition')
    if explicit in ('cut', 'continuous', 'match'):
        return {'cut': 'CUT', 'continuous': 'CONTINUE', 'match': 'MATCH'}[explicit]
    if index == 0:
        return 'START'
    previous_place, previous_age = phase_labels(phases[index-1])
    place, age = phase_labels(phase)
    change = bool(place and previous_place and place.isdisjoint(previous_place) or
                  age and previous_age and age.isdisjoint(previous_age))
    design = ' '.join(str(shot.get(k, '')) for k in ('coverage', 'editingRelation', 'requiredTransition'))
    if change and re.search(r'hard.?cut|montage|硬切|蒙太奇', design, re.I):
        return 'CUT'
    if change:
        raise ValueError('PHASE_BOUNDARY_DESIGN_REQUIRED')
    return 'CONTINUE'


def scoped_spans(text, places, ages, *, final_phase, path, entered_places=frozenset()):
    """Only explicit irrelevant clauses are suppressed. Returned spans pin bytes."""
    spans = []
    inherited_places, inherited_ages = set(), set()
    # Keep decimal timing intact. Lists/conjunctions have independent place scopes.
    split = r';|(?<!\d)\.(?!\d)|,|\band\b|\bthen\b'
    start = 0
    for end in [m.start() for m in re.finditer(split, text, re.I)] + [len(text)]:
        raw = text[start:end]
        left = start + len(raw) - len(raw.lstrip()); right = end - len(raw) + len(raw.rstrip())
        part = text[left:right]
        p, a = labels(part, PLACES), labels(part, AGES)
        # Unlabelled trailing clauses belong to the last explicitly named
        # environment/state in this same authored leaf. Splitting "Street:
        # wind; footsteps" must not make its footsteps a school instruction.
        if p: inherited_places = p
        else: p = inherited_places
        if a: inherited_ages = a
        else: a = inherited_ages
        outside = bool(p and places and p.isdisjoint(places) or a and ages and a.isdisjoint(ages))
        # Identity constraints describe the current subject/reference use. A
        # reference video's final close view is not a future dramatic event.
        future = not final_phase and 'identityConstraints' not in path and bool(re.search(r'final (?:line|segment)|before the adult|最后|末段', part, re.I))
        global_timing = 'temporalStructure' in path and bool(re.search(r'\d\s*(?:-|–)?\s*\d*\s*(?:seconds|秒)', part, re.I))
        whole_montage = bool(re.search(r'montage across|compress.*years|transition to', part, re.I))
        completed_entry = bool(p & entered_places and re.search(
            r'\bbefore\b.*\b(?:segment|vignette|entry|entering|arrival)\b|进入.*前', part, re.I))
        if part and not (outside or future or global_timing or whole_montage or completed_entry):
            spans.append((left, right))
        # Move past the delimiter that begins at this end.
        match = re.match(split, text[end:], re.I)
        start = end + (len(match.group()) if match else 0)
    return tuple(spans)


def make_context(*, phase, phases, index, shot, shot_ref, action_ref, facts, values, voice_ref):
    places, ages = phase_labels(phase)
    previous_places, _ = phase_labels(phases[index-1]) if index else (set(), set())
    entered_places = places & previous_places
    boundary = phase_boundary(phases, index, shot)
    fragments, background, current = [], [], []
    for fact in sorted(facts, key=lambda f: (f.domain.value, f.reference.artifact_ref, f.reference.path)):
        ref, value = fact.reference, values[fact.reference]
        if (not isinstance(value, str) or fact.domain in ('ACTION', 'REFERENCE') or ref.owner == 'scene'
                or ref == voice_ref):
            current.append(fact); continue
        spans = scoped_spans(value, places, ages, final_phase=index == len(phases)-1, path=ref.path,
            entered_places=entered_places)
        if spans:
            current.append(fact)
            if spans != ((0, len(value)),):
                fragments.append(ScopedFact(source_ref=ref, spans=spans))
        else:
            background.append(fact)
    return tuple(current), UnitExecutionContext(boundary=boundary,
        boundary_ref=child(action_ref, 'actionPhases', str(index), 'transition') if phase.get('transition') else child(shot_ref, 'content', 'editingRelation'),
        location_keys=tuple(sorted(places)), visible_state_ref=child(action_ref, 'actionPhases', str(index), 'entryState'),
        voice_over_ref=voice_ref, fact_spans=tuple(fragments), background_refs=tuple(background))


def canonical_context(context):
    """Order-free scope declarations retain their exact refs/spans and meaning.

    Older frozen selections may reflect Python set iteration order. Normalize
    only the two unordered inventories for comparison, never rewrite a task.
    """
    return context.model_copy(update={
        'fact_spans':tuple(sorted(context.fact_spans,key=lambda f: (f.source_ref.artifact_ref,f.source_ref.path,f.spans))),
        'background_refs':tuple(sorted(context.background_refs,key=lambda f: (f.domain.value,f.reference.artifact_ref,f.reference.path)))})


def project_scoped_value(context, ref, value):
    fragment = next((f for f in context.fact_spans if f.source_ref == ref), None) if context else None
    if fragment is None:
        return value
    if not isinstance(value, str) or any(not 0 <= a < b <= len(value) for a, b in fragment.spans):
        raise ValueError('UNIT_SOURCE_SPAN_INVALID')
    return '; '.join(value[a:b] for a, b in fragment.spans)
