"""Recheck the seal against freshly resolved approval, Asset and Media evidence."""
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.production_freeze import FreezeEntry, ProductionDesignFreeze


def freeze_gate(freeze: ProductionDesignFreeze, current_entries: tuple[FreezeEntry, ...]) -> dict[str, Any]:
    freeze = ProductionDesignFreeze.model_validate(dump_contract(freeze))
    current = {e.semantic_key: FreezeEntry.model_validate(dump_contract(e)) for e in current_entries}
    if len(current) != len(current_entries):
        raise ValueError('Ambiguous current freeze evidence')
    missing = []
    for e in freeze.entries:
        reasons = []
        if current.get(e.semantic_key) != e:
            reasons.append('CURRENT_EVIDENCE_MISSING_OR_CHANGED_RESEAL_REQUIRED')
        if e.requirement == 'OPTIONAL':
            if reasons:
                missing.append({'semanticKey': e.semantic_key, 'role': e.role, 'reasons': reasons})
            continue
        if e.approval_status != 'USER_APPROVED' or not e.approval_evidence:
            reasons.append('USER_APPROVAL_MISSING')
        if not e.asset_id or not e.content_fingerprint:
            reasons.append('ASSET_IDENTITY_MISSING')
        if e.requires_visual_media and (not e.media_id or not e.media_content_hash):
            reasons.append('APPROVED_VISUAL_MEDIA_MISSING')
        if reasons:
            missing.append({'semanticKey': e.semantic_key, 'role': e.role, 'reasons': reasons})
    return {'status': 'INCOMPLETE' if missing else 'COMPLETE',
            'fingerprint': sha256_canonical(freeze), 'missing': missing,
            'generationAuthorized': False,
            'evidenceBoundary': 'Host must resolve current Asset, approval evidence and verified Media bytes; this pure gate cannot authenticate a fabricated approval assertion.'}
