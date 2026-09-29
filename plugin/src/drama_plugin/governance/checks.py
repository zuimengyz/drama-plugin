"""Translate T2 source checks; optional quality is distinct from request essentials."""
from __future__ import annotations

from drama_plugin.governance.contracts import GateCode, GateFinding
from drama_plugin.production.contracts import AssemblyIssueCode as I, AssemblyValidation, SourceDomain
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


def assembly_findings(validation: AssemblyValidation, *, scope: RuntimeScope,
                      evidence_ref: ArtifactReference) -> tuple[GateFinding, ...]:
    findings = []
    for issue in validation.issues:
        if issue.code == I.SCOPE_MISMATCH:
            code = GateCode.PACKAGE_SCOPE_MISMATCH
        elif issue.code == I.VERSION_MISMATCH:
            code = GateCode.PACKAGE_STALE
        elif issue.code == I.AUTHORITY_MISMATCH:
            code = GateCode.CANON_AUTHORITY_MISMATCH
        elif issue.domain in {SourceDomain.LIGHTING, SourceDomain.COLOR}:
            code = GateCode.OPTIONAL_SOURCE_MISSING
        else:
            code = GateCode.REQUEST_INPUT_MISSING
        findings.append(GateFinding.classified(code, owner=issue.owner.value, scope=scope,
            evidence_ref=evidence_ref, required=code == GateCode.REQUEST_INPUT_MISSING))
    return tuple(findings)
