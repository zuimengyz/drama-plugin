"""One Director intent; the other values are nested projection/observation data.

No psychology, dialogue, provider controls, independent beat identity or approval.
"""
from __future__ import annotations
from typing import Annotated, Literal, Self, Any
from pydantic import ConfigDict, Field, StringConstraints, model_validator, model_serializer, SerializerFunctionWrapHandler
from drama_plugin.contracts.base import ContractModel

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Hash = Annotated[str, StringConstraints(pattern=r'^[0-9a-f]{64}$')]
Level = Literal['LOW', 'MEDIUM', 'HIGH']
ObservedLevel = Literal['LOW', 'MEDIUM', 'HIGH', 'UNKNOWN']
Ms = Annotated[int, Field(strict=True, ge=0)]


class BeatCoordination(ContractModel):
    """A relation between referenced events, not an independently owned timeline."""
    beat_id: Text
    spoken_content_id: Text
    event: Text
    relation: Literal['NOT_BEFORE', 'NOT_AFTER', 'WITHIN']
    anchor: Text
    end_anchor: Text | None = None
    reason: Text
    tolerance_ms: Ms = 0

    @model_validator(mode='after')
    def interval_anchor(self) -> Self:
        if (self.relation == 'WITHIN') != bool(self.end_anchor):
            raise ValueError('WITHIN requires exactly two event anchors')
        if self.event in (self.anchor, self.end_anchor):
            raise ValueError('Coordination must compare distinct events')
        return self


class DirectorPerformanceIntent(ContractModel):
    """The sole new top-level sidecar, indexed by existing Director SourcePins."""
    model_config = ConfigDict(frozen=True)
    schema_version: Literal['director-performance-intent-v1'] = 'director-performance-intent-v1'
    scene_id: Text
    source_fingerprints: dict[Text, Hash] = Field(min_length=1)
    dpd_fingerprints: tuple[Hash, ...] = Field(min_length=1)
    beat_ids: tuple[Text, ...] = Field(min_length=1)
    performance_core: Text
    audience_experience: Text
    primary_focus: Text
    containment: Text
    external_expression_ceiling: Level
    permitted_release: tuple[Text, ...]
    release_point: Text
    partner_focus: Text
    performance_rhythm: Text
    continuity_in: Text
    continuity_out: Text
    do_not: tuple[Text, ...] = Field(min_length=1)
    forbidden_behaviors: tuple[Text, ...] = ()
    coordination: tuple[BeatCoordination, ...] = ()
    music_constraints: tuple[Text, ...] = ()
    physical_consequences: dict[Text, Text] = Field(default_factory=dict)
    review_basis: Literal['DESIGN_FIXTURE_ONLY', 'SOURCE_BOUND_DESIGN']

    @model_serializer(mode='wrap')
    def legacy_intent(self, handler: SerializerFunctionWrapHandler) -> dict[str,Any]:
        result: dict[str,Any]=handler(self)
        for snake,camel in (('music_constraints','musicConstraints'),('physical_consequences','physicalConsequences')):
            if not getattr(self,snake):result.pop(snake,None);result.pop(camel,None)
        return result

    @model_validator(mode='after')
    def source_scoped(self) -> Self:
        if len(set(self.dpd_fingerprints)) != len(self.dpd_fingerprints) or len(set(self.beat_ids)) != len(self.beat_ids):
            raise ValueError('Duplicate DPD/Beat binding')
        if any(c.beat_id not in self.beat_ids for c in self.coordination):
            raise ValueError('Coordination references an unbound DPD Beat')
        if set(self.permitted_release) & set(self.forbidden_behaviors):
            raise ValueError('Release cannot also be forbidden')
        return self


class VocalDelivery(ContractModel):
    """Nested execution semantics, not a song, melody or new content entity."""
    mode: Literal['SPOKEN', 'RECITATIVE', 'SUNG', 'SHARED_RESPONSE', 'NONVERBAL', 'DECLAMED_VERSE']
    source_ref: Text
    lyric_status: Literal['EXACT_SOURCE', 'NO_APPROVED_LYRICS']
    melody_status: Literal['NOT_APPLICABLE', 'UNRESOLVED', 'APPROVED']
    melody_ref: Text | None = None
    realization_status: Literal['RESOLVED','UNRESOLVED','DO_NOT_REALIZE_AS_SEPARATE_MODERN_VOCAL'] = 'RESOLVED'

    @model_serializer(mode='wrap')
    def legacy_vocal(self, handler: SerializerFunctionWrapHandler) -> dict[str,Any]:
        result: dict[str,Any]=handler(self)
        if self.realization_status=='RESOLVED':result.pop('realization_status',None);result.pop('realizationStatus',None)
        return result

    @model_validator(mode='after')
    def melody_boundary(self) -> Self:
        if (self.melody_status == 'APPROVED') != bool(self.melody_ref):
            raise ValueError('MELODY_APPROVAL_REFERENCE_REQUIRED')
        if self.mode == 'DECLAMED_VERSE' and self.melody_status!='NOT_APPLICABLE':
            raise ValueError('HISTORICAL_VERSE_CANNOT_CLAIM_MELODY')
        if self.mode in ('SUNG', 'RECITATIVE', 'SHARED_RESPONSE') and self.melody_status == 'NOT_APPLICABLE' and self.realization_status=='RESOLVED':
            raise ValueError('Vocal composition choice must remain explicit; no invented melody')
        if self.mode == 'NONVERBAL' and self.lyric_status != 'NO_APPROVED_LYRICS':
            raise ValueError('Nonverbal vocalization cannot contain new lyrics')
        return self


class PerformanceProjection(ContractModel):
    """Nested in the existing Visual/Audio Brief; no own identity or authority."""
    director_intent_fingerprint: Hash
    beat_id: Text
    spoken_content_id: Text
    channel: Literal['VISUAL', 'VOICE']
    interaction_target: Text
    spatial_projection: Text
    external_expression: Level
    external_control: Level
    body_load: Level
    breath: Text
    release: tuple[Text, ...]
    continuity_in: Text
    continuity_out: Text
    coordination: tuple[BeatCoordination, ...] = ()
    instructions: dict[Text, Text] = Field(min_length=1)
    behaviors: tuple[Text, ...] = ()
    vocal_delivery: VocalDelivery | None = None
    context_fingerprint: Hash | None = None
    context_refs: tuple[Text, ...] = ()

    @model_serializer(mode="wrap")
    def legacy_projection(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        result: dict[str, Any] = handler(self)
        for snake, camel in (("vocal_delivery", "vocalDelivery"), ("context_fingerprint", "contextFingerprint"), ("context_refs", "contextRefs")):
            if not getattr(self, snake):
                result.pop(snake, None); result.pop(camel, None)
        return result

    route: Literal['stylized_cinematic_cg', 'live_action'] | None = None
    grammar_fingerprint: Hash | None = None

    @model_validator(mode='after')
    def channel_boundary(self) -> Self:
        if self.channel == 'VISUAL' and self.vocal_delivery:
            raise ValueError('Vocal mode belongs to voice projection')
        if bool(self.context_fingerprint) != bool(self.context_refs):
            raise ValueError('Context fingerprint and resolved refs are required together')
        visual = {'body_state', 'posture', 'weight', 'movement', 'eyes', 'head', 'hands',
                  'visible_breath', 'prop', 'partner', 'distance', 'timing', 'release',
                  'continuity', 'do_not'}
        voice = {'voice_core', 'interaction', 'spatial_projection', 'pace', 'rhythm',
                 'intensity', 'breath_support', 'phrase_attack', 'articulation', 'emphasis',
                 'pause_function', 'sentence_closure', 'coloration', 'release',
                 'continuity', 'do_not'}
        if set(self.instructions) != (visual if self.channel == 'VISUAL' else voice):
            raise ValueError('Projection requires concrete channel instructions, no psychology/provider fields')
        if self.channel == 'VOICE' and (self.route is not None or self.grammar_fingerprint is not None):
            raise ValueError('Voice direction is route-independent')
        if self.channel == 'VISUAL' and (self.route is None or self.grammar_fingerprint is None):
            raise ValueError('Visual direction requires the selected route grammar')
        if any(c.beat_id != self.beat_id or c.spoken_content_id != self.spoken_content_id for c in self.coordination):
            raise ValueError('Projection coordination must use its bound Beat and SpokenContent')
        return self


class PerformanceObservation(ContractModel):
    """Nested evidence in RP/FilmReview. Labels are observer attestations, not AI sensing."""
    channel: Literal['VISUAL', 'VOICE']
    beat_id: Text
    spoken_content_id: Text
    speaker_key: Text
    media_hash: Hash
    method: Literal['DESIGN_FIXTURE', 'NORMAL_AV', 'NORMAL_VIDEO', 'AUDIO', 'FRAMES']
    observer: Text
    evidence_ref: Text
    start_ms: Ms
    end_ms: Ms
    external_expression: ObservedLevel = 'UNKNOWN'
    external_control: ObservedLevel = 'UNKNOWN'
    interaction_target: Text | None = None
    spatial_projection: Text | None = None
    body_load: ObservedLevel = 'UNKNOWN'
    breath: Text | None = None
    behaviors: tuple[Text, ...] = ()
    release: tuple[Text, ...] = ()
    continuity_in: Text | None = None
    continuity_out: Text | None = None
    event_times_ms: dict[Text, Ms] = Field(default_factory=dict)
    meaning_preserved: Literal['PASS', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'

    @model_validator(mode='after')
    def observed_range(self) -> Self:
        if self.end_ms <= self.start_ms or any(not self.start_ms <= t <= self.end_ms for t in self.event_times_ms.values()):
            raise ValueError('Observed event outside evidence interval')
        if self.channel == 'VOICE' and self.method in ('FRAMES', 'NORMAL_VIDEO'):
            raise ValueError('Frames cannot establish audible performance')
        return self
