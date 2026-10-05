"""Finite leaf selection from Package refs, not a second interpretation of the film."""
from __future__ import annotations

from dataclasses import dataclass

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.generation.audio import package_scope
from drama_plugin.generation.contracts import (
    AudioExecutionPlan, CoverageEntry, CoverageStatus as S, ExecutableFact,
    ExecutionDiagnostic, GenerationTask, Obligation as O, PromptIR,
)
from drama_plugin.generation.sources import PackageReader, SelectedValue, child
from drama_plugin.production.contracts import ProductionPackage, SourceDomain as D, SourceReference
from drama_plugin.production.sources import SourceReadError

# A bounded vocabulary of existing executable fields. Unknown/research/review/
# motivation/history fields never become Prompt material. No Department names.
FIELDS = {
    D.WORLD: (("architectural_language", "environment.architecture", True),
        ("location_identity", "environment.architecture", True), ("topology", "environment.topology", True),
        ("source_visual_basis", "world.environment_rules", True), ("material_palette", "environment.materials", False),
        ("lived_in_state", "environment.props_vehicles", False)),
    D.CAMERA: (("perspective", "camera.perspective", True), ("camera_point_of_view", "camera.framing", True),
        ("camera_movement", "video.camera_motion", True), ("lens_intention", "camera.depth_cues", True),
        ("subject_hierarchy", "camera.framing", False)),
    D.LIGHTING: (("source", "lighting.light_sources", True), ("direction", "lighting.light_sources", True),
        ("intensity_relationship", "lighting.contrast", True), ("contrast", "lighting.contrast", True),
        ("practical_lights", "lighting.light_sources", True), ("day_night_continuity", "lighting.time_of_day", True)),
    D.COLOR: (("scene_palettes", "secondary.color", False),
        ("character_environment_color_relation", "secondary.color", False),
        ("emotional_color_progression", "secondary.color", True)),
    D.PERFORMANCE: (("actor_movements", "video.action_progression", True), ("eye_lines", "video.performance", True),
        ("physical_relations", "blocking.visible_relation", True), ("handoffs", "blocking.contact", True)),
    D.DIRECTION: (("restraint_principles", "preserve.restraint", True),),
    D.EDITORIAL: (("cut_points", "video.end_state", True), ("holds", "preserve.holds", True),
        ("temporal_compression", "preserve.time", True)),
}
SUBJECT_FIELDS = (("apparent_age", "apparent_age", True), ("face_structure", "face", True),
    ("body_proportion", "body_proportions", True), ("hair", "hair", True), ("facial_hair", "beard", True),
    ("skin", "visible_condition", True), ("garment_construction_intent", "costume", True),
    ("materials", "costume", True), ("wear", "visible_condition", True), ("dirt", "visible_condition", False))
ORDER = {D.WORLD: 0, D.REFERENCE: 1, D.SUBJECTS: 2, D.ACTION: 4, D.PERFORMANCE: 5,
         D.CAMERA: 6, D.LIGHTING: 7, D.COLOR: 8, D.EDITORIAL: 9, D.DIRECTION: 10, D.SOUND: 11}


@dataclass(frozen=True)
class PromptProjection:
    ir: PromptIR | None
    internal: tuple[CoverageEntry, ...]
    diagnostics: tuple[ExecutionDiagnostic, ...]
    aliases: tuple[tuple[str, ExecutableFact], ...] = ()


class ExecutionProjection:
    role = "COMPILER"
    creative_authority = False

    def __init__(self, reader: PackageReader):
        self.reader = reader

    async def project(self, package: ProductionPackage, task: GenerationTask, plan: AudioExecutionPlan,
                      selected: tuple[SelectedValue, ...]) -> PromptProjection:
        if task.unit is not None:
            return await self._operation(package, task, selected, plan)
        facts: list[ExecutableFact] = []
        internal, diagnostics, aliases = [], [], []

        def add(domain: D, slot: str, text: object, ref: SourceReference, required: bool = True, subject: str | None = None) -> None:
            if not isinstance(text, str) or not text.strip():
                return
            if "\n" in text or len(text) > 3000:
                diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING" if required else "OPTIONAL_COVERAGE",
                    owner=ref.owner.value, domain=domain, source_ref=ref, required=required))
                return
            identity = "execution:" + sha256_canonical([domain.value, slot, text, ref.model_dump(mode="json"), subject])
            fact = ExecutableFact(fact_id=identity, domain=domain, slot=slot, text=text,
                source_ref=ref, obligation=O.EXECUTION_REQUIRED if required else O.QUALITY_SUPPORTING, subject_id=subject)
            identical = next((f for f in facts if (f.domain, f.slot, f.text, f.subject_id) == (domain, slot, text, subject)), None)
            if identical is not None:
                aliases.append((identical.fact_id, fact))
                if required and identical.obligation == O.QUALITY_SUPPORTING:
                    facts[facts.index(identical)] = identical.model_copy(update={"obligation": O.EXECUTION_REQUIRED})
            else:
                facts.append(fact)

        for item in selected:
            domain, ref, value = item.selection.domain, item.selection.reference, item.value
            before = len(facts)
            if isinstance(value, str):
                slot = {"subjectAction": "video.action_progression", "visualEntryState": "video.start_state",
                        "visualExitState": "video.end_state"}.get(ref.path[-1] if ref.path else "")
                if slot:
                    add(domain, slot, value, ref)
            elif isinstance(value, dict):
                for field, slot, required in FIELDS.get(domain, ()):
                    add(domain, slot, value.get(field), child(ref, field), required)
                if domain == D.SUBJECTS and value.get("character_ref"):
                    for field, slot, required in SUBJECT_FIELDS:
                        add(domain, "subject." + slot, value.get(field), child(ref, field), required, value["character_ref"])
                if domain == D.PERFORMANCE and value.get("physical_state", {}).get("dpdOriginal"):
                    pin = value["physical_state"]["dpdOriginal"]
                    try:
                        dependency, body = self.reader.historical_pin(pin, work_id=package.scope.work.artifact_ref)
                        index = value["physical_state"]["actorBeat"]
                        physical, beat = body["physicalPerformance"][index], body["beats"][index]
                        if (body["scene"]["sceneId"] != package.scope.scene.artifact_ref or
                            beat["beatId"] != value["beat_ref"] or beat["actor"] != value["character_ref"] or
                            physical["beatId"] != beat["beatId"] or physical["actor"] != beat["actor"] or
                            physical["dpdFingerprint"] != sha256_canonical(beat)):
                            diagnostics.append(ExecutionDiagnostic(code="DIALOGUE_IDENTITY_MISMATCH", owner="performance",
                                domain=domain, source_ref=ref, required=True))
                        else:
                            add(domain, "video.performance", physical["visibleDirection"],
                                child(dependency, "physicalPerformance", str(index), "visibleDirection"))
                    except SourceReadError as error:
                        code = "PACKAGE_STALE" if error.code.value == "VERSION_MISMATCH" else "EXECUTION_REQUIRED_MISSING"
                        diagnostics.append(ExecutionDiagnostic(code=code, owner="performance", domain=domain,
                            source_ref=ref, required=True))
                    except (KeyError, IndexError, TypeError):
                        diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="performance",
                            domain=domain, source_ref=ref, required=True))
                if domain == D.REFERENCE and "key" in value:
                    try:
                        dependency, body = self.reader.historical_pin(value, work_id=package.scope.work.artifact_ref)
                        add(domain, "medium", body.get("medium"), child(dependency, "medium"))
                        # Only the selected authored asset's name; never its compiled asset Prompt.
                        for index, asset in enumerate(body.get("assetBible", {}).get("assets", ())):
                            if asset.get("id") == body.get("assetId") and asset.get("characterRef"):
                                add(D.SUBJECTS, "subject.role", asset.get("name"),
                                    child(dependency, "assetBible", "assets", str(index), "name"), subject=asset["characterRef"])
                    except SourceReadError as error:
                        diagnostics.append(ExecutionDiagnostic(code="PACKAGE_STALE" if error.code.value == "VERSION_MISMATCH"
                            else "OPTIONAL_REFERENCE_UNRESOLVED", owner="reference-strategy", domain=domain, source_ref=ref))
                if domain == D.SOUND and task.native_audio != "DISABLED":
                    # Only sound obligations that belong to this Shot's existing execution selection.
                    add(domain, "video.audio_requirements", value.get("ambience"), child(ref, "ambience"), False)
                    add(domain, "video.audio_requirements", value.get("distance"), child(ref, "distance"), False)
                    add(domain, "video.audio_requirements", value.get("foreground_background_relationship"), child(ref, "foreground_background_relationship"))
                    add(domain, "video.audio_requirements", value.get("silence_design"), child(ref, "silence_design"))
                    if value.get("no_music_zones"):
                        for i, zone in enumerate(value["no_music_zones"]):
                            if zone.get("scene") == package.scope.scene.artifact_ref:
                                add(domain, "video.audio_requirements", zone.get("decision"), child(ref, "no_music_zones", str(i), "decision"))
                    if ref.owner == "scene" and value.get("id") in {e.spoken_content_id for e in plan.speech_events}:
                        add(domain, "video.audio_requirements", value["text"], child(ref, "text"), subject=value["speakerKey"])
                        add(D.PERFORMANCE, "video.performance", value.get("performanceIntent"), child(ref, "performanceIntent"))
            if len(facts) == before:
                internal.append(CoverageEntry(fact_id="internal:" + sha256_canonical(ref), domain=domain,
                    source_ref=ref, obligation=O.QUALITY_SUPPORTING, status=S.INTERNAL_ONLY))
        for ref, value in await self.reader.obligation_values(package):
            # Purpose is the source selection lock; requiredTransition is executable.
            if ref.path[-1] == "requiredTransition":
                add(D.ACTION, "video.action_progression", value, ref)
            else:
                internal.append(CoverageEntry(fact_id="internal:" + sha256_canonical(ref), domain=D.DIRECTION,
                    source_ref=ref, obligation=O.QUALITY_SUPPORTING, status=S.INTERNAL_ONLY))
        add(D.DIRECTION, "video.duration", f"镜头规划时长：{package.generation_intent.duration_ms / 1000:g}秒。",
            package.generation_intent.duration_ref)
        if task.native_audio != "DISABLED":
            by_event = {e.event_id: e for e in plan.speech_events}
            # Syntax translation of declared layer/relations; never choose which
            # speaker should dominate, interrupt or overlap.
            for event in plan.speech_events:
                if event.spoken_content_id and len(plan.speech_events) > 1:
                    speaker_ref = event.speaker_ref
                    if speaker_ref is None:
                        raise ValueError("Exact speech requires Scene dialogue and speaker references")
                    layer = {"PRIMARY": "主对白", "SECONDARY": "次对白", "BACKGROUND": "背景人声"}[event.layer.value]
                    priority = {"MUST_UNDERSTAND": "必须听清", "BRIEFLY_CLEAR": "允许短暂听清", "TEXTURE": "作为声音织体"}[event.intelligibility.value]
                    add(D.SOUND, "preserve.audio_layer", f"{speaker_ref.artifact_ref}为{layer}，{priority}。",
                        event.execution_ref)
                elif event.spoken_content_id is None:
                    for item in selected:
                        parent = item.selection.reference
                        ref = event.source_ref
                        if (parent.artifact_ref, parent.fingerprint) == (ref.artifact_ref, ref.fingerprint) and ref.path[:len(parent.path)] == parent.path:
                            value = item.value
                            for segment in ref.path[len(parent.path):]:
                                value = value[int(segment)] if isinstance(value, list) else value[segment]
                            add(D.SOUND, "video.audio_requirements", value, ref)
                            break
            for relation in plan.relations:
                a, b = by_event[relation.event_id], by_event[relation.target_event_id]
                left = a.speaker_ref.artifact_ref if a.speaker_ref else "背景人声"
                right = b.speaker_ref.artifact_ref if b.speaker_ref else "背景人声"
                syntax = {"BEFORE": "先于", "AFTER": "后于", "OVERLAP": "与其重叠",
                          "INTERRUPT": "插入其声场", "CONTINUE_UNDER": "持续在其声音下方", "FADE_BEHIND": "渐弱到其声音之后"}[relation.relation.value]
                add(D.SOUND, "preserve.audio_relation", f"{left}的声音{syntax}{right}的声音。", relation.source_ref)
        slots = {fact.slot for fact in facts}
        for slot, owner, domain in (("video.start_state", "shot-design", D.DIRECTION),
            ("video.end_state", "shot-design", D.DIRECTION), ("video.action_progression", "action-performance", D.ACTION),
            ("video.camera_motion", "camera", D.CAMERA), ("environment.architecture", "environment", D.WORLD)):
            if slot not in slots:
                diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner=owner, domain=domain, required=True))
        for domain in (D.LIGHTING, D.COLOR):
            if not any(f.domain == domain for f in facts):
                diagnostics.append(ExecutionDiagnostic(code="OPTIONAL_COVERAGE", owner=domain.value.lower(), domain=domain))
        if any(d.required for d in diagnostics):
            return PromptProjection(None, tuple(internal), tuple(diagnostics), tuple(aliases))
        # Preserve source temporal order, with space and start state before actions.
        def order(f: ExecutableFact) -> int:
            phase = -1 if f.slot == "video.start_state" else 12 if f.slot == "video.end_state" else ORDER.get(f.domain, 3)
            return phase
        unique = {f.fact_id: f for f in facts}
        ir = PromptIR.seal(source_package_ref=package.artifact_reference(), scope=package_scope(package),
            duration_ms=package.generation_intent.duration_ms, facts=tuple(sorted(unique.values(), key=order)))
        return PromptProjection(ir, tuple(internal), tuple(diagnostics), tuple(aliases))

    async def _operation(self, package: ProductionPackage, task: GenerationTask,
                         selected: tuple[SelectedValue, ...], plan: AudioExecutionPlan) -> PromptProjection:
        """Explicit finite leaf projection, scoped by production selection and receipt."""
        assert task.unit and task.profile
        facts: list[ExecutableFact] = []
        internal: list[CoverageEntry] = []
        diagnostics: list[ExecutionDiagnostic] = []
        slots = {D.ACTION: "video.action_progression", D.PERFORMANCE: "video.performance",
            D.WORLD: "environment.architecture", D.CAMERA: "camera.perspective",
            D.LIGHTING: "lighting.light_sources", D.COLOR: "secondary.color",
            D.EDITORIAL: "preserve.time", D.SOUND: "video.audio_requirements", D.SUBJECTS: "subject.role"}
        def add(domain: D, ref: SourceReference, text: object, slot: str, subject: str | None = None) -> None:
            if not isinstance(text, str) or not text.strip() or len(text) > 3000 or "\n" in text:
                raise ValueError("UNIT_EXECUTABLE_LEAF_REQUIRED")
            facts.append(ExecutableFact(fact_id="execution:" + sha256_canonical([ref.model_dump(mode="json",by_alias=True), slot]), domain=domain,
                slot=slot, text=text, source_ref=ref, obligation=O.EXECUTION_REQUIRED,
                subject_id=subject))
        for item in selected:
            domain, ref = item.selection.domain, item.selection.reference
            if task.return_last_frame and domain == D.EDITORIAL and 'temporalStructure' in ref.path:
                # The adopted whole-Shot runtime remains context. The actual
                # bounded duration comes from the frozen execution profile.
                internal.append(CoverageEntry(fact_id='shot-time-context:'+sha256_canonical(ref),
                    domain=domain,source_ref=ref,obligation=O.QUALITY_SUPPORTING,status=S.INTERNAL_ONLY))
                continue
            if task.continuation and item.selection in task.continuation.context_fact_refs:
                internal.append(CoverageEntry(fact_id="continuation-context:"+sha256_canonical(ref),
                    domain=domain, source_ref=ref, obligation=O.QUALITY_SUPPORTING, status=S.INTERNAL_ONLY))
                continue
            if domain == D.SOUND and ref.path[-1:] == ("speechRelations",):
                internal.append(CoverageEntry(fact_id="speech-relations:"+sha256_canonical(ref),domain=domain,source_ref=ref,
                    obligation=O.EXECUTION_REQUIRED,status=S.INTERNAL_ONLY))
                continue
            if domain == D.SOUND and task.profile.native_audio is False:
                internal.append(CoverageEntry(fact_id="disabled-audio:"+sha256_canonical(ref), domain=domain,source_ref=ref,
                    obligation=O.QUALITY_SUPPORTING,status=S.NOT_APPLICABLE))
                continue
            if domain == D.REFERENCE:
                internal.append(CoverageEntry(fact_id="reference-plan:"+sha256_canonical(ref), domain=domain,
                    source_ref=ref, obligation=O.EXECUTION_REQUIRED, status=S.NOT_APPLICABLE))
                continue
            if domain == D.SOUND and ref.owner == "scene" and isinstance(item.value, dict):
                add(domain, child(ref, "text"), item.value["text"], "video.audio_requirements", str(item.value["speakerKey"]))
                continue
            slot = slots.get(domain)
            if slot is None:
                raise ValueError("UNIT_FIELD_NOT_EXECUTABLE")
            if domain == D.CAMERA and ref.path[-2:] == ("movement", "policy"):
                slot = "video.camera_motion"
            subject = None
            if domain == D.SUBJECTS and "presentSubjects" in ref.path:
                parent = SourceReference(**{**ref.model_dump(), "path": ref.path[:-1] + ("id",)})
                value = await self.reader.resolver.resolve(parent)
                if not isinstance(value, str):
                    raise ValueError("UNIT_SUBJECT_ID_REQUIRED")
                subject = value
            add(domain, ref, item.value, slot, subject)
        for ref, slot in ((task.unit.start_ref, "video.start_state"), (task.unit.end_ref, "video.end_state")):
            add(D.ACTION, ref, await self.reader.resolver.resolve(ref), slot)
        if task.continuation:
            # This physical constraint is derived from the real endpoint binding,
            # independently of the opening camera plan retained as context.
            endpoint = next(i for i in selected if i.selection.reference in task.execution_reference_refs)
            add(D.CAMERA, child(endpoint.selection.reference, "endpointState"),
                endpoint.value['endpointState'], "video.camera_motion")
        for ref in task.unit.action_refs:
            if ref not in {f.source_ref for f in facts}:
                add(D.ACTION, ref, await self.reader.resolver.resolve(ref), "video.action_progression")
        # Preserve every declared reference duty, including unresolved REQUIRED
        # inputs; a bounded technical disposition is backed by its scope receipt.
        dispositions = dict(task.unit.reference_disposition)
        for item in await self.reader.selections(package):
            if item.selection.domain != D.REFERENCE or not isinstance(item.value, dict):
                continue
            for index, row in enumerate(item.value.get("references", [])):
                ref = child(item.selection.reference, "references", str(index))
                disposition = dispositions[row["id"]]
                internal.append(CoverageEntry(fact_id="reference-duty:"+sha256_canonical(ref),
                    domain=D.REFERENCE, source_ref=ref,
                    obligation=O.EXECUTION_REQUIRED if row["priority"] == "REQUIRED" else O.QUALITY_SUPPORTING,
                    status=S.OUT_OF_UNIT if disposition == "OUT_OF_UNIT" else S.OPTIONAL_OMITTED if disposition == "OPTIONAL_OMITTED" else S.INTERNAL_ONLY,
                    input_ref=task.unit.scope_decision_ref))
        by_event = {event.event_id: event for event in plan.speech_events}
        for relation in plan.relations:
            first, second = by_event[relation.event_id], by_event[relation.target_event_id]
            left = first.speaker_ref.artifact_ref if first.speaker_ref else first.event_id
            right = second.speaker_ref.artifact_ref if second.speaker_ref else second.event_id
            syntax = {"BEFORE":"先于", "AFTER":"后于", "OVERLAP":"与其重叠", "INTERRUPT":"插入其声场", "CONTINUE_UNDER":"持续在其声音下方", "FADE_BEHIND":"渐弱到其声音之后"}[relation.relation.value]
            add(D.SOUND,relation.source_ref,f"{left}的声音{syntax}{right}的声音。","preserve.audio_relation")
        selected_refs = {f.source_ref for f in facts}
        for item in await self.reader.selections(package):
            if item.selection.reference not in selected_refs:
                internal.append(CoverageEntry(fact_id="out:"+sha256_canonical(item.selection.reference),
                    domain=item.selection.domain, source_ref=item.selection.reference,
                    obligation=O.QUALITY_SUPPORTING, status=S.OUT_OF_UNIT))
        required = {"video.start_state", "video.end_state", "video.action_progression", "video.camera_motion",
            "environment.architecture", "subject.role", "video.performance", "video.audio_requirements"}
        if task.profile.native_audio is False:
            required.discard("video.audio_requirements")
        if not required <= {f.slot for f in facts}:
            diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="production-selection",
                domain=D.DIRECTION, required=True))
            return PromptProjection(None, tuple(internal), tuple(diagnostics))
        ir = PromptIR.seal(source_package_ref=package.artifact_reference(), scope=package_scope(package),
            duration_ms=task.profile.requested_duration_ms, facts=tuple(facts))
        return PromptProjection(ir, tuple(internal), ())
