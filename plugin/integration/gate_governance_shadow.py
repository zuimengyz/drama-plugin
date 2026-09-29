"""Read actual T2 S02-K02 Package; controlled cases operate only on temporary copies."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import socket
import tempfile
from typing import Any
from unittest.mock import patch

from drama_plugin import DramaPlugin
from drama_plugin.config import DramaPluginConfig
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.creation import Work, Script, Episode, Scene, Shot
from drama_plugin.governance import GateCode, GateFinding, GovernanceInput
from drama_plugin.governance.policy import WORKFLOW
from drama_plugin.production import ProductionPackage, ProductionPackageStore
from drama_plugin.providers.mock import MockDramaData
from drama_plugin.runtime import ArtifactReference, RunMode

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
FIXTURE = PROJECT / "artifacts/flagship-literary-film-01/test-shoot-01"
EVIDENCE = PROJECT / "未来架构/迁移/evidence"


def forbidden(*args: Any, **kwargs: Any) -> Any:
    raise AssertionError("No network, Provider, Prompt or formal writes in T3 shadow")


async def shadow() -> dict[str, Any]:
    context = FIXTURE / "S02-cinematic/K02-context.json"
    original_root = FIXTURE / "S02-design"
    package_file = EVIDENCE / "T2-S02-K02-ProductionPackage.json"
    hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    paths = [context, package_file, *sorted(original_root.glob("*.json"))]
    original_hashes = {str(p): hashfile(p) for p in paths}
    old = ProductionPackage.model_validate_json(package_file.read_text())
    cases = []
    for name in ("fresh", "stale-owner-version-fixture", "missing-optional-lighting",
                 "wrong-shot-scope", "capability-absent-fixture", "production-quality-review"):
        raw = json.loads(context.read_text())
        data = MockDramaData.empty()
        for field, model in (("work",Work),("script",Script),("episode",Episode),("scene",Scene),("shot",Shot)):
            setattr(data, field, model.model_validate(raw[field]))
        assert data.work is not None and data.scene is not None and data.shot is not None
        with tempfile.TemporaryDirectory(prefix="t3-shadow-") as temporary:
            root = original_root
            if name in {"stale-owner-version-fixture", "missing-optional-lighting"}:
                root = Path(temporary)
                for path in original_root.glob("*.json"):
                    shutil.copyfile(path, root / path.name)
                if name == "stale-owner-version-fixture":
                    body = json.loads((root / "cinematography.json").read_text())
                    body["version"] += 1  # Controlled legal-owner version, not a live Canon revision.
                    (root / "cinematography.json").write_text(json.dumps(body,ensure_ascii=False))
                    data.shot.content["departmentRefs"]["cinematography"]["fingerprint"] = sha256_canonical(body)
                else:
                    (root / "lighting-design.json").unlink()
            mode = RunMode.PRODUCTION if name == "production-quality-review" else RunMode.EXPERIMENT
            store = ProductionPackageStore()
            # Production comparison uses its own T2 assembly, preserving the mode contract.
            reference = store.put(old) if mode == RunMode.EXPERIMENT else None
            before = {n:dump_contract(getattr(data,n)) for n in ("work","scene","shot","script","episode")}
            with patch("drama_plugin.plugin.load_config",return_value=DramaPluginConfig()), \
                 patch.object(socket.socket,"connect",forbidden),patch.object(socket.socket,"connect_ex",forbidden), \
                 patch("drama_plugin.professional.compile_prompt_projection",forbidden), \
                 patch("drama_plugin.hosts.cinematic_projection.project",forbidden):
                async with DramaPlugin.load(ROOT,mock_data=data,production_artifact_roots=(root,),
                        production_package_store=store) as plugin:
                    additional = ()
                    scope_shot = "wrong-shot-fixture" if name == "wrong-shot-scope" else data.shot.id
                    from drama_plugin.runtime import RuntimeScope
                    scope = RuntimeScope(work_id=data.work.id,scene_id=data.scene.id,shot_id=scope_shot)
                    if name == "capability-absent-fixture":
                        f = GateFinding.classified(GateCode.CAPABILITY_NOT_IMPLEMENTED,
                            owner="generation-capability-catalog",scope=scope,required=True,
                            evidence_ref=ArtifactReference(owner="offline-capability-fixture",
                                artifact_ref="video-capability-not-implemented"))
                        additional = (plugin.gate_findings.put_finding(f),)
                    elif name == "production-quality-review":
                        f = GateFinding.classified(GateCode.QUALITY_COVERAGE_RISK,
                            owner="creative-review",scope=scope,required=True,
                            evidence_ref=ArtifactReference(owner="offline-quality-fixture",artifact_ref="delivery-quality-review"))
                        additional = (plugin.gate_findings.put_finding(f),)
                    run = plugin.create_governed_run(work_id=data.work.id,scene_id=data.scene.id,shot_id=scope_shot,
                        mode=mode,run_id="t3-"+name,package_ref=reference,finding_refs=additional)
                    calls,decisions = [],[]
                    execute = plugin.runtime.executor.execute
                    async def observed(key: str, inputs: Any) -> Any:
                        calls.append(key)
                        result = await execute(key,inputs)
                        if result.artifact_refs and result.artifact_refs[0].owner == "gate-decision":
                            d = plugin.gate_findings.decision(result.artifact_refs[0])
                            decisions.append({"decision":d.model_dump(mode="json",by_alias=True),
                                "explanations":plugin.gate_governor.explain(d),
                                "findings":[plugin.gate_findings.finding(r).model_dump(mode="json",by_alias=True) for r in d.finding_refs]})
                        return result
                    with patch.object(plugin.runtime.executor,"execute",observed), \
                         patch.object(plugin.providers.production,"generate_image",forbidden), \
                         patch.object(plugin.providers.production,"generate_video",forbidden):
                        final = await plugin.runtime.run(run.run_id)
                    expected = {"fresh":"SUCCEEDED","stale-owner-version-fixture":"SUCCEEDED",
                        "missing-optional-lighting":"SUCCEEDED","wrong-shot-scope":"BLOCKED",
                        "capability-absent-fixture":"WAITING_EXTERNAL","production-quality-review":"WAITING_EXTERNAL"}[name]
                    assert final.state == expected
                    assert before == {n:dump_contract(getattr(data,n)) for n in before}
                    if name == "stale-owner-version-fixture":
                        assert decisions[0]["decision"]["effect"] == "AUTO_MAINTAIN"
                        assert final.last_result is not None and final.last_result.artifact_refs[0] != reference
                        assert plugin.gate_findings.maintenance_count(run.run_id) == 1
                    if name == "missing-optional-lighting":
                        assert decisions[0]["decision"]["effect"] == "CONTINUE"
                        assert any(f["code"]=="OPTIONAL_SOURCE_MISSING" for f in decisions[0]["findings"])
                    cases.append({"case":name,"controlledFixture":name != "fresh",
                        "temporarySourceCopy":root!=original_root,"calls":calls,"decisions":decisions,
                        "runtime":json.loads(plugin.runtime.serialize(run.run_id)),"canonUnchangedDuringGovernance":True,
                        "maintenanceCount":plugin.gate_findings.maintenance_count(run.run_id)})
    assert original_hashes == {str(p):hashfile(p) for p in paths}
    return {"level":"OFFLINE_REAL_T2_PACKAGE_GATE_GOVERNANCE","actualPackageRef":old.artifact_reference().model_dump(mode="json",by_alias=True),
        "sourceHashes":original_hashes,"cases":cases,"allOriginalFilesUnchanged":True,
        "providerSubmission":0,"paidGenerationCalls":0,"mediaGeneration":0,"formalWrites":0}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path)
    args=parser.parse_args();result=asyncio.run(shadow())
    if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"cases":[{"case":c["case"],"state":c["runtime"]["state"],"maintenance":c["maintenanceCount"]} for c in result["cases"]],
        "providerSubmission":0,"paidGenerationCalls":0,"mediaGeneration":0},ensure_ascii=False,indent=2))
