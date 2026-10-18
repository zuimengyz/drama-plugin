"""Thin structural view of Target IR into the existing sole Seedance2 generator."""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.visual_prompt import VisualPromptIR
from drama_plugin.generation.contracts import AudioExecutionPlan, ExecutionProfile, Obligation, PromptIR
from drama_plugin.prompt_generators.contracts import AudioBinding, ProjectionAnnotations
from drama_plugin.prompt_generators.registry import get_generator
from drama_plugin.prompt_generators.seedance_2.policy import policy
from drama_plugin.providers.video.registry import registry


@dataclass(frozen=True)
class GeneratorPolicy:
    family: str
    version: str
    hard_limit: int
    fingerprint: str
    native_audio: bool


class ModelPolicyCatalog:
    """Read the real adapter capability catalog; no soft target masquerades as a limit."""
    def policy(self, model: str) -> GeneratorPolicy | None:
        return self._policy(model, "t5r-seedance-unit-layout-v9")

    def uses_legacy_unit_scope(self, model: str, fingerprint: str) -> bool:
        """Only exact frozen v5-v8 policies use their original selection algorithm."""
        return any(p is not None and p.fingerprint == fingerprint for p in
            (self._policy(model, f"t5r-seedance-unit-layout-v{version}") for version in range(5, 9)))

    def legacy_scope_policy(self, model: str) -> GeneratorPolicy | None:
        """Exact previous policy for reading frozen preparations, never new compilation."""
        return self._policy(model, "t5r-seedance-unit-layout-v5")

    def legacy_reference_use_policy(self, model: str) -> GeneratorPolicy | None:
        """Frozen v6 used the former blanket reference exclusion."""
        return self._policy(model, "t5r-seedance-unit-layout-v6")

    def _policy(self, model: str, adapter_version: str) -> GeneratorPolicy | None:
        spec = registry()["models"].get(model)
        if spec is None:
            return None
        from drama_plugin.prompt_generators.registry import is_seedance2
        family = "seedance_2" if is_seedance2(model) else spec["provider"]
        try:
            generator = get_generator(family)
        except ValueError:
            return None
        material = {"model": model, "family": family, "generator_version": generator.version,
                    "target_adapter_version": adapter_version,
                    "generator_policy": policy(), "hard_limit": spec["prompt_limit"],
                    "native_audio": spec["native_audio"], "input_modes": spec["input_modes"],
                    "durations": spec["durations"]}
        return GeneratorPolicy(family, generator.version, spec["prompt_limit"], sha256_canonical(material),
                               True in spec["native_audio"])


class SeedanceTargetAdapter:
    """Ephemeral syntax view, not a second IR, package, serializer or stored final prompt."""
    creative_authority = False

    def generate(self, ir: PromptIR, plan: AudioExecutionPlan, *, policy: GeneratorPolicy,
                 input_mode: str, references=(), profile: ExecutionProfile | None = None) -> dict[str, Any]:
        rows, audio, mapping = [], [], {}
        count: dict[str, int] = {}
        subjects = sorted({fact.subject_id for fact in ir.facts if fact.subject_id and fact.domain == "SUBJECTS"})
        # Arrange a native unit as space/time, cast, current action, photography,
        # light/color and sound. Sorting never paraphrases an owner's text or
        # changes the canonical subject-label/input order.
        order = {"WORLD": 0, "SUBJECTS": 1, "REFERENCE": 2, "ACTION": 3,
                 "PERFORMANCE": 4, "CAMERA": 5, "LIGHTING": 6, "COLOR": 7,
                 "EDITORIAL": 8, "DIRECTION": 9, "SOUND": 10}
        def execution_order(fact):
            field = fact.source_ref.path[-1]
            phase = (-1 if field == "entryState" or fact.slot == "video.start_state"
                     else 2 if field == "observable" or fact.slot == "video.end_state" else 0)
            if fact.domain == "WORLD":
                phase = {"time": 0, "setting": 1, "weather": 2, "physicalWorldRules": 3}.get(field, 4)
            elif fact.domain == "SUBJECTS":
                phase = {"identityConstraints": 0, "absences": 1, "role": 2, "inSceneBehaviour": 3}.get(field, 4)
            elif fact.domain == "CAMERA":
                phase = {"pointOfView": 0, "axisAndScreenDirection": 1, "cameraPosition": 2, "height": 3,
                         "lensIntention": 4, "policy": 5, "inheritedState": 6, "decision": 7,
                         "trigger": 8, "motivation": 9, "trajectory": 10, "amplitude": 11, "endState": 12}.get(field, 5)
            return (order.get(fact.domain.value, 9), phase)

        for fact in sorted(ir.facts, key=execution_order):
            slot = fact.slot
            # These finite Action leaves are states/constraints, not extra
            # numbered events. The source fact and coverage receipt stay exact.
            if fact.domain == "ACTION":
                slot = {"entryState": "video.start_state", "observable": "video.end_state",
                        "physicalStateConstraints": "preserve.physical_state"}.get(
                            fact.source_ref.path[-1], slot)
            elif fact.domain == "SUBJECTS" and fact.source_ref.path[-1] == "inSceneBehaviour":
                slot = "subject.current_visible_action"
            elif fact.domain == "WORLD" and fact.source_ref.path[-1] == "time":
                slot = "world.time_of_day"
            elif fact.domain == "LIGHTING" and fact.source_ref.path[-1] == "nightContinuity":
                slot = "lighting.time_of_day"
            if slot.startswith("subject.") and fact.subject_id is None:
                slot = 'preserve.subject_constraints'
            elif slot.startswith("subject."):
                slot = "subject." + str(fact.subject_id) + "." + slot.split(".", 1)[1]
            index = count.get(slot, 0)
            count[slot] = index + 1
            # Indexed paths are projection IDs, never emitted as a mechanical dump.
            path = slot + f"[{index}]"
            source = fact.fact_id
            text = fact.text
            # Render closed authored enum values, never enhance free creative prose.
            if fact.slot == "medium":
                text = {"LIVE_ACTION": "真人电影", "DESIGNED_CG": "设计型CG", "CINEMATIC_CG": "电影CG",
                        "ILLUSTRATION": "插画", "ANIMATION": "动画"}.get(text, text)
            if fact.source_ref.path[-1:] == ("decision",) and text == "NO_SCORE_MUST_PRESERVE":
                text = "本镜头不配乐。"
            if fact.domain == "CAMERA" and fact.source_ref.path[-1:] == ("decision",):
                text = {"START": "本镜开始运镜。", "CONTINUE": "延续已开始的运镜。", "CHANGE": "改变运镜。",
                        "STOP": "停止运镜。", "HOLD": "保持当前机位。"}.get(text, text)
            rows.append(dict(path=path, text=text, source=source, scope="CLIP",
                priority="CRITICAL" if fact.obligation == Obligation.EXECUTION_REQUIRED else "OPTIONAL",
                required=fact.obligation == Obligation.EXECUTION_REQUIRED))
            mapping[path] = fact.fact_id
            if slot == "video.audio_requirements" and plan.native_audio_policy != "DISABLED":
                event = next((e for e in plan.speech_events if e.spoken_content_id and
                    fact.source_ref.artifact_ref == e.source_ref.artifact_ref and
                    fact.source_ref.path == e.source_ref.path + ("text",)), None)
                timing = None if event is None or event.window_ms is None else f"{event.window_ms[0]/1000:g}–{event.window_ms[1]/1000:g}s"
                audio.append(AudioBinding(path=path, source=source, text_hash=sha256_canonical(text),
                    kind=(event.delivery_mode if event.delivery_mode in ('VOICE_OVER','OFF_SCREEN') else 'DIALOGUE') if event is not None else "SFX", speaker=str(fact.subject_id) if event else None,
                    language=event.language if event else None, timing=timing))
        camera = next(f for f in ir.facts if f.slot == "video.camera_motion")
        # Existing generator only needs this read-only structural subset. We do
        # not fill unused legacy VisualPromptIR fields with fabricated defaults.
        view = SimpleNamespace(task=SimpleNamespace(clip_id=ir.scope.shot_id),
            subjects=tuple(SimpleNamespace(id=identity, role=SimpleNamespace(text=next(
                (f.text for f in ir.facts if f.subject_id == identity and f.slot == "subject.role" and f.source_ref.path[-1:] == ('role',)),
                next((f.text for f in ir.facts if f.subject_id == identity and f.slot == 'subject.role'),identity))))
                for identity in subjects), action=True, blocking=True,
            video_temporal=SimpleNamespace(camera_motion=SimpleNamespace(text=camera.text, source=camera.fact_id),
                action_progression=tuple(f for f in ir.facts if f.slot == "video.action_progression")))
        inputs = []
        for item in references:
            binding = item.binding
            media = binding.media.model_dump(mode="json", by_alias=False)
            media["slot"] = ("reference_" + binding.media.kind + "s" if binding.role == "REFERENCE" else
                {"FIRST_FRAME": "first_frame", "LAST_FRAME": "last_frame"}[binding.role])
            media["prompt_binding"] = {"subject_ids": list(binding.subject_ids), "coverage": []}
            inputs.append(media)
        generated = get_generator(policy.family).generate(cast(VisualPromptIR, view), rows,
            context={"mode": input_mode, "references": inputs, "native_audio": policy.native_audio and plan.native_audio_policy != "DISABLED",
                     "unit_layout": True,
                     "segment_timing": self.segment_timing(profile),
                     "actor_tokens_only": True,
                     "annotations": ProjectionAnnotations(audio=tuple(audio)).model_dump(mode="json")},
            hard_limit=policy.hard_limit)
        return {**generated, "target_mapping": mapping}

    @staticmethod
    def segment_timing(profile: ExecutionProfile | None) -> str:
        """Transport duration semantics only; creative windows remain literal owner text."""
        if profile is None:
            return ""
        if profile.duration_mode == 'AUTO':
            from drama_plugin.providers.video.registry import automatic_duration_bounds_ms
            lo, hi = automatic_duration_bounds_ms(profile.model)
            duration = f"本段自动时长范围{lo/1000:g}–{hi/1000:g}秒，上限不是填满目标"
        else:
            duration = f"本段生成时长{profile.requested_duration_ms/1000:g}秒"
        return duration + "；保持下述动作与声音注明的先后、并行与结束条件，不为凑时长补演或循环。"


class ExactPromptTransfer:
    """The future transport handoff reads the authoritative text without a rewrite."""
    @staticmethod
    def prompt(artifact) -> str:
        return artifact.prompt_text
