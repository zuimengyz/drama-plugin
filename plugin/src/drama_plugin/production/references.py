"""Reviewed execution bindings, reusing VideoReference and ReferenceRequirement.

This is a production-assembly source, not a creative Canon or media library.
Only an already reviewed binding can be registered; consumers resolve its ref.
"""
from __future__ import annotations

from typing import Literal, Self
import re

from pydantic import ConfigDict, Field, model_validator

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.cinematic import ReferenceRequirement
from drama_plugin.contracts.video import VideoReference
from drama_plugin.contracts.location_design import SceneLocationBinding
from drama_plugin.production.contracts import SourceOwner, SourceReference, AssemblyIssueCode
from drama_plugin.production.sources import OwnedSource, SourceReadError
from drama_plugin.runtime.contracts import Identifier, ExtendedRuntimeContract, RuntimeScope, ArtifactReference

PREFIX = "execution-reference:"


class FrozenVideoReference(VideoReference):
    model_config = ConfigDict(frozen=True, revalidate_instances="always")
    media_id: Identifier


class FrozenReferenceRequirement(ReferenceRequirement):
    model_config = ConfigDict(frozen=True, revalidate_instances="always")


class ReferenceExecutionBinding(ExtendedRuntimeContract):
    """The existing media/duty contracts lack Shot scope and joint subject binding.

    The wrapper adds only those relations and explicit authorization evidence.
    No URL, syntax tag, API slot or request is accepted.
    """
    schema_version: Literal["reference-execution-binding-v1"] = "reference-execution-binding-v1"
    extension_fields = ("endpoint_frame_ref", 'source_scope', 'use_ref', 'state_ref', 'location_binding')
    binding_id: Identifier
    version: int = Field(gt=0)
    scope: RuntimeScope
    media: FrozenVideoReference
    duties: tuple[FrozenReferenceRequirement, ...] = Field(min_length=1, max_length=8)
    subject_ids: tuple[Identifier, ...] = Field(default=(), max_length=16)
    role: Literal["FIRST_FRAME", "LAST_FRAME", "REFERENCE"]
    endpoint_state: str | None = Field(default=None, min_length=1, max_length=1000)
    authorization_scope: Literal["REVIEWED_TRIAL_INPUT", "ADOPTED_PRODUCTION_INPUT"]
    authority_refs: tuple[SourceReference, ...] = Field(min_length=1, max_length=8)
    endpoint_frame_ref: ArtifactReference | None = None
    source_scope: RuntimeScope | None = None
    use_ref: SourceReference | None = None
    state_ref: SourceReference | None = None
    location_binding: SceneLocationBinding | None = None

    @model_validator(mode="after")
    def execution_identity(self) -> Self:
        if self.source_scope and self.source_scope != self.scope:
            if self.source_scope.work_id != self.scope.work_id or self.use_ref is None or self.state_ref is None:
                raise ValueError('CROSS_SCOPE_REFERENCE_REQUIRES_AUTHORED_USE_AND_STATE')
            if self.use_ref not in self.authority_refs or self.use_ref.owner != 'professional':
                raise ValueError('CROSS_SCOPE_REFERENCE_USE_AUTHORITY_REQUIRED')
        if self.endpoint_frame_ref and (self.role != "FIRST_FRAME" or self.endpoint_frame_ref.owner != "continuation-frame"):
            raise ValueError("CONTINUATION_ENDPOINT_REQUIRED")
        if not self.scope.scene_id or not self.scope.shot_id:
            raise ValueError("Execution reference is Shot scoped")
        if self.media.prompt_binding is not None:
            raise ValueError("Model/IR coverage annotations are not execution source authority")
        if len(self.subject_ids) != len(set(self.subject_ids)):
            raise ValueError("Duplicate subject binding")
        if len({(d.role, d.subject) for d in self.duties}) != len(self.duties):
            raise ValueError("Duplicate reference duty")
        if self.role != "REFERENCE" and (self.media.kind != "image" or not self.endpoint_state):
            raise ValueError("Endpoint requires an image and reviewed state")
        if any(d.establishes_opening_state for d in self.duties) and self.role != "FIRST_FRAME":
            raise ValueError("Opening duty requires a real first frame")
        for value in (self.media.media_id, self.media.version, self.media.review_ref,
                      self.endpoint_state or "", *(d.subject for d in self.duties),
                      *(d.purpose for d in self.duties), self.binding_id, *self.subject_ids,
                      *self.scope.model_dump(exclude_none=True).values(),
                      *(r.artifact_ref for r in self.authority_refs)):
            if "://" in value or value.startswith("data:") or re.search(r"@(?:图片|视频|音频)\d+|<主体\d+>", value):
                raise ValueError("URL/provider syntax is not binding authority")
        return self

    @property
    def origin_scope(self) -> RuntimeScope:
        return self.source_scope or self.scope

    def source(self) -> OwnedSource:
        return OwnedSource(SourceOwner.PROFESSIONAL,
            PREFIX + str(self.scope.shot_id) + ":" + self.binding_id, self.version,
            self.model_dump(mode="json", by_alias=True))


class ReferenceExecutionStore:
    durability = "IN_MEMORY_TEST_FOUNDATION"
    creative_authority = False

    def __init__(self):
        self._current: dict[str, ReferenceExecutionBinding] = {}
        self._by_scope: dict[RuntimeScope, dict[str, ReferenceExecutionBinding]] = {}

    def register(self, binding: ReferenceExecutionBinding) -> SourceReference:
        # Revalidate nested immutable contracts; no arbitrary extras can be retained.
        binding = ReferenceExecutionBinding.model_validate(binding.model_dump())
        source = binding.source()
        previous = self._current.get(source.artifact_ref)
        if previous and binding.scope != previous.scope:
            raise ValueError("A binding cannot move across owner scopes")
        if previous and (binding.version < previous.version or
                binding.version == previous.version and binding != previous):
            raise ValueError("A binding revision is immutable and monotonic")
        self._current[source.artifact_ref] = binding
        self._by_scope.setdefault(binding.scope, {})[source.artifact_ref] = binding
        return source.reference()

    def select(self, scope: RuntimeScope) -> tuple[OwnedSource, ...]:
        # Indexed by exact Shot; never scans media, assets, departments or history.
        return tuple(v.source() for _, v in sorted(self._by_scope.get(scope, {}).items()))

    def mode(self, scope: RuntimeScope) -> str:
        roles = {b.role for b in self._by_scope.get(scope, {}).values()
                 if any(d.necessity == "REQUIRED" for d in b.duties)}
        return ("first_last_frame" if "LAST_FRAME" in roles else "image_to_video" if "FIRST_FRAME" in roles
                else "reference" if roles else "text_to_video")

    def resolve(self, ref: SourceReference):
        binding = self._current.get(ref.artifact_ref)
        if binding is None:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, ref.owner, ref.artifact_ref)
        source = binding.source()
        if ref.owner != SourceOwner.PROFESSIONAL:
            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, ref.owner, ref.artifact_ref)
        if ref.version != source.version or ref.fingerprint != sha256_canonical(source.body):
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, ref.owner, ref.artifact_ref)
        selected = source.body
        try:
            for part in ref.path:
                selected = selected[int(part)] if isinstance(selected, list) else selected[part]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, ref.owner, ref.artifact_ref) from error
        return selected


class ReferenceBoundSources:
    """Compose native binding storage with the explicit migration Canon reader."""
    lifecycle = "MIGRATION_ONLY"  # Canon reader facade; the native store has its own authority.
    def __init__(self, legacy, references: ReferenceStore):
        self.legacy, self.references = legacy, references

    async def scope_sources(self, scope):
        return await self.legacy.scope_sources(scope)

    async def professional(self, department, pin):
        return await self.legacy.professional(department, pin)

    async def resolve(self, ref):
        if ref.artifact_ref.startswith(PREFIX):
            return self.references.resolve(ref)
        return await self.legacy.resolve(ref)


class BoundMediaReader:
    """Explicit read-only media.get_media; no list/resolve/download/Provider calls."""
    lifecycle = "MIGRATION_ONLY"
    READ_TOOLS = frozenset({"media.get_media"})
    def __init__(self, tools):
        self.tools = tools

    async def get(self, identity: str):
        return await self.tools.invoke("media.get_media", media_id=identity)


# Both existing implementations expose the same owner operations.
from typing import TYPE_CHECKING, TypeAlias
if TYPE_CHECKING:
    from drama_plugin.persistence.stores import DurableReferenceExecutionStore
ReferenceStore: TypeAlias = "ReferenceExecutionStore | DurableReferenceExecutionStore"
