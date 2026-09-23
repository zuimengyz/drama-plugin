"""Sequence entry before the existing MCP reservation submission, with no fallback."""
from collections.abc import Awaitable, Callable
from typing import Any
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.creative_asset import Hash, Text
from drama_plugin.contracts.production_freeze import FrozenContract, ProductionDesignFreeze, FreezeEntry
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.sequence import executable_sequence_handoff
from drama_plugin.hosts.mcp_execution import MCPRegistry, invoke_reserved


class SequenceRequestBinding(FrozenContract):
    package_fingerprint: Hash
    freeze_fingerprint: Hash
    clip_key: Text
    request_fingerprint: Hash
    # Host captures this only AFTER projecting the clip into the sealed request.
    # Existing request verification still owns Canon, projection, quote and user budget.


async def invoke_sequence_reserved(attempt: dict[str, Any], registry: MCPRegistry, *,
        package: SequencePackage, freeze: ProductionDesignFreeze,
        current_entries: tuple[FreezeEntry, ...], current_fingerprints: dict[str, str],
        binding: SequenceRequestBinding,
        verify_request: Callable[[dict[str, Any]], None],
        claim_submission: Callable[[str], Awaitable[dict[str, Any]]],
        state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every retry/resume rechecks live approval and references before discovery/claim."""
    verdict = executable_sequence_handoff(package, current_fingerprints, freeze, current_entries)
    if not verdict['designReady'] or not verdict['productionDesignComplete']:
        raise ValueError('SEQUENCE_PRODUCTION_DESIGN_BLOCKED')
    if (binding.package_fingerprint != sha256_canonical(package)
            or binding.freeze_fingerprint != sha256_canonical(freeze)
            or binding.clip_key not in {s.key for s in package.shots}
            or binding.request_fingerprint != sha256_canonical(attempt['request'])):
        raise ValueError('SEQUENCE_REQUEST_BINDING_STALE')
    clip = next(s for s in package.shots if s.key == binding.clip_key)
    from drama_plugin.visual.history import attempt_frame
    requirements = attempt_frame(state, attempt).get('requirements', {})
    if (requirements.get('shot_id') != clip.source_shot_id or clip.production is None
            or requirements.get('target_id') != clip.production.generation_group):
        raise ValueError('SEQUENCE_REQUEST_TARGET_MISMATCH')
    return await invoke_reserved(attempt, registry, verify_request=verify_request,
                                 claim_submission=claim_submission, state=state)
