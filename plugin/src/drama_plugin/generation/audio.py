"""Project authored speech layers/relations. No dialogue writing or serial fallback."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from drama_plugin.generation.contracts import (
    AudioExecutionPlan, ExecutionDiagnostic, GenerationTask, Intelligibility,
    SpeechEvent, SpeechLayer, SpeechRelation,
)
from drama_plugin.generation.sources import SelectedValue, child
from drama_plugin.production.contracts import ProductionPackage, SourceDomain as D
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope


@dataclass(frozen=True)
class AudioAssembly:
    plan: AudioExecutionPlan | None
    diagnostics: tuple[ExecutionDiagnostic, ...]


def package_scope(package: ProductionPackage) -> RuntimeScope:
    return RuntimeScope(work_id=package.scope.work.artifact_ref,
                        scene_id=package.scope.scene.artifact_ref, shot_id=package.scope.shot.artifact_ref)


class AudioPerformanceAssembler:
    role = "ASSEMBLER"
    creative_authority = False

    def assemble(self, package: ProductionPackage, task: GenerationTask,
                 selected: tuple[SelectedValue, ...]) -> AudioAssembly:
        diagnostics: list[ExecutionDiagnostic] = []
        events, relations = [], []
        lines: dict[str, SelectedValue] = {}
        bindings = []
        declarations: list[tuple[SelectedValue, int, dict[str, Any]]] = []
        relation_rows = []
        refs: dict[str, list] = {key: [] for key in ("ambience", "foley", "music", "silence", "mix")}
        delivery: dict[str, list] = {}
        def language(line):
            value, ref = line.value, line.selection.reference
            if value.get("language"):
                return value["language"], child(ref, "language")
            # This historical fixture explicitly attests approved Chinese adapted
            # dialogue. Do not infer production language from Unicode characters.
            if "用户批准的中文改编对白" in value.get("provenance", {}).get("adaptationNote", ""):
                return "中文", child(ref, "provenance", "adaptationNote")
            return None, None
        for item in selected:
            if item.selection.domain != D.SOUND:
                continue
            ref, value = item.selection.reference, item.value
            if ref.owner == "scene" and isinstance(value, dict) and "speakerKey" in value:
                if value["id"] in lines:
                    diagnostics.append(ExecutionDiagnostic(code="DIALOGUE_IDENTITY_MISMATCH", owner="screenplay-dialogue",
                        domain=D.SOUND, source_ref=ref, required=True))
                lines[value["id"]] = item
            elif ref.owner == "shot" and ref.path[-1:] == ("spokenContentBindings",):
                bindings = value
            elif isinstance(value, dict):
                if value.get("line_id"):
                    delivery.setdefault(value["line_id"], []).append(ref)
                declarations.extend((item, i, row) for i, row in enumerate(value.get("audio_events", ())))
                relation_rows.extend((item, i, row) for i, row in enumerate(value.get("audio_relations", ())))
                for field, kind in (("ambience", "ambience"), ("foley", "foley"), ("score_cues", "music"),
                    ("no_music_zones", "silence"), ("silence_design", "silence"),
                    ("foreground_background_relationship", "mix"), ("distance", "mix"), ("acoustic_space", "mix")):
                    if value.get(field):
                        refs[kind].append(child(ref, field))
        for item in selected:
            value = item.value
            if item.selection.domain == D.SOUND and isinstance(value, dict) and value.get("line_id") in lines:
                canonical = lines[value["line_id"]].value
                if value.get("speaker") != canonical["speakerKey"] or value.get("dialogue_text") != canonical["text"]:
                    diagnostics.append(ExecutionDiagnostic(code="DIALOGUE_IDENTITY_MISMATCH", owner="screenplay-dialogue",
                        domain=D.SOUND, source_ref=item.selection.reference, required=True))
        bound_ids = {b.get("spokenContentId") for b in bindings}
        if bound_ids != set(lines):
            diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="screenplay-dialogue",
                domain=D.SOUND, required=True))
        for identity, item in lines.items():
            if not item.value.get("text", "").strip() or not item.value.get("speakerKey"):
                diagnostics.append(ExecutionDiagnostic(code="DIALOGUE_IDENTITY_MISMATCH", owner="screenplay-dialogue",
                    domain=D.SOUND, source_ref=item.selection.reference, required=True))
        try:
            if declarations:
                for item, index, row in declarations:
                    source = child(item.selection.reference, "audio_events", str(index))
                    line_id = row.get("spoken_content_id")
                    if line_id is not None:
                        line = lines.get(line_id)
                        if line is None or row.get("speaker_key") != line.value["speakerKey"]:
                            diagnostics.append(ExecutionDiagnostic(code="DIALOGUE_IDENTITY_MISMATCH", owner="screenplay-dialogue",
                                domain=D.SOUND, source_ref=source, required=True))
                            continue
                        line_ref = line.selection.reference
                        speaker = ArtifactReference(owner="character", artifact_ref=row["speaker_key"])
                        lang, lang_ref = language(line)
                    else:
                        # A texture obligation must exist verbatim in the author record.
                        if not row.get("texture_obligation"):
                            diagnostics.append(ExecutionDiagnostic(code="CREATIVE_SOURCE_INSUFFICIENT", owner="sound-performance",
                                domain=D.SOUND, source_ref=source, required=True))
                            continue
                        line_ref, speaker, lang, lang_ref = child(source, "texture_obligation"), None, None, None
                    events.append(SpeechEvent(event_id=row["event_id"], source_ref=line_ref,
                        spoken_content_id=line_id, speaker_ref=speaker, layer=row["layer"],
                        intelligibility=row["intelligibility"], mix_priority=row["mix_priority"],
                        execution_ref=source, delivery_refs=tuple(delivery.get(line_id, ())),
                        language=lang, language_ref=lang_ref,
                        window_ms=row.get("window_ms")))
                if {e.spoken_content_id for e in events if e.spoken_content_id} != set(lines):
                    diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="sound-performance",
                        domain=D.SOUND, required=True))
                for item, index, row in relation_rows:
                    relations.append(SpeechRelation(**row, source_ref=child(item.selection.reference, "audio_relations", str(index))))
                if len(events) > 1 and not relations:
                    diagnostics.append(ExecutionDiagnostic(code="CREATIVE_SOURCE_INSUFFICIENT", owner="sound-performance",
                        domain=D.SOUND, required=True))
            elif len(lines) == 1 and next(iter(lines.values())).value.get("mustKeep") is True:
                # A single explicitly mustKeep line has no inter-line ordering decision.
                identity, line = next(iter(lines.items()))
                lang, lang_ref = language(line)
                events.append(SpeechEvent(event_id=identity, spoken_content_id=identity,
                    source_ref=line.selection.reference,
                    speaker_ref=ArtifactReference(owner="character", artifact_ref=line.value["speakerKey"]),
                    layer=SpeechLayer.PRIMARY, intelligibility=Intelligibility.MUST_UNDERSTAND,
                    mix_priority=3, execution_ref=child(line.selection.reference, "mustKeep"),
                    language=lang, language_ref=lang_ref,
                    delivery_refs=tuple(delivery.get(identity, ()))))
            elif lines:
                diagnostics.append(ExecutionDiagnostic(code="CREATIVE_SOURCE_INSUFFICIENT" if task.native_audio != "DISABLED" else "OPTIONAL_COVERAGE", owner="screenplay-dialogue",
                    domain=D.SOUND, required=task.native_audio != "DISABLED"))
            if not refs["ambience"]:
                diagnostics.append(ExecutionDiagnostic(code="OPTIONAL_AMBIENCE_MISSING", owner="sound-design",
                    domain=D.SOUND))
            if task.native_audio != "DISABLED" and any(e.spoken_content_id and e.language is None for e in events):
                diagnostics.append(ExecutionDiagnostic(code="EXECUTION_REQUIRED_MISSING", owner="production-language",
                    domain=D.SOUND, required=True))
            if any(d.required for d in diagnostics):
                return AudioAssembly(None, tuple(diagnostics))
            plan = AudioExecutionPlan.seal(source_package_ref=package.artifact_reference(), scope=package_scope(package),
                duration_ms=package.generation_intent.duration_ms, speech_events=tuple(events), relations=tuple(relations),
                ambience_refs=tuple(refs["ambience"]), foley_refs=tuple(refs["foley"]), music_refs=tuple(refs["music"]),
                silence_refs=tuple(refs["silence"]), mix_intent_refs=tuple(refs["mix"]), native_audio_policy=task.native_audio,
                source_roles=("NATIVE_VIDEO_AUDIO", "TTS", "AMBIENCE", "FOLEY", "MUSIC"))
            return AudioAssembly(plan, tuple(diagnostics))
        except (ValidationError, KeyError, TypeError, ValueError):
            diagnostics.append(ExecutionDiagnostic(code="CREATIVE_SOURCE_INSUFFICIENT", owner="sound-performance",
                domain=D.SOUND, required=True))
            return AudioAssembly(None, tuple(diagnostics))
