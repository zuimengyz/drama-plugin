"""IN_MEMORY_TEST_FOUNDATION; one authoritative final artifact per package/task/policy."""
from __future__ import annotations

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.contracts import (
    DerivedArtifact, ExecutionDiagnostic, GenerationInput, GenerationPreparation,
)
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


class GenerationArtifactStore:
    durability = "IN_MEMORY_TEST_FOUNDATION"
    creative_authority = False

    def __init__(self) -> None:
        self._artifacts: dict[str, DerivedArtifact] = {}
        self._diagnostics: dict[str, tuple[ExecutionDiagnostic, ...]] = {}
        self._inputs: dict[str, GenerationInput] = {}
        self._prepared: dict[str, ArtifactReference] = {}
        self._maintenance: set[str] = set()
        self._finals: dict[str, ArtifactReference] = {}

    def put(self, artifact: DerivedArtifact) -> ArtifactReference:
        checked = type(artifact).model_validate(artifact.model_dump())
        ref = checked.artifact_reference()
        previous = self._artifacts.get(ref.artifact_ref)
        if previous is not None and previous != checked:
            raise ValueError("Immutable artifact collision")
        self._artifacts[ref.artifact_ref] = checked
        return ref

    def get(self, ref: ArtifactReference, expected: type[DerivedArtifact]):
        item = self._artifacts[ref.artifact_ref]
        if ref != item.artifact_reference() or type(item) is not expected:
            raise ValueError("Wrong derived artifact reference/type")
        return item

    def retain_diagnostics(self, diagnostics: tuple[ExecutionDiagnostic, ...],
                           *, scope: RuntimeScope | None = None) -> ArtifactReference:
        if len(diagnostics) > 128:
            raise ValueError("Execution diagnostic budget exceeded")
        checked = tuple(ExecutionDiagnostic.model_validate(d.model_dump()) for d in diagnostics)
        identity = "execution-diagnostic:" + sha256_canonical([d.model_dump(mode="json", by_alias=True) for d in checked])
        self._diagnostics[identity] = checked
        return ArtifactReference(owner="execution-diagnostic", artifact_ref=identity, version=1)

    def diagnostics(self, ref: ArtifactReference) -> tuple[ExecutionDiagnostic, ...]:
        if ref.owner != "execution-diagnostic" or ref.version != 1:
            raise ValueError("Expected diagnostic reference")
        return self._diagnostics[ref.artifact_ref]

    def bind(self, run_id: str, inputs: GenerationInput) -> None:
        if run_id in self._inputs:
            raise ValueError("Generation task is already bound")
        self._inputs[run_id] = GenerationInput.model_validate(inputs.model_dump())

    def inputs(self, run_id: str) -> GenerationInput:
        return self._inputs.get(run_id, GenerationInput())

    def set_prepared(self, run_id: str, ref: ArtifactReference) -> None:
        self.get(ref, GenerationPreparation)
        self._prepared[run_id] = ref

    def prepared(self, run_id: str) -> ArtifactReference:
        return self._prepared[run_id]

    def claim_rebuild(self, run_id: str) -> bool:
        if run_id in self._maintenance:
            return False
        self._maintenance.add(run_id)
        return True

    def final_for(self, key: str) -> ArtifactReference | None:
        return self._finals.get(key)

    def register_final(self, key: str, ref: ArtifactReference) -> None:
        if key in self._finals and self._finals[key] != ref:
            raise ValueError("One task cannot have competing authoritative FinalPrompt artifacts")
        self._finals[key] = ref
