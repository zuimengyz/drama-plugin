"""Provider-neutral visual intent. Missing creative facts are errors, never defaults."""
from __future__ import annotations
from typing import Literal, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

Priority = Literal['CRITICAL', 'IMPORTANT', 'SECONDARY']
TaskType = Literal['TEXT_TO_IMAGE', 'IMAGE_EDIT', 'REFERENCE_EDIT', 'FIRST_FRAME', 'KEY_FRAME', 'VIDEO']


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class Fact(Record):
    text: str = Field(min_length=1)
    priority: Priority
    scope: Literal['CURRENT', 'CLIP', 'CAPABILITY', 'FUTURE', 'INTERNAL'] = 'CURRENT'
    # An authoring/source locator, retained in IR; never emitted to the provider.
    source: str = Field(min_length=1)

    @model_validator(mode='after')
    def text_shape(self) -> Self:
        if not self.text.strip() or '\n' in self.text or not self.source.strip():
            raise ValueError('VISUAL_PROMPT_FACT_REQUIRES_SINGLE_SCOPED_DESCRIPTION')
        return self


class Task(Record):
    task_type: TaskType
    provider_family: str = Field(min_length=1)
    visual_medium: Literal['LIVE_ACTION', 'DESIGNED_CG', 'CINEMATIC_CG', 'ILLUSTRATION', 'ANIMATION']
    subject_kind: Literal['CHARACTER', 'SCENE', 'COMPOSITE']
    input_mode: Literal['text', 'reference', 'single_image', 'first_last', 'edit']
    clip_id: str | None = None


class World(Record):
    era: Fact
    location: Fact
    historical_context: Fact
    environment_rules: tuple[Fact, ...] = Field(min_length=1)


class Subject(Record):
    id: str = Field(min_length=1)
    role: Fact
    apparent_age: Fact
    identity_priority: Literal['CRITICAL'] = 'CRITICAL'
    face: Fact
    hair: Fact
    beard: Fact | None = None
    body_proportions: Fact
    costume: Fact
    visible_condition: Fact


class Blocking(Record):
    positions: Fact
    orientation: Fact
    contact: Fact
    visible_relation: Fact


class Action(Record):
    current_visible_action: Fact
    expression: Fact
    # Retained source capabilities and future information are never projected.
    non_current: tuple[Fact, ...] = ()


class Environment(Record):
    architecture: Fact
    topology: Fact
    required_period_objects: Fact
    props_vehicles: tuple[Fact, ...] = ()


class Camera(Record):
    framing: Fact
    shot_size: Fact
    readable_details: Fact
    perspective: Fact
    depth_cues: tuple[Fact, ...] = ()


class Lighting(Record):
    time_of_day: Fact
    light_sources: Fact
    contrast: Fact
    realism: Fact


class EditDelta(Record):
    operation: Literal['remove', 'replace', 'correct']
    source_issue: Fact
    target_correction: Fact
    region: str = Field(min_length=1)


class Temporal(Record):
    start_state: Fact
    action_progression: tuple[Fact, ...] = Field(min_length=1)
    performance: tuple[Fact, ...] = Field(min_length=1)
    camera_motion: Fact
    end_state: Fact
    audio_requirements: tuple[Fact, ...] = ()


class Negative(Record):
    constraint: Fact
    # An explicit equivalent, not a keyword substitution or inferred rewrite.
    positive_target: Fact


class VisualPromptIR(Record):
    schema_version: Literal['visual-prompt-ir-v1'] = 'visual-prompt-ir-v1'
    source_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    task: Task
    world: World
    subjects: tuple[Subject, ...] = ()
    blocking: Blocking | None = None
    action: Action | None = None
    environment: Environment
    camera: Camera
    lighting: Lighting
    continuity: tuple[Fact, ...] = ()
    edit_delta: tuple[EditDelta, ...] = ()
    video_temporal: Temporal | None = None
    preserve: tuple[Fact, ...] = ()
    negative_constraints: tuple[Negative, ...] = ()
    secondary_details: tuple[Fact, ...] = ()

    @model_validator(mode='after')
    def task_contract(self) -> Self:
        t = self.task
        if t.subject_kind != 'SCENE' and (not self.subjects or self.blocking is None or self.action is None):
            raise ValueError('VISUAL_PROMPT_SUBJECT_STATE_REQUIRED')
        if self.subjects and (self.blocking is None or self.action is None):
            raise ValueError('VISUAL_PROMPT_BLOCKING_ACTION_REQUIRED')
        if len({s.id for s in self.subjects}) != len(self.subjects):
            raise ValueError('VISUAL_PROMPT_DUPLICATE_SUBJECT')
        edit = t.task_type in {'IMAGE_EDIT', 'REFERENCE_EDIT'}
        if edit != bool(self.edit_delta) or edit and (not self.preserve or t.input_mode not in {'edit', 'reference'}):
            raise ValueError('VISUAL_PROMPT_EDIT_REQUIRES_DELTA_AND_PRESERVE')
        if t.task_type == 'VIDEO':
            if not self.video_temporal or not t.clip_id or not t.clip_id.strip():
                raise ValueError('VISUAL_PROMPT_CLIP_TEMPORAL_REQUIRED')
        elif self.video_temporal is not None or t.clip_id is not None:
            raise ValueError('VISUAL_PROMPT_STATIC_CANNOT_HAVE_TEMPORAL')
        if t.task_type == 'TEXT_TO_IMAGE' and t.input_mode != 'text':
            raise ValueError('VISUAL_PROMPT_INPUT_MODE_MISMATCH')
        return self
