"""Drama Service owns canonical registration; local files are verified delivery cache.

The import claim is persisted before the multipart call. An ambiguous import is
looked up by its deterministic source_ref and is never blindly uploaded again.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
from typing import ClassVar, Literal
from drama_plugin.contracts.media import Media, MediaType
from drama_plugin.contracts.base import canonical_json
from drama_plugin.execution.contracts import MediaIdentity, ExecutionOperation
from drama_plugin.execution.media import LocalMediaStore, probe
from drama_plugin.execution.store import ExecutionStore
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.providers.base.interfaces import MediaProvider
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope, RuntimeContract

class FormalRegistration(RuntimeContract):
    owner: ClassVar[str] = 'formal-media-registration'
    schema_version: Literal['formal-media-registration-v1'] = 'formal-media-registration-v1'
    identity: MediaIdentity
    canonical_media_ref: ArtifactReference
    source_ref: str
    scope: RuntimeScope
    @property
    def fingerprint(self) -> str:
        from drama_plugin.contracts.base import sha256_canonical
        return sha256_canonical(self)
    def artifact_reference(self) -> ArtifactReference:
        return ArtifactReference(owner=self.owner,artifact_ref=self.owner+':'+self.fingerprint,version=1)

class FormalMediaStore(LocalMediaStore):
    owner = 'DRAMA_SERVICE_MEDIA_PROVIDER'
    def __init__(self,directory:Path,provider:MediaProvider,execution_store:ExecutionStore):
        super().__init__(directory)
        self.provider,self.execution_store=provider,execution_store
    def _registration_path(self,scope:RuntimeScope,media:MediaIdentity)->Path:
        key=hashlib.sha256((scope.work_id+media.content_hash).encode()).hexdigest()
        root=self.execution_store.ledger.path.parent/(self.execution_store.ledger.path.name+".formal-media-refs")
        root.mkdir(parents=True,exist_ok=True)
        return root/(key+'.registration.json')
    def _validate(self,item:Media,scope:RuntimeScope,media:MediaIdentity,source_ref:str)->None:
        if (item.work_id,item.source_ref,item.content_hash)!=(scope.work_id,source_ref,media.content_hash) or item.media_type.value!=media.kind or item.file_size!=media.byte_count or item.mime_type!=media.mime:
            raise ValueError('Formal Media registration identity/hash/MIME/size mismatch')
    async def register(self,media:MediaIdentity,*,scope:RuntimeScope,source_ref:ArtifactReference,
                       attempt_ref:ArtifactReference|None=None,package_ref:ArtifactReference|None=None,
                       parents:tuple[MediaIdentity,...]=())->ArtifactReference:
        identity=MediaIdentity.model_validate(media.model_dump())
        path=self._registration_path(scope,identity)
        logical='target-media:'+hashlib.sha256((scope.work_id+identity.content_hash).encode()).hexdigest()
        async with self.execution_store.lock(logical):
            if path.exists():
                old=FormalRegistration.model_validate_json(path.read_bytes())
                if old.identity!=identity or old.scope.work_id!=scope.work_id:
                    raise ValueError('Formal registration changed')
                ledger=self.execution_store.ledger
                ledger.put_artifact(old.owner,old.artifact_reference(),old.scope,old.fingerprint,old)
                ledger.put_index('formal-media-current',scope.work_id+':'+identity.content_hash,old.artifact_reference(),scope=old.scope)
                return old.canonical_media_ref
            found=await self.provider.list_media(work_id=scope.work_id,source_ref=logical)
            if len(found)>1:
                raise ValueError('Duplicate canonical Media registrations')
            claim=path.with_suffix('.claim')
            if not found:
                if claim.exists():
                    raise CapabilityAbsent('FORMAL_MEDIA_IMPORT_RECONCILIATION_REQUIRED')
                self.path(identity) # Fully hash-verified cache, not another canonical owner.
                observation=probe(self.path(identity))
                extension={"video/mp4":".mp4","audio/wav":".wav","audio/mp4":".m4a"}[identity.mime]
                upload=self.directory/(identity.content_hash+extension)
                try:
                    os.link(self.path(identity),upload)
                except FileExistsError:
                    if hashlib.sha256(upload.read_bytes()).hexdigest()!=identity.content_hash:
                        raise ValueError('Upload cache hash conflict')
                # Reject local file/configuration errors before recording an
                # ambiguous remote import. Only the existing owner uploads.
                from drama_plugin.providers.http.providers import HttpMediaProvider
                from drama_plugin.providers.http.media_source import open_media_source
                if isinstance(self.provider,HttpMediaProvider):
                    async with open_media_source(upload.as_uri()):
                        pass
                from drama_plugin.execution.media import atomic_write
                atomic_write(claim,b'SUBMITTING')
                item=await self.provider.import_media(work_id=scope.work_id,media_type=MediaType(identity.kind),
                    source_uri=upload.as_uri(),shot_id=scope.shot_id,purpose='TARGET_DERIVATIVE',source_ref=logical,
                    duration_ms=observation.duration_ms,content={
                        'contentSha256':identity.content_hash,'sourceOperation':source_ref.model_dump(mode='json',by_alias=True),
                        'providerAttempt':attempt_ref.model_dump(mode='json',by_alias=True) if attempt_ref else None,
                        'packageRef':package_ref.model_dump(mode='json',by_alias=True) if package_ref else None,
                        'scope':scope.model_dump(mode='json',by_alias=True),
                        'parentMediaRefs':[p.model_dump(mode='json',by_alias=True) for p in parents],
                        'technicalMetadata':observation.model_dump(mode='json',by_alias=True)})
            else:
                item=found[0]
            self._validate(item,scope,identity,logical)
            ref=ArtifactReference(owner='media-provider',artifact_ref=item.id,version=1)
            registration=FormalRegistration(identity=identity,canonical_media_ref=ref,source_ref=logical,scope=scope)
            from drama_plugin.execution.media import atomic_write
            registration_ref=registration.artifact_reference()
            ledger=self.execution_store.ledger
            ledger.put_artifact(registration.owner,registration_ref,scope,registration.fingerprint,registration)
            ledger.put_index('formal-media-current',scope.work_id+':'+identity.content_hash,registration_ref,scope=scope)
            atomic_write(path,canonical_json(registration).encode())
            return ref
    async def restore(self,scope:RuntimeScope,identity:MediaIdentity)->Path:
        registration=FormalRegistration.model_validate_json(self._registration_path(scope,identity).read_bytes())
        try:
            return self.path(identity)
        except (OSError,ValueError):
            destination=self.directory/(identity.content_hash+'.download')
            await self.provider.download_media(registration.canonical_media_ref.artifact_ref,destination)
            self.retain(destination.read_bytes(),kind=identity.kind,mime=identity.mime,expected_hash=identity.content_hash)
            destination.unlink()
            return self.path(identity)
