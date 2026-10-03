"""Production selection and owner admission. No creative writes or provider IO."""
from __future__ import annotations

from pydantic import JsonValue, TypeAdapter
from drama_plugin.config.video_route import VideoRoutePolicy, require_runtime_route
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import DesignBody, Kind, SceneBody
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.dpd.core import fingerprint_dpd
from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.contracts import ExecutionProfile, GenerationTask
from drama_plugin.generation.sources import PackageReader, SelectedValue
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.production.contracts import ProductionPackage, SourceReference
from drama_plugin.professional_design.performance_scope import read_performance_scope
from drama_plugin.providers.video.registry import registry
from drama_plugin.runtime.contracts import ArtifactReference, DecisionCategory, RuntimeScope


def resolve_profile(*, model: str, duration_ms: int, resolution: str, ratio: str,
                    native_audio: bool, policy: VideoRoutePolicy, mode: str = "text_to_video") -> ExecutionProfile:
    spec = registry()["models"][model]
    provider = str(spec["provider"])
    require_runtime_route(provider, model, policy=policy)
    if (duration_ms % 1000 or duration_ms // 1000 not in spec["durations"]
            or resolution not in spec["resolutions"] or ratio not in spec["aspect_ratios"]
            or mode not in spec["input_modes"] or native_audio not in spec["native_audio"]):
        raise ValueError("REQUEST_UNSUPPORTED")
    return ExecutionProfile.model_validate(dict(provider=provider, model=model, vendor_model_id=spec["vendor_model"],
        mode=mode, requested_duration_ms=duration_ms, resolution=resolution, aspect_ratio=ratio,
        native_audio=native_audio, catalog_fingerprint=sha256_canonical(spec), policy_fingerprint=sha256_canonical(policy)))


def object_at(value: object) -> dict[str, JsonValue]:
    checked: JsonValue = TypeAdapter(JsonValue).validate_python(value)
    if not isinstance(checked, dict):
        raise ValueError("OWNER_OBJECT_REQUIRED")
    return checked


class OperationResolver:
    """Reads exact owner facts, receipts and projections at prepare AND dispatch."""
    def __init__(self, versions: CreativeVersionStore, ledger: ProductionLedger, policy: VideoRoutePolicy):
        self.versions, self.ledger, self.policy = versions, ledger, policy

    def read(self, pin: SourcePin) -> dict[str, JsonValue]:
        return object_at(self.versions.objects.read_ref(pin))

    def decision(self, ref: ArtifactReference, *, category: DecisionCategory, scope: RuntimeScope,
                 source_ref: ArtifactReference, terms_hash: str | None = None) -> UserDecisionRecord:
        body, actual_scope, fingerprint = self.ledger.get_artifact("user-decision", ref)
        receipt = UserDecisionRecord.model_validate(body)
        if (receipt.artifact_reference() != ref or receipt.fingerprint != fingerprint or actual_scope != scope
                or receipt.scope != scope or not receipt.accepted or receipt.category != category
                or receipt.source_ref != source_ref or terms_hash is not None and receipt.terms_hash != terms_hash):
            raise ValueError("OWNER_DECISION_MISMATCH")
        return receipt

    def validate(self, package: ProductionPackage, task: GenerationTask, *, require_scope: bool = True) -> None:
        unit, profile, owners = task.unit, task.profile, task.owners
        if unit is None or profile is None or owners is None:
            raise ValueError("OPERATION_INPUTS_MISSING")
        scope = package_scope(package)
        current = resolve_profile(model=profile.model, duration_ms=profile.requested_duration_ms,
            resolution=profile.resolution, ratio=profile.aspect_ratio, native_audio=profile.native_audio,
            policy=self.policy, mode=profile.mode)
        if current != profile:
            raise ValueError("OPERATION_PROFILE_STALE")
        originals = [self.versions.resolve(r) for r in owners.adopted_refs]
        for value in originals:
            from drama_plugin.creative_engine.contracts import scope_contains
            if not scope_contains(value.scope, scope) or self.versions.stale(value.ref()):
                raise ValueError("OPERATION_SCOPE_OR_VERSION_MISMATCH")
            if value.kind != Kind.SOURCE and (value.state != "ADOPTED" or value.adoption_decision_ref != owners.adoption_decision_ref):
                raise ValueError("OPERATION_NOT_ADOPTED")
        scene = next(v for v in originals if v.kind == Kind.SCENE)
        shot = next(v for v in originals if v.kind == Kind.SHOT)
        assert isinstance(scene.body, SceneBody)
        for projected in (package.scope.work, package.scope.scene, package.scope.shot):
            if self.versions.projection(projected.fingerprint).ref() not in owners.adopted_refs:
                raise ValueError("PACKAGE_OWNER_VERSION_MISMATCH")
        declaration = read_performance_scope(self.versions, owners.performance_scope_pin).current()
        if declaration.scope != scope or declaration.scene_ref != scene.ref() or declaration.shot_ref != shot.ref():
            raise ValueError("PERFORMANCE_SCOPE_MISMATCH")
        performance = self.versions.resolve(declaration.performance_ref)
        assert isinstance(performance.body, DesignBody)
        beats = performance.body.facts.get("beats")
        if not isinstance(beats, list) or not set(unit.beat_ids) <= {object_at(b)["id"] for b in beats}:
            raise ValueError("PERFORMANCE_BEAT_MISMATCH")
        dpd = self.read(owners.dpd_pin)
        if (dpd["scope"] != scope.model_dump(mode="json", by_alias=True)
                or dpd["sceneRef"] != scene.ref().model_dump(mode="json", by_alias=True)
                or dpd["shotRef"] != shot.ref().model_dump(mode="json", by_alias=True)
                or dpd["projectionScopePin"] != owners.performance_scope_pin.model_dump(mode="json", by_alias=True)
                or object_at(dpd["fullShotDPDCoverage"])["status"] != "PASS"):
            raise ValueError("DPD_BINDING_MISMATCH")
        rows = dpd["snapshotBindings"]
        if not isinstance(rows, list) or {sha256_canonical(object_at(r)["snapshotPin"]) for r in rows} != {sha256_canonical(p) for p in owners.snapshot_pins}:
            raise ValueError("DPD_SNAPSHOT_INVENTORY_MISMATCH")
        for pin in owners.snapshot_pins:
            snapshot = DPDSnapshot.model_validate(self.read(pin))
            if snapshot.fingerprint != fingerprint_dpd(snapshot) or snapshot.scene.scene_id != scope.scene_id:
                raise ValueError("DPD_SNAPSHOT_MISMATCH")
            line = next((x for x in scene.body.dialogue if x.id == snapshot.line.spoken_content_id), None)
            row = next(object_at(r) for r in rows if object_at(r)["snapshotPin"] == pin.model_dump(mode="json", by_alias=True))
            if line is None or sha256_canonical(line) != row["canonicalDialogueHash"] or line.speaker != snapshot.line.speaker:
                raise ValueError("DPD_CANON_DIALOGUE_MISMATCH")
        if not set(unit.spoken_ids) <= {line.id for line in scene.body.dialogue}:
            raise ValueError("UNIT_DIALOGUE_MISMATCH")
        rights = self.read(owners.rights_pin)
        expected = [r.model_dump(mode="json", by_alias=True) for r in owners.adopted_refs
                    if self.versions.resolve(r).kind != Kind.PROFESSIONAL]
        if (rights["scope"] != scope.model_dump(mode="json", by_alias=True) or rights["adoptedRefs"] != expected
                or rights.get("externalProcessingAuthorized") is not True
                or rights["sourceRef"] != next(r for r in expected if str(r["identity"]).startswith("creative-source:"))
                or rights["creativeAdoptionDecisionRef"] != owners.adoption_decision_ref.model_dump(mode="json",by_alias=True)
                or rights["dpdBindingRef"] != {"owner":"dpd-core","artifactRef":"dpd-binding:"+owners.dpd_pin.fingerprint,"version":1}
                or rights["requestRef"] != owners.rights_request_ref.model_dump(mode="json", by_alias=True)
                or rights["decisionRef"] != owners.rights_decision_ref.model_dump(mode="json", by_alias=True)):
            raise ValueError("RIGHTS_SCOPE_OR_VERSION_MISMATCH")
        self.decision(owners.rights_decision_ref, category=DecisionCategory.ADOPTION, scope=scope,
            source_ref=owners.rights_request_ref)
        processing = object_at(rights["processingScope"])
        if any(processing[key] != value for key, value in {
                "purpose": "MINIMAL_CONTROLLED_LIVE_TECHNICAL_PROOF",
                "material": "necessary Source-derived / Canon-derived information of exact adopted Shot",
                "providerModelAuthority": "CURRENT_B1_REQUALIFICATION",
                "durationSeconds": profile.requested_duration_ms / 1000, "resolution": profile.resolution,
                "aspectRatio": profile.aspect_ratio, "mode": profile.mode, "maxLogicalVideoOperations": 1,
                "paidReferences": 0, "paidRetries": 0}.items()):
            raise ValueError("RIGHTS_PROCESSING_LIMIT")
        if require_scope:
            if unit.scope_decision_ref is None:
                raise ValueError("UNIT_SCOPE_DECISION_REQUIRED")
            self.decision(unit.scope_decision_ref, category=DecisionCategory.ART_APPROVAL, scope=scope,
                source_ref=package.artifact_reference(), terms_hash=unit.terms_hash(package.artifact_reference()))

    async def selected(self, package: ProductionPackage, task: GenerationTask, reader: PackageReader) -> tuple[SelectedValue, ...]:
        self.validate(package, task, require_scope=False)
        unit = task.unit
        assert unit
        full = await reader.selections(package)
        permitted = {item.selection.reference for item in full}
        def allowed(ref: SourceReference) -> bool:
            return any((parent.owner, parent.artifact_ref, parent.version, parent.fingerprint) ==
                (ref.owner, ref.artifact_ref, ref.version, ref.fingerprint) and ref.path[:len(parent.path)] == parent.path
                for parent in permitted)
        refs = (*unit.action_refs, unit.start_ref, unit.end_ref, *(d.reference for d in unit.fact_refs))
        if any(not allowed(r) for r in refs):
            raise ValueError("UNIT_SOURCE_OUTSIDE_PACKAGE")
        finite = {"ACTION": {"actionPhases", "physicalStateConstraints"},
            "PERFORMANCE": {"beats", "physicalExpression"}, "CAMERA": {"movement", "cameraPosition", "height", "pointOfView", "lensIntention", "axisAndScreenDirection"},
            "WORLD": {"setting", "weather", "time", "physicalWorldRules"},
            "SUBJECTS": {"presentSubjects", "identityConstraints", "absences"},
            "SOUND": {"ambience", "contactTiedSound", "dialogueAndLegibility", "orderingRules", "silence", "acousticSpace"},
            "LIGHTING": {"sources", "directionAndQuality", "intensityRatios", "constraints", "nightContinuity"},
            "COLOR": {"scenePalette", "arc", "constraints"}, "EDITORIAL": {"compression", "temporalStructure", "protectedEvents", "spatialOrientation"},
            "REFERENCE": {"references"}}
        for fact in unit.fact_refs:
            ref = fact.reference
            if ref.owner == "professional" and (len(ref.path) < 2 or ref.path[0] != "content"
                    or ref.path[1] not in finite.get(fact.domain.value, set())):
                raise ValueError("UNIT_FIELD_NOT_EXECUTABLE")
            if ref.owner == "scene" and (fact.domain != "SOUND" or not isinstance(await reader.resolver.resolve(ref), dict)):
                raise ValueError("UNIT_CANON_FIELD_NOT_EXECUTABLE")
        reference_rows = [object_at(r) for item in full if item.selection.domain == "REFERENCE"
            and isinstance(item.value, dict) for r in item.value.get("references", [])]
        dispositions = dict(unit.reference_disposition)
        if len(dispositions) != len(unit.reference_disposition) or set(dispositions) != {str(r["id"]) for r in reference_rows}:
            raise ValueError("REFERENCE_DUTY_DISPOSITION_REQUIRED")
        if any(value == "INPUT" for value in dispositions.values()) and not any(
                item.selection.reference.artifact_ref.startswith("reference-execution-binding:") for item in full):
            raise ValueError("REFERENCE_INPUT_UNRESOLVED")
        self.validate(package, task)
        # Every explicit path is read from the immutable selected owner, never a model string.
        return tuple([SelectedValue(d, await reader.resolver.resolve(d.reference)) for d in unit.fact_refs])
