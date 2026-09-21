"""Embodiment source verification and read-only department handoff."""
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.character_package import CharacterPackage, CharacterPackageRef
from .repository import CharacterPackageError, CharacterRepository

SECTIONS={'core','dramaticIdentity','relationships','actionSignature','antiDrift','performance'}
DESIGN_SECTIONS=('core','dramaticIdentity','visualExpression','actionSignature','performance',
                 'dialogueVoice','antiDrift','relationships','historicalBasis')

def pointer_value(payload: dict, pointer: str):
    if not pointer.startswith('/') or pointer.split('/')[1] not in SECTIONS:
        raise CharacterPackageError('UNSUPPORTED_EMBODIMENT_SOURCE')
    value=payload
    try:
        for part in pointer[1:].split('/'):
            key=part.replace('~1','/').replace('~0','~')
            value=value[int(key)] if isinstance(value,list) else value[key]
    except (KeyError,ValueError,TypeError,IndexError):
        raise CharacterPackageError('CHARACTER_CORE_INSUFFICIENT') from None
    if not value: raise CharacterPackageError('CHARACTER_CORE_INSUFFICIENT')
    return value

def verify_embodiment_sources(package: CharacterPackage, source: CharacterPackage) -> None:
    e=package.embodiment
    if e is None: raise CharacterPackageError('EMBODIMENT_MISSING')
    p=e.provenance
    m=package.manifest
    sm=source.manifest
    if package.provenance.source_files.get(p.directive_ref)!=p.driver_directive_hash:
        raise CharacterPackageError('EMBODIMENT_DIRECTIVE_NOT_PINNED')
    if (p.source_character_package!=f'characters/{m.project_id}/{m.character_id}' or
        p.source_character_package!=f'characters/{sm.project_id}/{sm.character_id}' or
        p.source_version!=sm.version or p.source_version==m.version or p.source_checksum!=sm.checksum or
        p.source_work!=m.source_work or p.source_work!=sm.source_work or
        p.source_revision!=m.source_revision or p.source_revision!=sm.source_revision or
        m.source_fingerprint!=sm.source_fingerprint):
        raise CharacterPackageError('EMBODIMENT_SOURCE_IDENTITY_MISMATCH')
    old,new=dump_contract(source),dump_contract(package)
    if any(old[s]!=new[s] for s in DESIGN_SECTIONS):
        raise CharacterPackageError('EMBODIMENT_MUST_NOT_REWRITE_CHARACTER')
    pins=[s for r in e.rules for s in r.source]+[s for c in e.contrasts for s in c.source]
    if not {s.pointer.split('/')[1] for s in pins}<=set(p.derived_from):
        raise CharacterPackageError('EMBODIMENT_DERIVATION_NOT_DECLARED')
    for pin in pins:
        if sha256_canonical(pointer_value(old,pin.pointer))!=pin.value_hash:
            raise CharacterPackageError('EMBODIMENT_SOURCE_CHANGED')

def embodiment_handoff(repository: CharacterRepository, reference: CharacterPackageRef, *, consumer: str,
                       route: str, purpose: str='DESIGN_REVIEW') -> dict:
    """Never writes, approves or compiles prompts; comparisons remain review-only."""
    payload=repository.resolve_character_package(reference,consumer=consumer,purpose=purpose,route=route)
    e=payload.get('embodiment')
    if not e or e['depth'] in ('NONE','ARCHETYPE'): raise CharacterPackageError('EMBODIMENT_NOT_AUTHORED')
    from drama_plugin.contracts.character_embodiment import CharacterEmbodiment
    findings=CharacterEmbodiment.model_validate(e).review_findings()
    if findings: raise CharacterPackageError(','.join(findings))
    return {'characterPackageRef':reference.character_package_ref,'characterPackageVersion':reference.character_package_version,
            'checksum':reference.checksum,'access':'READ_ONLY','core':payload['core'],
            'embodiment':{k:v for k,v in e.items() if k not in ('contrasts','counterfactual')},
            'visualExpression':payload['visualExpression'],'actionSignature':payload['actionSignature'],
            'performance':payload['performance'],'artisticApproval':False}
