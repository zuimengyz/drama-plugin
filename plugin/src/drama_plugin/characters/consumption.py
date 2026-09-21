"""Execution gates. No provider calls and no authoring authority."""
from drama_plugin.config import load_config
from drama_plugin.contracts.character_package import CharacterPackageRef
from .repository import CharacterRepository, CharacterPackageError

def require_character_context(binding: dict | None, *, consumer: str, purpose: str, route: str | None = None) -> dict:
    if not binding: raise CharacterPackageError('CHARACTER_PACKAGE_BINDING_REQUIRED')
    reference = CharacterPackageRef.model_validate(binding)
    return CharacterRepository(load_config().character_repository_root).resolve_character_package(
        reference,consumer=consumer,purpose=purpose,route=route)

def require_work_character(work, character: str, *, consumer: str, purpose: str, route: str) -> dict:
    roster = work.content.get('characterPackageRoster',{})
    if roster.get('sourceRevision') != work.content.get('revisionId'):
        raise CharacterPackageError('CURRENT_CHARACTER_ROSTER_REQUIRED')
    rows = [r for r in roster.get('characters',[]) if character in (r.get('characterId'),r.get('name'))]
    if len(rows) != 1: raise CharacterPackageError('CHARACTER_ROSTER_IDENTITY_AMBIGUOUS_OR_MISSING')
    row = rows[0]
    if not row.get('dedicatedPackageRequired'):
        if row.get('category') not in {'ROLE_ARCHETYPE_ONLY','BACKGROUND_GROUP'}:
            raise CharacterPackageError('DEDICATED_CHARACTER_PACKAGE_REQUIRED')
        return {'access':'ARCHETYPE_ONLY','sourceRevision':roster['sourceRevision']}
    context = require_character_context(row.get('package'), consumer=consumer,purpose=purpose,route=route)
    if context['characterId'] != row['characterId'] or context['core']['identity'] != row['name']:
        raise CharacterPackageError('CHARACTER_PACKAGE_ROSTER_IDENTITY_MISMATCH')
    if context['manifest']['sourceWork'] != work.id or context['manifest']['sourceRevision'] != work.content['revisionId']:
        raise CharacterPackageError('CHARACTER_PACKAGE_SOURCE_STALE')
    return context
