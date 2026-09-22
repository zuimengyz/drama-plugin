"""Retain compiled source and hand it to the existing Director workspace/store."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creative_source import CompileSourceRequest, ScreenplayInput
from drama_plugin.contracts.director import DirectorWorkspace
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
