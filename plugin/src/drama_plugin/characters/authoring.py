"""Explicit Host authoring entry. Production imports the read-only repository instead."""
import json
from pathlib import Path
import yaml
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.character_package import CharacterPackage, CharacterDesignAuthorization
from .repository import CharacterRepository, CharacterPackageError, FILES, digest, manifest_digest, safe_content

def create_character_version(repository: CharacterRepository, authored: dict, *,
                             authorization: CharacterDesignAuthorization, directive: bytes) -> CharacterPackage:
    package = CharacterPackage.model_validate(authored)
    m = package.manifest
    ref = f'characters/{m.project_id}/{m.character_id}'
    if (authorization.capability != 'character-external-driver' or authorization.operation != 'CREATE_VERSION'
        or ref not in authorization.allowed_package_refs or digest(directive) != authorization.directive_hash
        or authorization.source_work != m.source_work or authorization.source_revision != m.source_revision):
        raise CharacterPackageError('CHARACTER_DESIGN_AUTHORIZATION_MISMATCH')
    safe_content(dump_contract(package))
    folder = repository._safe_file(f'{ref}/{m.version}')
    # Immutable versions: existing directories are NEVER replaced, including failed writes.
    folder.mkdir(parents=True, exist_ok=False)
    payload = dump_contract(package)
    checksums = {}
    for field,name in FILES.items():
        if field == 'manifest': continue
        alias = CharacterPackage.model_fields[field].alias or field
        value = payload[alias]
        content = (json.dumps(value,ensure_ascii=False,indent=2)+'\n' if name.endswith('.json')
                   else yaml.safe_dump(value,allow_unicode=True,sort_keys=False))
        (folder/name).write_text(content,encoding='utf-8')
        checksums[name] = digest(content.encode())
    manifest = payload['manifest']
    manifest['fileChecksums'] = checksums
    manifest['checksum'] = manifest_digest(manifest)
    (folder/'manifest.yaml').write_text(yaml.safe_dump(manifest,allow_unicode=True,sort_keys=False),encoding='utf-8')
    return repository.load_character_package(ref,m.version)
