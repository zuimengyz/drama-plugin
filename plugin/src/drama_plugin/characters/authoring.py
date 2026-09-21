"""Explicit Host authoring entry. Production imports the read-only repository instead."""
import json
from pathlib import Path
import yaml
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.character_package import CharacterPackage, CharacterDesignAuthorization
from .repository import CharacterRepository, CharacterPackageError, FILES, OPTIONAL_FILES, digest, manifest_digest, safe_content

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
    if package.embodiment is not None:
        from .embodiment import verify_embodiment_sources
        p=package.embodiment.provenance
        source=repository.load_character_package(p.source_character_package,p.source_version,checksum=p.source_checksum)
        verify_embodiment_sources(package,source)
        if p.driver_directive_hash!=authorization.directive_hash or p.directive_ref!=authorization.directive_ref:
            raise CharacterPackageError('EMBODIMENT_DIRECTIVE_MISMATCH')
        if package.embodiment.review_findings():
            raise CharacterPackageError(','.join(package.embodiment.review_findings()))
    folder = repository._safe_file(f'{ref}/{m.version}')
    # Immutable versions: existing directories are NEVER replaced, including failed writes.
    folder.mkdir(parents=True, exist_ok=False)
    payload = dump_contract(package)
    checksums = {}
    files={**FILES,**(OPTIONAL_FILES if package.embodiment is not None else {})}
    for field,name in files.items():
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
