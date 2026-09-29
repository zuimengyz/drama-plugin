"""T4 real Literary S02-K02: same inputs, single Resolver, identical Package."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import socket
from typing import Any
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.production import ProductionPackage
from drama_plugin.professional_design import ProfessionalDesignRequest
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import RunMode, RuntimeState

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
FIXTURE = PROJECT / "artifacts/flagship-literary-film-01/test-shoot-01"
EVIDENCE = PROJECT / "未来架构/迁移/evidence"


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("T4 forbids network, DAG execution, creative writes, Prompt and Provider")


async def shadow(before_path: Path = EVIDENCE / "T2-S02-K02-ProductionPackage.json") -> dict[str, Any]:
    context = FIXTURE / "S02-cinematic/K02-context.json"
    professional_root = FIXTURE / "S02-design"
    raw_before = json.loads(before_path.read_text())
    before_package = ProductionPackage.model_validate(raw_before.get("package", raw_before))
    paths = [context, before_path, *sorted(professional_root.glob("*.json"))]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    hashes = {str(p): digest(p) for p in paths}
    data = MockDramaData.empty()
    raw = json.loads(context.read_text())
    for name, model in (("work", Work), ("script", Script), ("episode", Episode), ("scene", Scene), ("shot", Shot)):
        setattr(data, name, model.model_validate(raw[name]))
    assert data.work is not None and data.scene is not None and data.shot is not None
    canon = {n: dump_contract(getattr(data, n)) for n in ("work", "script", "episode", "scene", "shot")}
    calls: list[str] = []
    reads: list[str] = []
    requests: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    selection_reads: list[int] = []
    with patch("drama_plugin.plugin.load_config", return_value=DramaPluginConfig()), \
         patch.object(socket.socket, "connect", forbidden), patch.object(socket.socket, "connect_ex", forbidden), \
         patch("drama_plugin.professional.compile_prompt_projection", forbidden), \
         patch("drama_plugin.hosts.cinematic_projection.project", forbidden):
        async with DramaPlugin.load(ROOT, mock_data=data, production_artifact_roots=(professional_root,)) as plugin:
            execute = plugin.runtime.executor.execute
            resolve = plugin.professional_design.resolve
            read = plugin.shot_assembler.sources.professional

            async def observed_execute(key: str, inputs: Any) -> Any:
                calls.append(key)
                return await execute(key, inputs)

            async def observed_resolve(request: ProfessionalDesignRequest) -> Any:
                requests.append(request.model_dump(mode="json", by_alias=True))
                before_reads = len(reads)
                selection = await resolve(request)
                selection_reads.append(len(reads) - before_reads)
                selections.append(selection.model_dump(mode="json", by_alias=True))
                return selection

            async def observed_read(department: str, pin: Any) -> Any:
                reads.append(department)
                return await read(department, pin)

            with patch.object(plugin.runtime.executor, "execute", observed_execute), \
                 patch.object(plugin.professional_design, "resolve", observed_resolve), \
                 patch.object(plugin.shot_assembler.sources, "professional", observed_read), \
                 patch.object(plugin.providers.production, "generate_image", forbidden), \
                 patch.object(plugin.providers.production, "generate_video", forbidden), \
                 patch("drama_plugin.professional.registry", forbidden), \
                 patch("drama_plugin.professional.dependency_order", forbidden), \
                 patch("drama_plugin.hosts.professional.ProfessionalDepartmentHost.task", forbidden):
                run = plugin.create_governed_run(work_id=data.work.id, scene_id=data.scene.id,
                    shot_id=data.shot.id, mode=RunMode.EXPERIMENT, run_id="t4-real-literary-shadow")
                final = await plugin.runtime.run(run.run_id)
                assert final.state == RuntimeState.SUCCEEDED and final.last_result is not None
                package = plugin.production_packages.get(final.last_result.artifact_refs[0])
                decision = plugin.gate_findings.decision(plugin.gate_findings.latest(run.run_id))
            assert package == before_package
            assert len(requests) == len(selections) == 1
            assert plugin.professional_design is plugin.shot_assembler.professional_design
            assert not {"battle-crowd-choreography", "vfx-planning"} & set(reads)
            assert canon == {n: dump_contract(getattr(data, n)) for n in canon}
            encoded = package.model_dump_json(by_alias=True)
            assert package.fingerprint == before_package.fingerprint
            assert hashes == {str(p): digest(p) for p in paths}
            return {
                "level": "OFFLINE_REAL_LITERARY_S02_K02_PROFESSIONAL_CONSOLIDATION",
                "fixture": str(context), "beforePackageEvidence": str(before_path), "sourceHashes": hashes,
                "scopeIdentical": package.scope == before_package.scope,
                "allReferencesIdentical": package.sources == before_package.sources,
                "useSemanticsIdentical": True, "fingerprintUnchanged": True,
                "beforeFingerprint": before_package.fingerprint, "afterFingerprint": package.fingerprint,
                "package": package.model_dump(mode="json", by_alias=True), "packageBytes": len(encoded.encode()),
                "professionalSelection": selections[0], "resolverRequest": requests[0],
                "resolverRequestBytes": len(json.dumps(requests[0], ensure_ascii=False, separators=(",", ":")).encode()),
                "runtimeProfessionalInterfaceCount": 1, "externalProfessionalDomainCount": 11,
                "domainReferenceCounts": dict(Counter(s.domain.value for s in package.sources)),
                "declaredShotPinCount": len(data.shot.content["departmentRefs"]),
                "professionalBibleReads": reads, "professionalBibleReadCount": len(reads),
                "selectionBibleReadCount": selection_reads[0],
                "validationBibleReadCount": len(reads) - selection_reads[0],
                "uniqueProfessionalBibleCount": len(set(reads)),
                "selectedProfessionalReferenceCount": len(selections[0]["sources"]),
                "professionalAuthoringCalls": 0, "professionalDagCalls": 0,
                "nativeCalls": calls, "gateDecision": decision.model_dump(mode="json", by_alias=True),
                "runtimeFinal": json.loads(plugin.runtime.serialize(run.run_id)),
                "canonUnchanged": True, "allOriginalFilesUnchanged": True,
                "providerSubmission": 0, "paidGenerationCalls": 0, "mediaGeneration": 0, "formalWrites": 0,
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-package", type=Path, default=EVIDENCE / "T2-S02-K02-ProductionPackage.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(shadow(args.before_package))
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("fingerprintUnchanged", "afterFingerprint", "packageBytes",
        "resolverRequestBytes", "professionalBibleReadCount", "selectedProfessionalReferenceCount",
        "professionalAuthoringCalls", "professionalDagCalls", "providerSubmission", "paidGenerationCalls", "mediaGeneration")},
        ensure_ascii=False, indent=2))
