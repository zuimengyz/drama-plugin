"""Retain compiled source and hand it to the existing Director workspace/store."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creative_source import CompileSourceRequest, ScreenplayInput
from drama_plugin.contracts.director import DirectorWorkspace
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_source import compile_source, verify_screenplay_input, validate_script_content
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore


class CreativeSourceHost:
    def __init__(self, root: Path | str):
        self.store = DirectorArtifactStore(root)

    def prepare(self, request: CompileSourceRequest) -> ScreenplayInput:
        compiled = compile_source(request)
        # Same hash-addressed store and SourcePin as existing Director/department artifacts.
        self.store.put(compiled.package_ref.key, dump_contract(request.source))
        self.store.put('screenplay-input:' + request.source.id, dump_contract(compiled))
        return compiled

    def director_handoff(self, *, work_id: str, work_content: dict[str, Any], script_content: dict[str, Any],
                         workspace_id: str, branch_id: str) -> DirectorWorkspace:
        validate_script_content(work_content, script_content)
        compiled = ScreenplayInput.model_validate(script_content['screenplayInput'])
        # Upstream control-plane validation happens before the Director enters.
        source = self.store.read_ref(compiled.package_ref)
        verify_screenplay_input(source, dump_contract(compiled))
        input_ref = self.store.put('screenplay-input:' + compiled.package_ref.key, dump_contract(compiled))
        screenplay_ref = self.store.put('screenplay:' + work_id, script_content)
        from drama_plugin.director import source_intent
        intent = source_intent(compiled)
        intent_ref = self.store.put('source-intent:' + work_id, intent)
        workspace = DirectorWorkspace(workspace_id=workspace_id, scope_id=work_id, branch_id=branch_id,
            source_pins=(compiled.package_ref, input_ref, screenplay_ref), intent_refs=(intent_ref,))
        return self.store.create(workspace)

    def retain_interpretation(self, item: dict[str, Any], *, current: dict[str, str],
                              previous_ref: SourcePin | None = None) -> SourcePin:
        """Persist an existing Cinematic Intent item with a candidate evidence facet.

        Version replacement retains the old immutable object and never approves it.
        """
        from drama_plugin.interpretation import facet, intent_pin, validate_interpretation
        f = facet(item)
        refs = (f.source_ref, *f.thesis_refs)
        originals = {p.key:self.store.read_ref(p) for p in refs}
        validate_interpretation(item, originals, current)
        if previous_ref is not None:
            old = self.store.read_ref(previous_ref); old_f = facet(old)
            if (intent_pin(old) != previous_ref or intent_pin(old).key != intent_pin(item).key
                    or f.version != old_f.version + 1 or current.get(previous_ref.key) != previous_ref.fingerprint):
                raise ValueError('INTERPRETATION_REVISION_REQUIRES_CURRENT_PREDECESSOR')
        elif f.version != 1 or intent_pin(item).key in current:
            raise ValueError('INTERPRETATION_PREDECESSOR_REQUIRED')
        return self.store.put(intent_pin(item).key, item)

    def interpretation_board(self, refs: tuple[SourcePin, ...], *, current: dict[str, str]) -> dict[str, Any]:
        from drama_plugin.interpretation import facet, project_board, resolve
        retained = {p.key:self.store.read_ref(p) for p in refs}
        items = [resolve(p, retained, current) for p in refs]
        originals = {p.key:self.store.read_ref(p) for i in items for p in (facet(i).source_ref,*facet(i).thesis_refs)}
        return project_board(items, originals, current)

    def retain_interpretation_approval(self, item_ref: SourcePin, receipt: Any, *, current: dict[str, str],
                                       approved_refs: tuple[SourcePin, ...]) -> Any:
        """Consume the original Host user approval; never manufacture it from review."""
        from drama_plugin.contracts.interpretation import InterpretationApproval
        from drama_plugin.interpretation import facet, validate_approval
        from drama_plugin.director import pin
        r=InterpretationApproval.model_validate(receipt)
        ref=pin('interpretation-approval:'+item_ref.key,dump_contract(r))
        if ref not in approved_refs or current.get(item_ref.key)!=item_ref.fingerprint:
            raise ValueError('USER_INTERPRETATION_APPROVAL_REQUIRED')
        item=self.store.read_ref(item_ref); f=facet(item)
        originals={p.key:self.store.read_ref(p) for p in (f.source_ref,*f.thesis_refs)}
        validate_approval(item,r,originals,current)
        return self.store.put(ref.key,dump_contract(r))
