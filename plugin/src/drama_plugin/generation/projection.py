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
        facts, internal, diagnostics, aliases = [], [], [], []

        def add(domain: D, slot: str, text, ref: SourceReference, required=True, subject=None):
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
                        dependency, body = self.reader.dependencies.resolve_pin(pin, work_id=package.scope.work.artifact_ref)
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
                        dependency, body = self.reader.dependencies.resolve_pin(value, work_id=package.scope.work.artifact_ref)
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
                    layer = {"PRIMARY": "主对白", "SECONDARY": "次对白", "BACKGROUND": "背景人声"}[event.layer.value]
                    priority = {"MUST_UNDERSTAND": "必须听清", "BRIEFLY_CLEAR": "允许短暂听清", "TEXTURE": "作为声音织体"}[event.intelligibility.value]
                    add(D.SOUND, "preserve.audio_layer", f"{event.speaker_ref.artifact_ref}为{layer}，{priority}。",
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
        def order(f):
            phase = -1 if f.slot == "video.start_state" else 12 if f.slot == "video.end_state" else ORDER.get(f.domain, 3)
            return phase
        unique = {f.fact_id: f for f in facts}
        ir = PromptIR.seal(source_package_ref=package.artifact_reference(), scope=package_scope(package),
            duration_ms=package.generation_intent.duration_ms, facts=tuple(sorted(unique.values(), key=order)))
        return PromptProjection(ir, tuple(internal), tuple(diagnostics), tuple(aliases))
