"""Resolve only Package-granted execution bindings and their exact media IDs."""
from __future__ import annotations

from dataclasses import dataclass

from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.contracts import ExecutionDiagnostic, GenerationTask
from drama_plugin.generation.sources import SelectedValue
from drama_plugin.production.contracts import SourceDomain as D, SourceReference
from drama_plugin.production.references import PREFIX, ReferenceExecutionBinding
from drama_plugin.exceptions import ProviderError


@dataclass(frozen=True)
class ExecutableReference:
    source_ref: SourceReference
    binding: ReferenceExecutionBinding


@dataclass(frozen=True)
class ReferenceResolution:
    inputs: tuple[ExecutableReference, ...]
    diagnostics: tuple[ExecutionDiagnostic, ...]


class ExecutionReferenceResolver:
    """No media list, URL, download, old request/spec or inferred reference duty."""
    def __init__(self, media_reader):
        self.media_reader = media_reader

    async def resolve(self, package, task: GenerationTask, selected: tuple[SelectedValue, ...],
                      *, subjects: set[str]) -> ReferenceResolution:
        inputs, diagnostics = [], []
        for item in selected:
            ref = item.selection.reference
            if item.selection.domain != D.REFERENCE or not ref.artifact_ref.startswith(PREFIX):
                continue  # DESIGN_REFERENCE is not an executable image.
            binding = ReferenceExecutionBinding.model_validate(item.value)
            required = any(d.necessity == "REQUIRED" for d in binding.duties)
            def finding(code):
                diagnostics.append(ExecutionDiagnostic(code=code, owner="production-assembly/reference-strategy",
                    domain=D.REFERENCE, source_ref=ref, required=required))
            if (binding.scope != package_scope(package) or not set(binding.subject_ids) <= subjects or
                    any(d.role == "CHARACTER" and set(d.subject.split("+")) != set(binding.subject_ids)
                        for d in binding.duties)):
                finding("SCOPE_MISMATCH")
                continue
            if binding.role == "FIRST_FRAME":
                starts = [v.value for v in selected if v.selection.reference.owner == "shot" and
                          v.selection.reference.path[-1:] == ("visualEntryState",)]
                if starts != [binding.endpoint_state]:
                    finding("SCOPE_MISMATCH")
                    continue
            if binding.role == "LAST_FRAME":
                ends = [v.value for v in selected if v.selection.reference.owner == "shot" and
                        v.selection.reference.path[-1:] == ("visualExitState",)]
                if ends != [binding.endpoint_state]:
                    finding("SCOPE_MISMATCH")
                    continue
            if task.input_mode == "text_to_video":
                finding("REFERENCE_INPUT_UNRESOLVED" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            expected_roles = {"image_to_video": {"FIRST_FRAME"}, "first_last_frame": {"FIRST_FRAME", "LAST_FRAME"},
                              "reference": {"REFERENCE"}}[task.input_mode]
            if binding.role not in expected_roles:
                finding("REQUEST_UNSUPPORTED" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            try:
                if self.media_reader is None:
                    raise KeyError(binding.media.media_id)
                media = await self.media_reader.get(binding.media.media_id)
            except (KeyError, ValueError, LookupError, ProviderError):
                finding("REFERENCE_INPUT_UNRESOLVED" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            if (media.id != binding.media.media_id or media.work_id != binding.scope.work_id or
                    media.shot_id is not None and media.shot_id != binding.scope.shot_id or
                    media.media_type.value.lower() != binding.media.kind):
                finding("SCOPE_MISMATCH")
                continue
            if not media.content_hash:
                finding("REFERENCE_INPUT_UNRESOLVED" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            if media.content_hash != binding.media.content_hash:
                # Refresh must use a new already reviewed binding; never approve changed bytes.
                finding("PACKAGE_STALE" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            semantic_duties = {"CHARACTER": "identity", "COSTUME": "costume", "LOCATION": "environment",
                               "CONTINUITY": "continuity", "PERFORMANCE": "motion", "CAMERA_MOTION": "camera"}
            if any(d.role in semantic_duties and semantic_duties[d.role] not in binding.media.semantics for d in binding.duties):
                finding("REFERENCE_INPUT_UNRESOLVED" if required else "OPTIONAL_REFERENCE_UNRESOLVED")
                continue
            inputs.append(ExecutableReference(ref, binding))
        roles = [i.binding.role for i in inputs]
        if len({i.binding.media.media_id for i in inputs}) != len(inputs):
            diagnostics.append(ExecutionDiagnostic(code="REQUEST_UNSUPPORTED", owner="reference-strategy",
                domain=D.REFERENCE, required=True))
        valid = (task.input_mode == "text_to_video" and not inputs or
                 task.input_mode == "image_to_video" and roles == ["FIRST_FRAME"] or
                 task.input_mode == "first_last_frame" and sorted(roles) == ["FIRST_FRAME", "LAST_FRAME"] or
                 task.input_mode == "reference" and roles and set(roles) == {"REFERENCE"})
        if not valid and not any(d.required for d in diagnostics):
            diagnostics.append(ExecutionDiagnostic(code="REFERENCE_INPUT_UNRESOLVED", owner="reference-strategy",
                domain=D.REFERENCE, required=True))
        return ReferenceResolution(tuple(inputs), tuple(diagnostics))
