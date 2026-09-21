from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
import yaml
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.character_package import CharacterPackage, CharacterPackageRef

FILES = {key: key.replace('_', '-') + ('.json' if key == 'provenance' else '.yaml')
         for key in CharacterPackage.model_fields if key != 'embodiment'}
OPTIONAL_FILES = {'embodiment':'embodiment.yaml'}
CONSUMERS = frozenset({'character-art','performance-casting','expression','director','action-choreography',
                      'dialogue-design','voice-direction','shot-production','character-external-driver',
                      'character-embodiment','dramatic-performance-direction'})

class CharacterPackageError(ValueError):
    pass

class UniqueLoader(yaml.SafeLoader):
    pass

def _mapping(loader: UniqueLoader, node: Any, deep: bool = False) -> dict:
    result = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in result:
            raise CharacterPackageError('DUPLICATE_PACKAGE_KEY')
        result[key] = loader.construct_object(v, deep=deep)
    return result
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)

def resolve_root(value: str | Path = '', *, plugin_root: Path | None = None) -> Path:
    raw = str(value).strip()
    if raw:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            raise CharacterPackageError('CHARACTER_REPOSITORY_ROOT_MUST_BE_ABSOLUTE')
    elif sys.platform == 'darwin':
        candidate = Path.home() / 'Library/Application Support/drama-plugin/character-repository'
    elif sys.platform == 'win32':
        candidate = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'drama-plugin/character-repository'
    else:
        candidate = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'drama-plugin/character-repository'
    root = candidate.resolve()
    # An external repository may have its OWN Git history. Only plugin source trees are forbidden.
    for boundary in (Path(__file__).resolve().parents[4], plugin_root):
        if boundary is None:
            continue
        boundary = boundary.resolve()
        git_root = next((p for p in (boundary, *boundary.parents) if (p / '.git').exists()), boundary)
        if root == git_root or root.is_relative_to(git_root):
            raise CharacterPackageError('CHARACTER_ASSETS_MUST_BE_OUTSIDE_PLUGIN_SOURCE')
    return root

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def manifest_digest(manifest: dict) -> str:
    return sha256_canonical({k:v for k,v in manifest.items() if k != 'checksum'})

def safe_content(value: Any) -> None:
    """Reject credential keys and signed URLs without echoing their values."""
    if isinstance(value, dict):
        for k,v in value.items():
            if re.sub('[^a-z]', '', str(k).lower()) in {'apikey','secret','secretkey','accesstoken','authorization','password'}:
                raise CharacterPackageError('CREDENTIAL_IN_CHARACTER_PACKAGE')
            safe_content(v)
    elif isinstance(value, (list,tuple)):
        for v in value: safe_content(v)
    elif isinstance(value, str) and re.search(r'https?://\S*[?&](?:x-amz-|x-goog-|signature=|token=|sig=)',value,re.I):
        raise CharacterPackageError('SIGNED_URL_IN_CHARACTER_PACKAGE')

class CharacterRepository:
    """Read-only API; returns detached snapshots. Mutating a snapshot never edits assets."""
    def __init__(self, root: str | Path = '', *, plugin_root: Path | None = None):
        self.root = resolve_root(root, plugin_root=plugin_root)

    def _safe_file(self, relative: str) -> Path:
        path = self.root / relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts or not path.resolve().is_relative_to(self.root):
            raise CharacterPackageError('PACKAGE_PATH_ESCAPE')
        # Do not make packages depend on mutable symlink destinations.
        if any(p.is_symlink() for p in (path, *path.parents) if p != self.root and p.is_relative_to(self.root)):
            raise CharacterPackageError('PACKAGE_SYMLINK_NOT_ALLOWED')
        return path

    def load_character_package(self, character_package_ref: str, character_package_version: str,
                               *, checksum: str | None = None, _ancestry: tuple[str, ...] = ()) -> CharacterPackage:
        CharacterPackageRef(character_package_ref=character_package_ref,
                            character_package_version=character_package_version, checksum=checksum or '0'*64)
        relative = f'{character_package_ref}/{character_package_version}'
        if relative in _ancestry or len(_ancestry)>16: raise CharacterPackageError('CYCLIC_EMBODIMENT_SOURCE')
        folder = self._safe_file(relative)
        if not folder.is_dir(): raise CharacterPackageError('CHARACTER_PACKAGE_MISSING')
        data = {}
        try:
            for field, name in FILES.items():
                path = self._safe_file(f'{relative}/{name}')
                if path.stat().st_size > 2_000_000: raise CharacterPackageError('PACKAGE_DOCUMENT_TOO_LARGE')
                # YAML loader also parses JSON, with duplicate detection in both.
                data[field] = yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
            if data['manifest'].get('schemaVersion') == 'character-package-v2':
                path=self._safe_file(f'{relative}/embodiment.yaml')
                if path.stat().st_size>2_000_000: raise CharacterPackageError('PACKAGE_DOCUMENT_TOO_LARGE')
                data['embodiment']=yaml.load(path.read_text(encoding='utf-8'),Loader=UniqueLoader)
            safe_content(data)
            package = CharacterPackage.model_validate(data)
        except CharacterPackageError: raise
        except Exception:
            raise CharacterPackageError('MALFORMED_CHARACTER_PACKAGE') from None
        m = package.manifest
        if f'characters/{m.project_id}/{m.character_id}' != character_package_ref or m.version != character_package_version:
            raise CharacterPackageError('CHARACTER_PACKAGE_IDENTITY_MISMATCH')
        expected = set(FILES.values()) - {'manifest.yaml'}
        if package.embodiment is not None: expected.add('embodiment.yaml')
        elif 'embodiment.yaml' in m.file_checksums: raise CharacterPackageError('EMBODIMENT_SCHEMA_VERSION_MISMATCH')
        if not expected.issubset(m.file_checksums): raise CharacterPackageError('INCOMPLETE_PACKAGE_CHECKSUMS')
        actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p != folder/'manifest.yaml'}
        if actual != set(m.file_checksums): raise CharacterPackageError('UNMANIFESTED_PACKAGE_FILE')
        for name, sha in m.file_checksums.items():
            path = self._safe_file(f'{relative}/{name}')
            if not path.is_file() or digest(path.read_bytes()) != sha:
                raise CharacterPackageError('PACKAGE_FILE_CHECKSUM_MISMATCH')
        if manifest_digest(dump_contract(m)) != m.checksum or (checksum and checksum != m.checksum):
            raise CharacterPackageError('PACKAGE_CHECKSUM_MISMATCH')
        for name, sha in package.provenance.source_files.items():
            path = self._safe_file(name)
            if not path.is_file() or digest(path.read_bytes()) != sha:
                raise CharacterPackageError('PACKAGE_SOURCE_MISSING_OR_CHANGED')
        if package.embodiment is not None:
            from .embodiment import verify_embodiment_sources
            p=package.embodiment.provenance
            source=self.load_character_package(p.source_character_package,p.source_version,checksum=p.source_checksum,_ancestry=(*_ancestry,relative))
            verify_embodiment_sources(package,source)
        return package

    def verify_downstream_embodiment(self, reference: CharacterPackageRef, proposed: dict | None) -> None:
        package=self.load_character_package(reference.character_package_ref,reference.character_package_version,checksum=reference.checksum)
        original=dump_contract(package.embodiment) if package.embodiment else None
        if sha256_canonical(original)!=sha256_canonical(proposed):
            raise CharacterPackageError('DOWNSTREAM_EMBODIMENT_REDEFINITION')

    def resolve_character_package(self, reference: CharacterPackageRef, *, consumer: str,
                                  purpose: str = 'DESIGN_REVIEW', route: str | None = None) -> dict:
        if consumer not in CONSUMERS: raise CharacterPackageError('UNKNOWN_CHARACTER_CONSUMER')
        package = self.load_character_package(reference.character_package_ref, reference.character_package_version, checksum=reference.checksum)
        permitted = {'DESIGN_REVIEW': {'DRAFT','DESIGN_REVIEW','VISUAL_TESTING','USER_APPROVED','PRODUCTION_READY'},
                     'CASTING': {'VISUAL_TESTING','USER_APPROVED','PRODUCTION_READY'}, 'PRODUCTION': {'PRODUCTION_READY'}}
        if purpose not in permitted or package.manifest.status not in permitted[purpose]:
            raise CharacterPackageError('CHARACTER_PACKAGE_NOT_READY_FOR_PURPOSE')
        if route is not None and route not in package.visual_expression.routes:
            raise CharacterPackageError('CHARACTER_EXPRESSION_ROUTE_NOT_AUTHORED')
        payload = dump_contract(package)
        if route is not None:
            payload['visualExpression'] = {'routes': {route: payload['visualExpression']['routes'][route]}}
        return {'packageId':package.manifest.package_id,'characterId':package.manifest.character_id,
                'version':package.manifest.version,'status':package.manifest.status,
                'characterPackageRef':reference.character_package_ref,'characterPackageVersion':reference.character_package_version,
                'checksum':reference.checksum,'access':'READ_ONLY',**payload}

    def verify_downstream_core(self, reference: CharacterPackageRef, proposed_core: dict) -> None:
        original = self.load_character_package(reference.character_package_ref, reference.character_package_version, checksum=reference.checksum)
        if sha256_canonical(proposed_core) != sha256_canonical(dump_contract(original.core)):
            raise CharacterPackageError('DOWNSTREAM_CHARACTER_CORE_REDEFINITION')
