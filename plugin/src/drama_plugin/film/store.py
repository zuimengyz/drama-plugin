"""Bounded Film checkpoints in the existing Ledger; author bytes in Canon owner IO."""
from __future__ import annotations
from typing import TypeVar
from drama_plugin.contracts.base import canonical_json
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.film.contracts import FILM_TYPES, FilmArtifact, FilmCanon, FilmDirection, FilmCheckpoint, FilmInput
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeContract, RuntimeScope

F = TypeVar('F', bound=FilmArtifact)
C = TypeVar('C', bound=RuntimeContract)
class FilmStore:
    def __init__(self, ledger: ProductionLedger, versions: CreativeVersionStore):
        self.ledger, self.versions = ledger, versions
    def bind(self, run_id: str, scope: RuntimeScope, value: FilmInput) -> None:
        self.ledger.put_index('film-input', run_id, value, scope=scope, once=True)
        self.ledger.put_index('film-checkpoint', run_id, FilmCheckpoint(), scope=scope, once=True)
    def input(self, run_id: str) -> FilmInput:
        return FilmInput.model_validate(self.ledger.get_index('film-input', run_id))
    def checkpoint(self, run_id: str) -> FilmCheckpoint:
        return FilmCheckpoint.model_validate(self.ledger.get_index('film-checkpoint', run_id))
    def save(self, run_id: str, scope: RuntimeScope, cp: FilmCheckpoint) -> None:
        self.ledger.put_index('film-checkpoint', run_id, FilmCheckpoint.model_validate(cp.model_dump()), scope=scope)
    def put(self, item: F) -> ArtifactReference:
        item = type(item).model_validate(item.model_dump())
        if type(item) not in FILM_TYPES.values() or self.ledger.load_run(item.run_id).scope != item.scope:
            raise ValueError('Film artifact owner/scope mismatch')
        ref = item.artifact_reference()
        self.ledger.put_artifact(item.owner, ref, item.scope, item.fingerprint, item)
        return ref
    def get(self, ref: ArtifactReference, model: type[F]) -> F:
        if ref.owner != model.owner:
            raise ValueError('Wrong Film artifact')
        body, scope, digest = self.ledger.get_artifact(ref.owner, ref)
        value = model.model_validate(body)
        if value.artifact_reference() != ref or value.scope != scope or value.fingerprint != digest:
            raise ValueError('Film artifact identity mismatch')
        return value
    def put_author(self, run_id: str, value: FilmCanon | FilmDirection) -> ArtifactReference:
        owner = 'film-canon' if isinstance(value, FilmCanon) else 'film-direction'
        body = value.model_dump(mode='json', by_alias=True)
        pin = self.versions.objects.put(run_id+':'+owner, body)
        ref = ArtifactReference(owner=owner, artifact_ref=run_id+':'+owner+':'+pin.fingerprint, version=1)
        # This index is outside execution persistence. It lets a recovered author
        # action resolve its fixed result without calling its model again.
        self.versions.io.write(self.versions._path('film-author', [run_id,owner]), canonical_json(ref))
        return ref
    def author_ref(self, run_id: str, owner: str) -> ArtifactReference | None:
        path = self.versions._path('film-author', [run_id,owner])
        return ArtifactReference.model_validate_json(path.read_text()) if path.exists() else None
    def author(self, ref: ArtifactReference, model: type[C]) -> C:
        owner = 'film-canon' if model is FilmCanon else 'film-direction'
        key, digest = ref.artifact_ref.rsplit(':',1)
        if ref.owner != owner or not key.endswith(':'+owner):
            raise ValueError('Wrong creative author version')
        return model.model_validate(self.versions.objects.read_ref(SourcePin(key=key, kind='CANON', fingerprint=digest)))
