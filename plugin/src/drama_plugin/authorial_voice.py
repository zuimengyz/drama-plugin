"""Deterministic boundaries around a reasoned literary decision, not a prose scorer."""
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.authorial_voice import (AuthorialInterventionGate, AuthorialVoiceBudget,
    LiteraryCandidate, GATE_DIMENSIONS)


def evaluate_intervention(gate: AuthorialInterventionGate, candidate: LiteraryCandidate | None = None,
                          budget: AuthorialVoiceBudget | None = None) -> dict[str, Any]:
    gate = AuthorialInterventionGate.model_validate(dump_contract(gate))
    if candidate is not None:
        candidate = LiteraryCandidate.model_validate(dump_contract(candidate))
    if budget is not None:
        budget = AuthorialVoiceBudget.model_validate(dump_contract(budget))
        if budget.work_id != gate.work_id:
            raise ValueError('Authorial scarcity memory belongs to another work')
    reasons = []
    if gate.visual_sufficient:
        reasons.append('VISUAL_SUFFICIENCY: image/action already carries the remaining meaning')
    if not gate.world_voice_exhausted:
        reasons.append('WORLD_VOICE_FIRST: consider action, objects, environment and sound')
    if set(gate.findings) != set(GATE_DIMENSIONS):
        reasons.append('GATE_EVIDENCE_INCOMPLETE')
    if gate.literary_coda_eligibility != 'QUALIFIED':
        reasons.append('ELIGIBILITY_' + gate.literary_coda_eligibility + ': ' + gate.eligibility_reason)
    for key in ('NARRATIVE_WEIGHT', 'AUDIENCE_EMOTIONAL_INVESTMENT', 'ARC_COMPLETION', 'RESONANCE_SURPLUS',
                'REDUNDANCY_SCARCITY', 'OVER_EXPLANATION_RISK'):
        if key in gate.findings and gate.findings[key].status != 'QUALIFIED':
            reasons.append(key + ': ' + gate.findings[key].reason)
    if gate.intent is None:
        reasons.append('LITERARY_INTENT_MISSING')
    repetitions = []
    if candidate and candidate.text and budget is None:
        reasons.append('SCARCITY_MEMORY_REQUIRED')
    if candidate and budget:
        for prior in budget.recent_interventions:
            if prior.key not in budget.distinct_contribution_against:
                reasons.append('SCARCITY_NEW_CONTRIBUTION_REQUIRED:' + prior.key)
            overlap = []
            if prior.form == candidate.form:
                overlap.append('FORM_REPETITION')
            if set(prior.semantic_motifs) & set(candidate.semantic_motifs):
                overlap.append('SEMANTIC_REPETITION')
            if prior.emotional_function == candidate.emotional_function:
                overlap.append('EMOTIONAL_REDUNDANCY')
            if set(prior.character_ids) & set(candidate.character_ids):
                overlap.append('CHARACTER_REPETITION')
            if prior.key in budget.nearby_intervention_keys:
                overlap.append('NEARBY_INTERVENTION')
            if overlap:
                repetitions.append({'prior': prior.key, 'concerns': overlap})
                if prior.key not in budget.repetition_explanations:
                    reasons.append('REPETITION_NOT_JUSTIFIED:' + prior.key)
    if candidate is None or candidate.form == 'NO_AUTHORIAL_INTERVENTION':
        reasons.append('SILENCE_IS_A_COMPLETE_CHOICE')
    elif candidate.form == 'NO_TEXT_VISUAL_CODA':
        reasons.append('WORLD_VOICE_HANDOFF_ONLY: visual continuation requires its own downstream review')
    decision = 'NO_AUTHORIAL_INTERVENTION' if reasons else 'AUTHORIAL_CANDIDATE_FOR_REVIEW'
    return {'decision': decision, 'reasons': reasons, 'literaryCodaEligibility': gate.literary_coda_eligibility,
        'gateFingerprint': sha256_canonical(gate), 'candidateFingerprint': sha256_canonical(candidate) if candidate else None,
        'budgetFingerprint': sha256_canonical(budget) if budget else None, 'repetitionConcerns': repetitions,
        'candidateStatus': 'PENDING_USER_REVIEW', 'adopted': False, 'canonMutation': False,
        'characterDialogueMutation': False, 'automaticMoralVerdict': False,
        'boundary': 'Reasoned script/sequence evidence; no numeric score, factual certification, automatic prose or adoption.'}
