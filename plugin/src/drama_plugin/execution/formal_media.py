"""Drama Service owns canonical registration; local files are verified delivery cache.

The import claim is persisted before the multipart call. An ambiguous import is
looked up by its deterministic source_ref and is never blindly uploaded again.
"""
from __future__ import annotations
import hashlib
import os
import subprocess
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
from drama_plugin.generation.contracts import OwnerBindings


class FormalMediaPending(CapabilityAbsent):
    """A persisted import claim has a stable source_ref, but no known result yet."""


def native_scope_content(*, scope: RuntimeScope, owners: OwnerBindings, media: MediaIdentity,
                         package_ref: ArtifactReference, operation_ref: ArtifactReference,
                         attempt_ref: ArtifactReference, secret: str) -> dict[str, str]:
    """Authenticated owner assertion after TargetExecution admission; no Canon copy.

    Uses the existing Drama tool credential, not a new identity/approval system.
    Service validates the MAC, exact scope, typed refs and received bytes.
    """
    import hmac
    if not secret:
        raise CapabilityAbsent('FORMAL_MEDIA_NATIVE_OWNER_AUTHENTICATION_ABSENT')
    origin = canonical_json({'scope':scope.model_dump(mode='json',by_alias=True),
        'adoptedRefs':[r.model_dump(mode='json',by_alias=True) for r in owners.adopted_refs],
        'adoptionDecisionRef':owners.adoption_decision_ref.model_dump(mode='json',by_alias=True),
        'packageRef':package_ref.model_dump(mode='json',by_alias=True),
        'operationRef':operation_ref.model_dump(mode='json',by_alias=True),
        'attemptRef':attempt_ref.model_dump(mode='json',by_alias=True),
        'rightsFingerprint':owners.rights_pin.fingerprint,'contentSha256':media.content_hash})
    return {'owner':'TARGET_CREATIVE_VERSION_OWNER','originJson':origin,
        'signature':hmac.new(secret.encode(),origin.encode(),hashlib.sha256).hexdigest()}

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

    def repair_definitely_rejected_import(self, operation: ExecutionOperation, identity: MediaIdentity) -> None:
        """Archive a known NOT_FOUND refusal; an ambiguous import claim remains closed."""
        from drama_plugin.execution.contracts import OperationState
        from drama_plugin.execution.media import atomic_write
        from drama_plugin.runtime.contracts import RuntimeState
        checkpoint = self.execution_store.checkpoint(operation.artifact_reference())
        run = self.execution_store.ledger.load_run(operation.run_id)
        if (run.state != RuntimeState.FAILED or run.last_result is None
                or run.last_result.code != "FORMAL_MEDIA_NOT_FOUND"
                or checkpoint.state != OperationState.SUCCEEDED
                or checkpoint.progress.media_last_code != "FORMAL_MEDIA_NOT_FOUND"
                or checkpoint.progress.intake_media != identity or checkpoint.progress.video_ref is not None):
            raise ValueError("Exact definitely rejected canonical import required")
        self.path(identity)
        claim = self._registration_path(operation.scope, identity).with_suffix('.claim')
        archive = claim.with_suffix('.rejected-not-found.json')
        evidence = canonical_json({'claim':'SUBMITTING',
            'operationRef':checkpoint.operation_ref.model_dump(mode='json',by_alias=True),
            'attemptRef':checkpoint.attempt_ref.model_dump(mode='json',by_alias=True),
            'media':identity.model_dump(mode='json',by_alias=True),'failedRevision':run.revision,
            'failedResult':run.last_result.model_dump(mode='json',by_alias=True)}).encode()
        if archive.exists():
            if archive.read_bytes() == evidence and not claim.exists():
                return
            raise ValueError("Definite import rejection repair already consumed")
        if not claim.exists() or claim.read_bytes() != b'SUBMITTING':
            raise ValueError("Exact rejected import claim required")
        atomic_write(archive, evidence)
        claim.unlink()  # Original claim and failure survive together in the immutable archive.
    def _registration(self, scope: RuntimeScope, identity: MediaIdentity) -> FormalRegistration:
        ledger = self.execution_store.ledger
        key = scope.work_id+':'+identity.content_hash
        try:
            ref = ArtifactReference.model_validate(ledger.get_index('formal-media-current', key))
        except KeyError:
            # The immutable owner already committed; a derived index was lost.
            with ledger.transaction() as db:
                rows = db.execute("""SELECT artifact_id,version FROM immutable_artifact
                    WHERE artifact_type=? AND work_id=? AND scene_id IS ? AND shot_id IS ?
                    AND json_extract(body_json,'$.identity.contentHash')=? LIMIT 2""",
                    (FormalRegistration.owner,scope.work_id,scope.scene_id,scope.shot_id,identity.content_hash)).fetchall()
            if len(rows) != 1:
                if len(rows) > 1:
                    raise ValueError('Conflicting formal registrations')
                raise
            ref = ArtifactReference(owner=FormalRegistration.owner,artifact_ref=rows[0]['artifact_id'],version=rows[0]['version'])
            body, stored_scope, fingerprint = ledger.get_artifact(FormalRegistration.owner, ref)
            item = FormalRegistration.model_validate(body)
            if item.scope != scope or stored_scope != scope or item.identity != identity or item.fingerprint != fingerprint or item.artifact_reference() != ref:
                raise ValueError('Formal registration identity/scope/hash mismatch')
            ledger.put_index('formal-media-current',key,ref,scope=scope)
        body, stored_scope, fingerprint = ledger.get_artifact(FormalRegistration.owner, ref)
        registration = FormalRegistration.model_validate(body)
        if registration.artifact_reference() != ref or registration.fingerprint != fingerprint or stored_scope != scope or registration.scope != scope or registration.identity != identity:
            raise ValueError('Formal registration identity/scope/hash mismatch')
        return registration

    def _validate(self,item:Media,scope:RuntimeScope,media:MediaIdentity,source_ref:str)->None:
        if (item.work_id,item.shot_id,item.source_ref,item.content_hash)!=(scope.work_id,scope.shot_id,source_ref,media.content_hash) or item.media_type.value!=media.kind or item.file_size!=media.byte_count or item.mime_type!=media.mime:
            raise ValueError('Formal Media registration identity/hash/MIME/size mismatch')
    async def register(self,media:MediaIdentity,*,scope:RuntimeScope,source_ref:ArtifactReference,
                       attempt_ref:ArtifactReference|None=None,package_ref:ArtifactReference|None=None,
                       parents:tuple[MediaIdentity,...]=(), owners:OwnerBindings|None=None)->ArtifactReference:
        identity=MediaIdentity.model_validate(media.model_dump())
        path=self._registration_path(scope,identity)
        logical='target-media:'+hashlib.sha256((scope.work_id+identity.content_hash).encode()).hexdigest()
        async with self.execution_store.lock(logical):
            try:
                return self._registration(scope, identity).canonical_media_ref
            except KeyError:
                pass
            if path.exists():  # Historical sidecar reader; new registration has one durable owner.
                old=FormalRegistration.model_validate_json(path.read_bytes())
                if old.identity!=identity or old.scope!=scope:
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
                    raise FormalMediaPending('FORMAL_MEDIA_IMPORT_RECONCILIATION_REQUIRED')
                self.path(identity) # Fully hash-verified cache, not another canonical owner.
                try:
                    observation=probe(self.path(identity))
                except (ValueError,KeyError,subprocess.SubprocessError):
                    # Canonical quarantine evidence is not a technical PASS.
                    # Review reports the physical failure; no fabricated duration.
                    observation=None
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
                native = None
                if owners:
                    if not isinstance(self.provider,HttpMediaProvider) or not attempt_ref or not package_ref:
                        raise CapabilityAbsent('FORMAL_MEDIA_NATIVE_OWNER_ADAPTER_REQUIRED')
                    native = native_scope_content(scope=scope,owners=owners,media=identity,package_ref=package_ref,
                        operation_ref=source_ref,attempt_ref=attempt_ref,secret=self.provider.http.config.api_token or '')
                from drama_plugin.execution.media import atomic_write
                atomic_write(claim,b'SUBMITTING')
                item=await self.provider.import_media(work_id=scope.work_id,media_type=MediaType(identity.kind),
                    source_uri=upload.as_uri(),shot_id=scope.shot_id,purpose='TARGET_DERIVATIVE',source_ref=logical,
                    duration_ms=observation.duration_ms if observation else None,content={
                        'contentSha256':identity.content_hash,'sourceOperation':source_ref.model_dump(mode='json',by_alias=True),
                        'providerAttempt':attempt_ref.model_dump(mode='json',by_alias=True) if attempt_ref else None,
                        'packageRef':package_ref.model_dump(mode='json',by_alias=True) if package_ref else None,
                        'scope':scope.model_dump(mode='json',by_alias=True),
                        **({'targetNativeScope':native} if native else {}),
                        'parentMediaRefs':[p.model_dump(mode='json',by_alias=True) for p in parents],
                        'technicalMetadata':observation.model_dump(mode='json',by_alias=True) if observation else
                            {'probeCode':'CORRUPT_OR_UNREADABLE_MEDIA'}})
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
            return ref
    async def restore(self,scope:RuntimeScope,identity:MediaIdentity)->Path:
        registration=self._registration(scope, identity)
        try:
            return self.path(identity)
        except (OSError,ValueError):
            destination=self.directory/(identity.content_hash+'.download')
            await self.provider.download_media(registration.canonical_media_ref.artifact_ref,destination)
            content=destination.read_bytes()
            if hashlib.sha256(content).hexdigest()!=identity.content_hash or len(content)!=identity.byte_count:
                destination.unlink(missing_ok=True)
                raise ValueError('Canonical Media bytes differ from immutable identity')
            # Only this cache may be replaced, after canonical exact-hash validation.
            destination.replace(self.directory/identity.content_hash)
            metadata=self.directory/(identity.content_hash+'.metadata-recovery')
            metadata.write_bytes(identity.model_dump_json(by_alias=True).encode())
            metadata.replace(self.directory/(identity.content_hash+'.json'))
            return self.path(identity)
