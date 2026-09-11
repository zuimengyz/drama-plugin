"""Compact creative IR for director-authored, source-pinned Shot execution."""
from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import CinematicLanguageRef

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
Seconds = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Level = Literal['LOW', 'MEDIUM', 'HIGH']
ReferenceRole = Literal['CHARACTER', 'COSTUME', 'LOCATION', 'LOOK', 'COMPOSITION',
                        'CAMERA_MOTION', 'PERFORMANCE', 'VFX', 'CONTINUITY']


class Palette(ContractModel):
    dominant: tuple[Text, ...] = Field(min_length=1)
    accent: tuple[Text, ...] = ()


class Lighting(ContractModel):
    philosophy: Text
    fill: Text
    face_shadow_allowed: bool


class ImageCharacter(ContractModel):
    saturation: Text
    contrast: Text
    highlight: Text
    black_level: Text


class Materials(ContractModel):
    skin: Text
    costume: Text
    metal: Text
    environment: Text


class VisualBible(ContractModel):
    realism: Text
    palette: Palette
    lighting: Lighting
    image_character: ImageCharacter
    materials: Materials
    atmosphere: Text
    camera_philosophy: Text
    forbidden: tuple[Text, ...] = ()


class BehaviorAnchor(ContractModel):
    actor: Text
    ongoing_activity: Text
    continuity_basis: Text
    interruption: Text


class ObservableAction(ContractModel):
    actor: Text
    behavior: Text
    target: Text | None = None
    trigger: Text | None = None
    prop: Text | None = None


class PerformanceBeat(ContractModel):
    start: Seconds
    end: Seconds
    kind: Literal['ACTION', 'DIALOGUE', 'REACTION', 'HOLD', 'CONTINUOUS']
    start_state: Text
    actions: tuple[ObservableAction, ...] = Field(min_length=1)
    end_state: Text
    overlap_reason: Text | None = None


class Performance(ContractModel):
    objective: Text
    interaction_target: Text
    intended_belief: Text | None = None
    concealed: Text | None = None
    emotional_arc: tuple[Text, ...] = ()
    beats: tuple[PerformanceBeat, ...] = Field(min_length=1)


class DialogueDirection(ContractModel):
    spoken_content_id: Text
    speaker_key: Text
    text: Text
    start: Seconds
    end: Seconds
    target: Text
    delivery: Text
    after_line: Text
    coverage_intent: Literal['ON_SCREEN_SPEAKER', 'REACTION', 'OFF_SCREEN', 'VOICE_OVER'] = 'ON_SCREEN_SPEAKER'
    # Canonical sentence offset, not another Dialogue entity. The group artifact
    # proves these local slices; text remains the exact canonical full sentence.
    canonical_interval: tuple[Seconds, Seconds] | None = None
    text_range: tuple[int, int] | None = None


class SourceSoundIntent(ContractModel):
    """Generation-time intent; never a voice, mixing recipe or finishing plan."""
    native_audio_policy: Literal['REQUIRED', 'PREFERRED', 'DISABLED']
    canonical_dialogue_bindings: tuple[Text, ...] = ()
    diegetic: tuple[Text, ...] = ()
    ambience: tuple[Text, ...] = ()
    intentional_silence: tuple[Text, ...] = ()
    generated_music: Literal['FORBIDDEN', 'ALLOWED'] = 'FORBIDDEN'
    continuity: tuple[Text, ...] = ()


class Cinematography(ContractModel):
    shot_size: Text
    composition: Text
    placement: Text
    height: Text
    subject_orientation: Text
    lens_intent: Text
    focus_target: Text
    focus_transition: Text
    movement_class: Literal['LOCKED', 'RESTRAINED', 'MOTIVATED', 'DYNAMIC']
    movement: Text
    amplitude: Text
    trigger: Text | None = None
    motivation: Text | None = None
    opening_composition: Text
    ending_composition: Text


class SecondaryMotion(ContractModel):
    element: Text
    cause: Text
    response: Text
    limit: Text


class EnvironmentInteraction(ContractModel):
    source: Text
    effect: Text
    affected: Text
    response: Text
    occlusion_or_depth: Text


class StabilityRule(ContractModel):
    dimension: Text
    allowed: Text
    forbidden: Text
    reason: Text


class ReferenceRequirement(ContractModel):
    role: ReferenceRole
    necessity: Literal['REQUIRED', 'PREFERRED']
    subject: Text
    purpose: Text
    # A duty is not an upload slot or proof that a reference is a first frame.
    establishes_opening_state: bool = False

    @model_validator(mode='after')
    def role_semantics(self) -> Self:
        if self.establishes_opening_state and self.role not in {'COMPOSITION', 'CONTINUITY'}:
            raise ValueError('A character/look reference alone is not an opening frame')
        return self


class ExecutionRequirements(ContractModel):
    duration_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    performance: dict[str, Level]
    motion: dict[str, Level]
    continuity: dict[str, Level]
    reference_roles: tuple[ReferenceRole, ...]
    timing_intent: Text


class CinematicShotSpec(ContractModel):
    schema_version: Literal['cinematic-shot-v1'] = 'cinematic-shot-v1'
    work_id: Text
    scene_id: Text
    shot_id: Text
    creative_revision: Text
    source_fingerprint: Hash
    visual_bible_fingerprint: Hash
    narrative_intent: Text
    visual_bible: VisualBible
    duration_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    opening_state: Text
    behavior_anchor: BehaviorAnchor | None = None
    anchor_omission_reason: Text | None = None
    performance: Performance
    dialogue: tuple[DialogueDirection, ...] = ()
    cinematography: Cinematography
    lighting: Text
    secondary_motion: tuple[SecondaryMotion, ...] = ()
    secondary_motion_omission_reason: Text | None = None
    environment_interaction: tuple[EnvironmentInteraction, ...] = ()
    stability_contract: tuple[StabilityRule, ...] = Field(min_length=1)
    reference_requirements: tuple[ReferenceRequirement, ...] = ()
    execution_requirements: ExecutionRequirements
    ending_state: Text
    source_sound_intent: SourceSoundIntent | None = None
    cinematic_language_refs: tuple[CinematicLanguageRef, ...] = ()

    @model_validator(mode='after')
    def consistent_execution(self) -> Self:
        if len({r.asset_id for r in self.cinematic_language_refs}) != len(self.cinematic_language_refs):
            raise ValueError('Duplicate cinematic language reference')
        beats = self.performance.beats
        if beats[0].start != 0 or beats[-1].end != self.duration_seconds:
            raise ValueError('Timeline must cover Opening through Ending; holds are explicit beats')
        if beats[0].start_state != self.opening_state or beats[-1].end_state != self.ending_state:
            raise ValueError('Opening/Ending states disagree with boundary beats')
        for i, beat in enumerate(beats):
            if beat.end <= beat.start or beat.end > self.duration_seconds:
                raise ValueError('Negative/empty beat or Shot duration overflow')
            if i:
                previous = beats[i-1]
                if beat.start < previous.start or beat.end < previous.end:
                    raise ValueError('Beat order is reversed')
                if beat.start < previous.end and not beat.overlap_reason:
                    raise ValueError('Unexplained beat overlap')
                if beat.start > previous.end:
                    raise ValueError('Unexplained timeline gap; represent the hold/continuous action')
                if beat.start == previous.end and beat.start_state != previous.end_state:
                    raise ValueError('Unexplained state/prop jump between beats')
        if len({d.spoken_content_id for d in self.dialogue}) != len(self.dialogue):
            raise ValueError('Duplicate dialogue identity; one line may describe internal pauses')
        for line in self.dialogue:
            if line.end <= line.start or line.end > self.duration_seconds:
                raise ValueError('Dialogue outside Shot duration')
            if not any(b.kind in {'DIALOGUE', 'CONTINUOUS', 'REACTION'} and b.start <= line.start and b.end >= line.end for b in beats):
                raise ValueError('Dialogue lacks a covering performance beat')
        if self.execution_requirements.duration_seconds != self.duration_seconds:
            raise ValueError('Execution duration disagrees with Shot')
        if set(self.execution_requirements.reference_roles) != {r.role for r in self.reference_requirements}:
            raise ValueError('Execution reference roles must match explicit duties')
        if len({r.dimension for r in self.stability_contract}) != len(self.stability_contract):
            raise ValueError('Duplicate stability dimension')
        return self
