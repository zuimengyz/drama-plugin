"""Production selection and owner admission. No creative writes or provider IO."""
from __future__ import annotations

from pydantic import JsonValue, TypeAdapter
from drama_plugin.config.video_route import VideoRoutePolicy, require_runtime_route
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, SceneDPD, BeatDPD, LineDPD
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import DesignBody, Kind, SceneBody, ShotBody, VersionRef, CreativeVersion, Authority, scope_contains
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.dpd.core import fingerprint_dpd, compose_dpd
from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.contracts import ExecutionProfile, GenerationTask, OperationSelection, OwnerBindings
from drama_plugin.generation.sources import PackageReader, SelectedValue
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.persistence.review import UserDecisionRecord
from drama_plugin.production.contracts import ProductionPackage, SourceReference, DomainReference, SourceDomain
from drama_plugin.professional_design.performance_scope import (read_performance_scope, retain_performance_scope,
    PerformanceProjectionScope, ProjectionEvidence, SubjectProjection)
from drama_plugin.performance_coverage import validate_shot_dpd_coverage
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


def continuation_context(unit: OperationSelection, previous: OperationSelection) -> tuple[DomainReference, ...]:
    """Shared whole-shot setup remains context, rather than a repeated per-clip event."""
    contextual = {"CAMERA": {"movement", "cameraPosition", "lensIntention", "pointOfView"},
        "EDITORIAL": {"temporalStructure", "spatialOrientation", "protectedEvents"}, "COLOR": {"arc"}}
    return tuple(f for f in unit.fact_refs if f in previous.fact_refs and
        any(key in f.reference.path for key in contextual.get(f.domain, set())))


def continuation_frame(ledger: ProductionLedger, ref: ArtifactReference, *, allow_unverified_audio: bool = False):
    """Validate native last-frame provenance through its exact successful task."""
    from drama_plugin.execution.store import ExecutionStore
    from drama_plugin.execution.contracts import ContinuationFrame, MediaBinding, ExecutionOperation, ProviderReceipt, CreativeMediaReview
    from drama_plugin.generation.contracts import GenerationPreparation
    store = ExecutionStore(ledger)
    frame = store.get(ref, ContinuationFrame)
    source = store.get(frame.predecessor_media_ref, MediaBinding)
    receipt = store.get(frame.receipt_ref, ProviderReceipt)
    original = store.get(source.receipt_ref, ProviderReceipt)
    op = store.get(source.operation_ref, ExecutionOperation)
    review_ref = store.checkpoint(source.operation_ref).progress.video_creative_ref
    review = store.get(review_ref, CreativeMediaReview) if review_ref else None
    if (review is None or review.outcome != 'PASS' or review.operation_ref != source.operation_ref
            or review.media != source.media or review.scope != source.scope):
        raise ValueError('REVIEWED_CONTINUATION_PREDECESSOR_REQUIRED')
    if (not receipt.last_frame_url or receipt.state != "SUCCEEDED" or receipt.result is None
            or receipt.remote_identity != source.provider_result_id
            or receipt.attempt_ref != source.attempt_ref or receipt.operation_ref != source.operation_ref
            or original.remote_identity != receipt.remote_identity
            or frame.run_id != source.run_id or frame.scope != source.scope
            or frame.source_package_ref != source.source_package_ref):
        raise ValueError("PROVIDER_LAST_FRAME_PROVENANCE_MISMATCH")
    previous = ledger.get_artifact('generation-preparation', op.preparation_ref)[0]
    previous_task = GenerationPreparation.model_validate(previous).task
    validate_predecessor_speech(previous_task.unit,review.observations,allow_unverified_audio=allow_unverified_audio)
    return frame, source, receipt, previous_task


def validate_observed_speech(unit: OperationSelection, observations) -> None:
    if unit.spoken_ids:
        verified = {identity for row in observations for identity in (row.verified_spoken_ids or ())}
        if verified != set(unit.spoken_ids):
            raise ValueError('CONTINUATION_SPEECH_COMPLETION_UNVERIFIED')


def validate_predecessor_speech(unit: OperationSelection, observations, *, allow_unverified_audio: bool = False) -> None:
    try:
        validate_observed_speech(unit,observations)
    except ValueError:
        if not (allow_unverified_audio and any(row.code == 'SPOKEN_CONTENT_COVERAGE_UNVERIFIED'
                for row in observations) and not any(row.code in {'SPOKEN_CONTENT_MISSING','SPOKEN_CONTENT_REPEATED'}
                for row in observations)):
            raise


def validate_segment_progress(unit: OperationSelection, predecessors: tuple[OperationSelection, ...]) -> None:
    """Predecessors are newest first; IDs track assigned work, not audio QA claims."""
    seen_actions, seen_spoken = set(unit.action_refs), set(unit.spoken_ids)
    def phase(selection):
        ref = selection.action_refs[0]
        if (len(selection.action_refs) != 1 or len(ref.path) < 3
                or ref.path[-3] != 'actionPhases' or ref.path[-1] != 'action' or not ref.path[-2].isdigit()):
            raise ValueError('CONTINUATION_PHASE_CONTRACT_REQUIRED')
        return (ref.owner,ref.artifact_ref,ref.version,ref.fingerprint,ref.path[:-2]), int(ref.path[-2])
    key, index = phase(unit)
    for previous in predecessors:
        previous_key, previous_index = phase(previous)
        if key != previous_key or index != previous_index + 1:
            raise ValueError('CONTINUATION_PROGRESS_REPEAT_OR_SKIP')
        if seen_actions.intersection(previous.action_refs) or seen_spoken.intersection(previous.spoken_ids):
            raise ValueError('CONTINUATION_CONTENT_OVERLAP')
        seen_actions.update(previous.action_refs); seen_spoken.update(previous.spoken_ids)
        index = previous_index


def validate_continuation(ledger: ProductionLedger, task: GenerationTask) -> None:
    if task.continuation is None:
        return
    c = task.continuation
    frame, source, _, previous = continuation_frame(ledger, c.frame_ref,allow_unverified_audio=bool(c.allow_unverified_audio))
    if frame.predecessor_media_ref != c.predecessor_media_ref or not task.unit or not previous.unit:
        raise ValueError("CONTINUATION_PREDECESSOR_MISMATCH")
    if c.context_fact_refs != continuation_context(task.unit, previous.unit):
        raise ValueError("CONTINUATION_CONTEXT_DRIFT")
    predecessors = []
    for _ in range(3):
        predecessors.append(previous.unit)
        if previous.continuation is None:
            break
        if previous.continuation.global_reference_ref != c.global_reference_ref:
            raise ValueError("CONTINUATION_GLOBAL_REFERENCE_DRIFT")
        _, source, _, previous = continuation_frame(ledger, previous.continuation.frame_ref,
            allow_unverified_audio=bool(previous.continuation.allow_unverified_audio))
    else:
        raise ValueError("BOUNDED_SCENE_CONTINUATION_REQUIRED")
    validate_segment_progress(task.unit, tuple(predecessors))
    from drama_plugin.production.references import ReferenceExecutionBinding
    global_ref = c.global_reference_ref
    global_body, _, _ = ledger.get_artifact('reference-execution-binding',
        ArtifactReference(owner=global_ref.owner.value, artifact_ref=global_ref.artifact_ref, version=global_ref.version))
    global_binding = ReferenceExecutionBinding.model_validate(global_body)
    if (global_binding.source().reference() != global_ref or global_binding.scope != frame.scope
            or global_binding.media.kind != 'video' or global_binding.media.content_hash != source.media.content_hash):
        raise ValueError('CONTINUATION_GLOBAL_REFERENCE_MISMATCH')
    ref = task.execution_reference_refs[0]
    body, _, _ = ledger.get_artifact('reference-execution-binding',
        ArtifactReference(owner=ref.owner.value, artifact_ref=ref.artifact_ref, version=ref.version))
    binding = ReferenceExecutionBinding.model_validate(body)
    if (binding.source().reference() != ref or binding.endpoint_frame_ref != c.frame_ref
            or binding.role != 'FIRST_FRAME' or binding.media.content_hash != frame.media.content_hash
            or binding.media.media_id != frame.media.media_id or binding.scope != source.scope):
        raise ValueError("CONTINUATION_FIRST_FRAME_MISMATCH")


class OperationResolver:
    """Reads exact owner facts, receipts and projections at prepare AND dispatch."""
    def __init__(self, versions: CreativeVersionStore, ledger: ProductionLedger, policy: VideoRoutePolicy):
        self.versions, self.ledger, self.policy = versions, ledger, policy

    def read(self, pin: SourcePin) -> dict[str, JsonValue]:
        return object_at(self.versions.objects.read_ref(pin))

    def camera_direction(self, package: ProductionPackage, task: GenerationTask):
        from drama_plugin.generation.contracts import CameraExecutionDirection, CameraPhaseTiming
        from drama_plugin.creative_engine.sources import NativeCreativeSources
        if task.camera_direction_ref is None:
            return None
        raw, scope, digest = self.ledger.get_artifact(CameraExecutionDirection.owner, task.camera_direction_ref)
        binding = CameraExecutionDirection.model_validate(raw)
        if (binding.artifact_reference() != task.camera_direction_ref or binding.fingerprint != digest
                or binding.scope != scope or scope != package_scope(package)
                or binding.source_package_ref != package.artifact_reference()
                or binding.selection_hash != sha256_canonical(task.unit)):
            raise ValueError('CAMERA_DIRECTION_SCOPE_MISMATCH')
        camera = self.versions.resolve(binding.camera_ref)
        core = tuple(r for r in task.owners.adopted_refs if self.versions.resolve(r).kind != Kind.PROFESSIONAL)
        if (camera.kind != Kind.PROFESSIONAL or camera.scope != scope or camera.state != 'REVIEWED'
                or not isinstance(camera.body, DesignBody) or camera.body.domain != 'CAMERA'
                or set(camera.source_refs) != set(core)):
            raise ValueError('CAMERA_DIRECTION_OWNER_MISMATCH')
        self.decision(binding.approval_ref,category=DecisionCategory.ART_APPROVAL,scope=scope,
            source_ref=camera.ref().runtime_ref(),
            terms_hash=sha256_canonical([v.model_dump(mode='json',by_alias=True) for v in (package.artifact_reference(),task.unit,camera.ref())]),allow_parent_scope=True)
        rows = tuple(CameraPhaseTiming.model_validate(v) for v in camera.body.facts['movement']['phaseDirections'])
        phase = int(task.unit.action_refs[0].path[-2])
        selected = [(i, row) for i, row in enumerate(rows) if row.phase_index == phase]
        if len(selected) != 1 or len({row.phase_index for row in rows}) != len(rows):
            raise ValueError('CAMERA_DIRECTION_PHASE_MISMATCH')
        i, timing = selected[0]
        source = NativeCreativeSources(self.versions,core).project(camera).reference('content','movement','phaseDirections',str(i))
        return timing, source

    def decision(self, ref: ArtifactReference, *, category: DecisionCategory, scope: RuntimeScope,
                 source_ref: ArtifactReference, terms_hash: str | None = None, allow_parent_scope: bool = False) -> UserDecisionRecord:
        body, actual_scope, fingerprint = self.ledger.get_artifact("user-decision", ref)
        receipt = UserDecisionRecord.model_validate(body)
        if (receipt.artifact_reference() != ref or receipt.fingerprint != fingerprint
                or (not scope_contains(actual_scope, scope) if allow_parent_scope else actual_scope != scope)
                or receipt.scope != actual_scope or not receipt.accepted or receipt.category != category
                or receipt.source_ref != source_ref or terms_hash is not None and receipt.terms_hash != terms_hash):
            raise ValueError("OWNER_DECISION_MISMATCH")
        return receipt

    def validate_independent_adoption(self, value: CreativeVersion, scope: RuntimeScope) -> None:
        """A partial owner revision retains its own exact adopted-candidate receipt."""
        from drama_plugin.creative_engine.contracts import CreativeCheckpoint
        from drama_plugin.film.contracts import FilmPlan
        if value.adoption_decision_ref is None or value.candidate_origin_ref is None:
            raise ValueError("OPERATION_NOT_ADOPTED")
        body,actual_scope,fingerprint=self.ledger.get_artifact("user-decision",value.adoption_decision_ref)
        receipt=UserDecisionRecord.model_validate(body)
        if (receipt.artifact_reference()!=value.adoption_decision_ref or receipt.fingerprint!=fingerprint or not receipt.accepted
                or receipt.category!=DecisionCategory.ADOPTION or actual_scope!=receipt.scope or not scope_contains(receipt.scope,scope)):
            raise ValueError("PROFESSIONAL_ADOPTION_DECISION_MISMATCH")
        if receipt.source_ref is None:
            raise ValueError("PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH")
        if receipt.source_ref.owner=="creative-candidate":
            checkpoint=CreativeCheckpoint.model_validate(self.ledger.get_index("creative-checkpoint",receipt.run_id))
            refs=checkpoint.candidate_version_refs
            candidate=ArtifactReference(owner="creative-candidate",artifact_ref="creative-candidate:"+sha256_canonical(
                [ref.model_dump(mode="json",by_alias=True) for ref in refs]),version=1)
            if checkpoint.candidate_ref!=receipt.source_ref or candidate!=receipt.source_ref or value.candidate_origin_ref not in refs:
                raise ValueError("PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH")
        elif receipt.source_ref.owner=="film-plan":
            raw,plan_scope,plan_fingerprint=self.ledger.get_artifact("film-plan",receipt.source_ref)
            plan=FilmPlan.model_validate(raw)
            if (plan.artifact_reference()!=receipt.source_ref or plan.fingerprint!=plan_fingerprint or plan.scope!=plan_scope
                    or plan.scope!=receipt.scope or plan.run_id!=receipt.run_id
                    or value.candidate_origin_ref not in {ref for group in plan.unit_version_refs for ref in group}):
                raise ValueError("PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH")
        else:
            raise ValueError("PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH")
        original=self.versions.resolve(value.candidate_origin_ref)
        if original.authority!=value.authority or original.kind!=value.kind or original.scope!=value.scope or original.body!=value.body:
            raise ValueError("PROFESSIONAL_ADOPTION_CANDIDATE_MISMATCH")

    def validate(self, package: ProductionPackage, task: GenerationTask, *, require_scope: bool = True, require_current_profile: bool = True) -> None:
        unit, profile, owners = task.unit, task.profile, task.owners
        if unit is None or profile is None or owners is None:
            raise ValueError("OPERATION_INPUTS_MISSING")
        scope = package_scope(package)
        self.camera_direction(package,task)
        if require_current_profile:
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
            if value.kind != Kind.SOURCE:
                if value.state != "ADOPTED" or value.adoption_decision_ref is None:
                    raise ValueError("OPERATION_NOT_ADOPTED")
                if value.kind == Kind.SHOT and value.adoption_decision_ref != owners.adoption_decision_ref:
                    raise ValueError("OPERATION_NOT_ADOPTED")
                if value.adoption_decision_ref != owners.adoption_decision_ref:
                    self.validate_independent_adoption(value,scope)
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
        if "beatBindings" in dpd:
            snapshots = {snapshot.line.spoken_content_id: snapshot for pin in owners.snapshot_pins for snapshot in (DPDSnapshot.model_validate(self.read(pin)),)}
            bound_beats = {b.beat_id: b for raw in TypeAdapter(list[JsonValue]).validate_python(dpd["beatBindings"]) for b in (BeatDPD.model_validate(raw),)}
            validate_shot_dpd_coverage(projection_scope=read_performance_scope(self.versions, owners.performance_scope_pin), snapshots=snapshots, beats=bound_beats)
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
            source_ref=owners.rights_request_ref, allow_parent_scope=True)
        processing = object_at(rights["processingScope"])
        if any(processing[key] != value for key, value in {
                "durationSeconds": profile.requested_duration_ms / 1000, "resolution": profile.resolution,
                "aspectRatio": profile.aspect_ratio, "mode": profile.mode, "maxLogicalVideoOperations": 1,
                "paidReferences": 0, "paidRetries": 0}.items()):
            raise ValueError("RIGHTS_PROCESSING_LIMIT")
        if "profile" in rights and rights["profile"] != profile.model_dump(mode="json", by_alias=True):
            raise ValueError("RIGHTS_EXECUTION_PROFILE_MISMATCH")
        if require_scope and any(value == "TECHNICAL_RISK_ACCEPTED" for _, value in unit.reference_disposition):
            if unit.scope_decision_ref is None:
                raise ValueError("UNIT_SCOPE_DECISION_REQUIRED")
            self.decision(unit.scope_decision_ref, category=DecisionCategory.ART_APPROVAL, scope=scope,
                source_ref=package.artifact_reference(), terms_hash=unit.terms_hash(package.artifact_reference()), allow_parent_scope=True)

    def compose_performance(self, refs: tuple[VersionRef, ...]) -> tuple[SourcePin, SourcePin, tuple[SourcePin, ...]]:
        originals = [self.versions.resolve(ref) for ref in refs]
        scene = next(v for v in originals if v.kind == Kind.SCENE)
        shot = next(v for v in originals if v.kind == Kind.SHOT)
        performance = next((v for v in originals if v.kind == Kind.PROFESSIONAL and
            isinstance(v.body, DesignBody) and v.body.domain == "PERFORMANCE"), None)
        if performance is None or not isinstance(scene.body, SceneBody) or not isinstance(shot.body, ShotBody):
            raise ValueError("NATIVE_PERFORMANCE_CAPABILITY_ABSENT")
        assert isinstance(performance.body, DesignBody)
        if any(v.state != "ADOPTED" for v in (scene, shot, performance)) or shot.adoption_decision_ref is None:
            raise ValueError("DPD_INPUT_NOT_ADOPTED")
        facts = performance.body.facts
        subject_rows, beat_rows = facts.get("projectionSubjects"), facts.get("beats")
        if not isinstance(subject_rows, list) or not isinstance(beat_rows, list):
            raise ValueError("NATIVE_PERFORMANCE_CONTRACT_MISSING")
        subjects = tuple(SubjectProjection.model_validate(row) for row in subject_rows)
        evidence = [ProjectionEvidence(field_path=("projectionSubjects",), value_hash=sha256_canonical(subject_rows))]
        for index, row in enumerate(beat_rows):
            value = object_at(row)
            if any(s.role == "NON_INTERACTIVE_DESTINATION" and value.get("id") in s.beat_ids for s in subjects):
                for key in ("note", "objective", "obstacle", "tactic", "target"):
                    evidence.append(ProjectionEvidence(field_path=("beats", str(index), key), value_hash=sha256_canonical(value[key])))
        declaration = PerformanceProjectionScope(scope=shot.scope, performance_ref=performance.ref(),
            scene_ref=scene.ref(), shot_ref=shot.ref(), adoption_decision_ref=shot.adoption_decision_ref,
            evidence=tuple(evidence), subjects=subjects)
        scope_pin = retain_performance_scope(self.versions, declaration, writer=Authority.PROFESSIONAL)
        scene_dpd = SceneDPD.model_validate({**object_at(facts["sceneDPD"]), "sceneId": shot.scope.scene_id,
            "sourceFingerprint": sha256_canonical(scene.body)})
        beats: dict[str, BeatDPD] = {}
        for row in beat_rows:
            value = object_at(row)
            # Infrastructure identifiers come only from the fixed scope and approved Beat id.
            material = {key: val for key, val in value.items() if key in {f.alias or name for name, f in BeatDPD.model_fields.items()}}
            beat = BeatDPD.model_validate({**material, "sceneId": shot.scope.scene_id, "beatId": value["id"]})
            if beat.beat_id in beats:
                raise ValueError("DPD_DUPLICATE_BEAT")
            beats[beat.beat_id] = beat
        dialogue = {line.id: line for line in scene.body.dialogue}
        snapshots: dict[str, DPDSnapshot] = {}
        for row in TypeAdapter(list[JsonValue]).validate_python(facts.get("lines", [])):
            value = object_at(row)
            key = str(value["spokenContentId"])
            if key not in shot.body.spoken_ids or key in snapshots:
                raise ValueError("DPD_CANON_DIALOGUE_MISMATCH")
            line = LineDPD.model_validate({**value, "sceneId": shot.scope.scene_id, "speaker": dialogue[key].speaker})
            snapshots[key] = compose_dpd(scene_dpd, beats[line.beat_id], line)
        coverage = validate_shot_dpd_coverage(projection_scope=read_performance_scope(self.versions, scope_pin), snapshots=snapshots, beats=beats)
        snapshot_rows, snapshot_pins = [], []
        for key, snapshot in sorted(snapshots.items()):
            pin = self.versions.objects.put("dpd-snapshot:"+snapshot.fingerprint, snapshot.model_dump(mode="json", by_alias=True))
            snapshot_pins.append(pin)
            snapshot_rows.append({"snapshotPin": pin.model_dump(mode="json", by_alias=True), "canonicalDialogueHash": sha256_canonical(dialogue[key])})
        body = {"scope": shot.scope.model_dump(mode="json", by_alias=True),
            "sceneRef": scene.ref().model_dump(mode="json", by_alias=True), "shotRef": shot.ref().model_dump(mode="json", by_alias=True),
            "performanceRef": performance.ref().model_dump(mode="json", by_alias=True),
            "projectionScopePin": scope_pin.model_dump(mode="json", by_alias=True), "snapshotBindings": snapshot_rows,
            "beatBindings": [b.model_dump(mode="json", by_alias=True) for b in beats.values()], "fullShotDPDCoverage": coverage}
        dpd_pin = self.versions.objects.put("adopted-dpd-binding:"+sha256_canonical(body), body)
        return dpd_pin, scope_pin, tuple(snapshot_pins)

    async def select_unit(self, package: ProductionPackage, reader: PackageReader, *, phase_index: int = 0) -> OperationSelection:
        selected = await reader.selections(package)
        action = next((v for v in selected if v.selection.domain == "ACTION" and isinstance(v.value, dict) and v.value.get("actionPhases")), None)
        if action is None:
            raise ValueError("NATIVE_OPERATION_UNIT_CAPABILITY_ABSENT")
        if isinstance(phase_index, bool) or not 0 <= phase_index < len(action.value["actionPhases"]):
            raise ValueError("NATIVE_OPERATION_PHASE_OUT_OF_RANGE")
        phase = object_at(action.value["actionPhases"][phase_index])
        if not isinstance(phase.get("beatId"), str) or not isinstance(phase.get("spokenIds"), list):
            raise ValueError("NATIVE_OPERATION_UNIT_CONTRACT_MISSING")
        phase_spoken_ids = TypeAdapter(tuple[str, ...]).validate_python(phase["spokenIds"])
        base = action.selection.reference
        def leaf(ref: SourceReference, *path: str) -> SourceReference:
            return SourceReference.model_validate({**ref.model_dump(), "path": (*ref.path, *path)})
        start, end, action_ref = (leaf(base, "actionPhases", str(phase_index), name) for name in ("entryState", "observable", "action"))
        facts: list[DomainReference] = []
        # Finite approved executable leaves. DPD, provenance and entire JSON are never Prompt prose.
        fields = {"ACTION": {"actionPhases", "physicalStateConstraints"}, "PERFORMANCE": {"beats", "physicalExpression"},
            "CAMERA": {"movement", "cameraPosition", "height", "pointOfView", "lensIntention", "axisAndScreenDirection"},
            "WORLD": {"setting", "weather", "time", "physicalWorldRules"}, "SUBJECTS": {"presentSubjects", "identityConstraints", "absences"},
            "SOUND": {"ambience", "contactTiedSound", "dialogueAndLegibility", "orderingRules", "silence", "acousticSpace"},
            "LIGHTING": {"sources", "directionAndQuality", "intensityRatios", "constraints", "nightContinuity"},
            "COLOR": {"scenePalette", "arc", "constraints"}, "EDITORIAL": {"compression", "temporalStructure", "protectedEvents", "spatialOrientation"}}
        def walk(value: JsonValue, ref: SourceReference, domain: SourceDomain) -> None:
            if isinstance(value, str):
                if not value.strip() or len(value)>3000 or "\n" in value:
                    raise ValueError("UNIT_EXECUTABLE_LEAF_REQUIRED")
                facts.append(DomainReference(domain=domain, reference=ref))
            elif isinstance(value, dict):
                if isinstance(value.get("beatId"), str) and value["beatId"] != phase["beatId"]:
                    return
                if isinstance(value.get("id"), str) and domain == "PERFORMANCE" and value["id"] != phase["beatId"]:
                    return
                for name, child in value.items():
                    if name not in {"id", "beatId", "spokenIds", "actor", "target", "note", "objective", "obstacle", "tactic", "direction", "transitionTrigger"}:
                        walk(child, leaf(ref, name), domain)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    if domain == "ACTION" and "actionPhases" in ref.path and index != phase_index:
                        continue
                    walk(child, leaf(ref, str(index)), domain)
        dispositions = []
        for item in selected:
            if item.selection.domain == "SOUND" and isinstance(item.value,dict) and item.value.get("speechRelations"):
                # Keep authored relations structured; event IDs are not executable prose.
                facts.append(DomainReference(domain=SourceDomain.SOUND,reference=leaf(item.selection.reference,"speechRelations")))
            if item.selection.reference.owner == "scene" and isinstance(item.value, dict) and item.value.get("id") in phase_spoken_ids:
                facts.append(item.selection)
            if item.selection.domain == "REFERENCE" and isinstance(item.value, dict):
                for raw in item.value.get("references", []):
                    row = object_at(raw)
                    beat_ids = row.get("beatIds")
                    applies = not isinstance(beat_ids, list) or phase["beatId"] in beat_ids
                    # Uncertain/relevant duty is one explicit risk choice, never silently erased.
                    dispositions.append((str(row["id"]), "TECHNICAL_RISK_ACCEPTED" if applies and row["priority"] == "REQUIRED" else "OPTIONAL_OMITTED" if applies else "OUT_OF_UNIT"))
            if item.selection.domain not in fields or not isinstance(item.value, dict):
                continue
            for key in fields[item.selection.domain]:
                if key in item.value:
                    walk(TypeAdapter(JsonValue).validate_python(item.value[key]), leaf(item.selection.reference, key), item.selection.domain)
        return OperationSelection.model_validate(dict(beat_ids=(phase["beatId"],), action_refs=(action_ref,), spoken_ids=phase_spoken_ids,
            start_ref=start, end_ref=end, fact_refs=tuple(sorted(set(facts), key=lambda f: (f.domain.value, f.reference.path))), reference_disposition=tuple(dispositions)))

    async def selected(self, package: ProductionPackage, task: GenerationTask, reader: PackageReader) -> tuple[SelectedValue, ...]:
        self.validate(package, task, require_scope=False)
        validate_continuation(self.ledger, task)
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
        if task.continuation:
            action = unit.action_refs[0]
            phase_ref = SourceReference.model_validate({**action.model_dump(), 'path':action.path[:-1]})
            phase = object_at(await reader.resolver.resolve(phase_ref))
            if unit.spoken_ids != tuple(phase['spokenIds']) or unit.beat_ids != (phase['beatId'],):
                raise ValueError('CONTINUATION_AUTHORED_CONTENT_DRIFT')
            if (unit.start_ref.path != (*phase_ref.path,'entryState')
                    or unit.end_ref.path != (*phase_ref.path,'observable')
                    or any((ref.artifact_ref,ref.fingerprint) != (phase_ref.artifact_ref,phase_ref.fingerprint)
                        for ref in (unit.start_ref,unit.end_ref))):
                raise ValueError('CONTINUATION_ENDPOINT_PROGRESS_DRIFT')
            for fact in unit.fact_refs:
                if fact.domain == 'ACTION' and 'actionPhases' in fact.reference.path and fact.reference.path[:-1] != phase_ref.path:
                    raise ValueError('CONTINUATION_ACTION_OVERLAP')
                if fact.reference.owner == 'scene' and object_at(await reader.resolver.resolve(fact.reference))['id'] not in unit.spoken_ids:
                    raise ValueError('CONTINUATION_SPEECH_OVERLAP')
        finite = {"ACTION": {"actionPhases", "physicalStateConstraints"},
            "PERFORMANCE": {"beats", "physicalExpression"}, "CAMERA": {"movement", "cameraPosition", "height", "pointOfView", "lensIntention", "axisAndScreenDirection"},
            "WORLD": {"setting", "weather", "time", "physicalWorldRules"},
            "SUBJECTS": {"presentSubjects", "identityConstraints", "absences"},
            "SOUND": {"ambience", "contactTiedSound", "dialogueAndLegibility", "orderingRules", "silence", "acousticSpace", "speechRelations"},
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
        for row in reference_rows:
            disposition = dispositions[str(row["id"])]
            if row["priority"] == "REQUIRED" and disposition == "OPTIONAL_OMITTED":
                raise ValueError("REFERENCE_REQUIRED_DISPOSITION_INVALID")
            if disposition == "OUT_OF_UNIT":
                beat_ids = row.get("beatIds")
                if not isinstance(beat_ids,list) or not beat_ids or set(unit.beat_ids).intersection(beat_ids):
                    raise ValueError("REFERENCE_OUT_OF_UNIT_UNPROVEN")
        from drama_plugin.production.references import PREFIX, ReferenceExecutionBinding
        bound = []
        for ref in task.execution_reference_refs or ():
            if ref.owner != "professional" or not ref.artifact_ref.startswith(PREFIX) or ref.path:
                raise ValueError("REFERENCE_BINDING_AUTHORITY_REQUIRED")
            value = await reader.resolver.resolve(ref)
            binding = ReferenceExecutionBinding.model_validate(value)
            if binding.scope != package_scope(package) or binding.source().reference() != ref:
                raise ValueError("REFERENCE_BINDING_SCOPE_MISMATCH")
            granted = {(r.owner, r.artifact_ref, r.version, r.fingerprint) for r in permitted}
            if not all((r.owner, r.artifact_ref, r.version, r.fingerprint) in granted for r in binding.authority_refs):
                raise ValueError("REFERENCE_BINDING_OUTSIDE_PACKAGE")
            bound.append(SelectedValue(DomainReference(domain=SourceDomain.REFERENCE, reference=ref), value))
        if any(value == "INPUT" for value in dispositions.values()) and not (bound or any(
                item.selection.reference.artifact_ref.startswith(PREFIX) for item in full)):
            raise ValueError("REFERENCE_INPUT_UNRESOLVED")
        duties = {d.purpose for item in (*bound,*full) if item.selection.reference.artifact_ref.startswith(PREFIX)
            for d in ReferenceExecutionBinding.model_validate(item.value).duties}
        if any(dispositions[str(row['id'])] == 'INPUT' and row.get('inputDuty') not in duties for row in reference_rows):
            raise ValueError('REFERENCE_INPUT_DUTY_UNBOUND')
        self.validate(package, task)
        # Every explicit path is read from the immutable selected owner, never a model string.
        return tuple([SelectedValue(d, await reader.resolver.resolve(d.reference)) for d in unit.fact_refs] + bound)
