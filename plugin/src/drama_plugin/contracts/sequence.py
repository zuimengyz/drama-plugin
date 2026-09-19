"""Sequence sidecars compose existing owners; no new business entity or adoption authority."""
from __future__ import annotations
from typing import Annotated, Any, Literal, Self
from pydantic import ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer, model_validator
from drama_plugin.contracts.editorial_authority import EditorialUsability
from drama_plugin.contracts.adaptive_direction import ObservedMaterialEvidence, AdaptiveDecision
from drama_plugin.contracts.source_pin import SourcePin as SourcePin
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.performance_direction import PerformanceObservation
from drama_plugin.contracts.creative_asset import Hash, Text
from drama_plugin.contracts.dramatic_editorial import EditorialRhythmPlan, Seconds
from drama_plugin.contracts.production_freeze import FreezeReference
from drama_plugin.contracts.sequence_execution import MountInteraction, ProductionClip, AcceptanceCriterion


class BibleEntry(ContractModel):
    key: Text
    kind: Literal['CHARACTER', 'LOCATION', 'PROP', 'CREATURE']
    source_keys: tuple[Text, ...] = Field(min_length=1)
    invariants: dict[str, Text] = Field(min_length=1)
    state_variables: tuple[Text, ...] = ()
    interaction_requirements: tuple[Text, ...] = ()
    reference_duties: dict[str, Text] = Field(min_length=1)
    unresolved: tuple[Text, ...] = ()
    living_asset: MountInteraction | None = None
    # An index of source decisions; it cannot approve or replace the underlying Asset.


class SceneGeography(ContractModel):
    scene_id: Text
    anchors: dict[str, Text] = Field(min_length=1)
    traversable_relations: tuple[Text, ...]
    axis_and_viewpoint: Text
    scale_basis: Text
    design_assumptions: tuple[Text, ...] = ()


class ShotReceiver(ContractModel):
    key: Text
    source_shot_id: Text
    scene_id: Text
    incoming_state: dict[str, Text] = Field(min_length=1)
    outgoing_state: dict[str, Text] = Field(min_length=1)
    bible_keys: tuple[Text, ...] = ()
    storyboard: Text
    performance_change: Text
    camera_reason: Text
    edit_handles: Text
    production: ProductionClip | None = None
    unresolved: tuple[Text, ...] = ()


class ClipBridge(ContractModel):
    outgoing: Text
    incoming: Text
    relation: Literal['CONTINUOUS', 'ELLIPSIS', 'PARALLEL']
    carry_keys: tuple[Text, ...] = ()
    motivation: Text
    motion_bridge: Text
    visual_bridge: Text
    audio_bridge: Text
    discontinuity_explanation: Text | None = None
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()


class SequencePackage(ContractModel):
    schema_version: Literal['sequence-package-v1'] = 'sequence-package-v1'
    revision: Text
    scope_id: Text
    status: Literal['RECOMMENDED', 'DESIGN_REVIEWED'] = 'RECOMMENDED'
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    objective: Text
    payoff: Text
    aftermath: Text
    bibles: tuple[BibleEntry, ...] = ()
    geography: tuple[SceneGeography, ...] = Field(min_length=1)
    editorial: EditorialRhythmPlan
    shots: tuple[ShotReceiver, ...] = Field(min_length=1)
    bridges: tuple[ClipBridge, ...] = ()
    unresolved: tuple[Text, ...] = ()
    production_permission: Literal['NONE'] = 'NONE'
    formal_mutation_allowed: Literal[False] = False
    production_design_freeze: FreezeReference | None = None

    @model_validator(mode='after')
    def connected_package(self) -> Self:
        def unique(values: list[str]) -> set[str]:
            if len(set(values)) != len(values):
                raise ValueError('Duplicate sequence identity')
            return set(values)
        pins = unique([p.key for p in self.source_pins])
        if not any(p.kind == 'CANON' for p in self.source_pins):
            raise ValueError('Sequence needs current Canon pins')
        bibles = unique([b.key for b in self.bibles])
        for b in self.bibles:
            if not set(b.source_keys) <= pins:
                raise ValueError('Bible source is not pinned')
        geography = unique([g.scene_id for g in self.geography])
        keys = [s.key for s in self.shots]
        unique(keys)
        if keys != [s.key for s in self.editorial.coverage]:
            raise ValueError('Storyboard must follow the reviewed coverage order')
        for s in self.shots:
            if s.source_shot_id not in pins:
                raise ValueError('Source Shot is not pinned')
            if s.scene_id not in geography or s.scene_id not in self.editorial.scene_ids:
                raise ValueError('Shot has no geography or editorial Scene')
            if s.production and not set(s.production.asset_refs) <= set(s.bible_keys):
                raise ValueError('Production Asset ref must resolve through receiver Bible')
            if not set(s.bible_keys) <= bibles:
                raise ValueError('Shot has an unresolved Bible identity')
        pairs = list(zip(keys, keys[1:]))
        if [(b.outgoing, b.incoming) for b in self.bridges] != pairs:
            raise ValueError('Every adjacent cut needs exactly one receiver')
        shots = {s.key: s for s in self.shots}
        for bridge in self.bridges:
            left, right = shots[bridge.outgoing], shots[bridge.incoming]
            if bridge.relation == 'CONTINUOUS' and left.scene_id != right.scene_id:
                raise ValueError('Cross-Scene cut needs an explicit relation')
            if bridge.relation != 'CONTINUOUS' and not bridge.discontinuity_explanation:
                raise ValueError('Time/space jump must be accounted for')
            for key in bridge.carry_keys:
                if key not in left.outgoing_state or key not in right.incoming_state:
                    raise ValueError('Missing declared continuity state')
                if left.outgoing_state[key] != right.incoming_state[key]:
                    raise ValueError('Receiver contradicts outgoing state')
        return self


class PlaybackObservation(ContractModel):
    start: Seconds
    end: Seconds
    mode: Literal['NORMAL_AV', 'NORMAL_VIDEO', 'TEMPORAL_VISUAL', 'AUDIO', 'FRAMES', 'TECHNICAL']
    observer: Text
    evidence_ref: Text

    @model_validator(mode='after')
    def positive(self) -> Self:
        if self.end <= self.start:
            raise ValueError('Observation needs a positive interval')
        return self


class FilmFinding(ContractModel):
    key: Text
    start: Seconds
    end: Seconds
    domain: Literal['STORY', 'CASTING', 'SPACE', 'CONTINUITY', 'PERFORMANCE', 'PICTURE', 'SOUND', 'CANON']
    severity: Literal['MAJOR', 'NOTE']
    observation: Text
    consequence: Text
    repair_owner: Text
    proposed_repair: Text
    resolved: bool = False
    recheck_evidence: Text | None = None

    @model_validator(mode='after')
    def resolution_evidence(self) -> Self:
        if self.end < self.start or (self.resolved and not self.recheck_evidence):
            raise ValueError('Finding resolution requires interval and recheck evidence')
        return self


DirectorDisposition = Literal['APPROVE', 'REVISE_EXECUTION', 'REVISE_PERFORMANCE',
    'REVISE_BLOCKING', 'REVISE_COVERAGE', 'REVISE_EDIT', 'REVISE_SOUND', 'REPLAN_SCENE',
    'REQUEST_SCRIPT_REVIEW', 'ESCALATE_PRODUCTION_METHOD', 'INSUFFICIENT_EVIDENCE']


class DirectorReviewFacet(ContractModel):
    """Optional binding in the existing FilmReview or Bible design review, never a second review."""
    model_config = ConfigDict(frozen=True)
    workspace_id: Text
    branch_id: Text
    scope_id: Text
    source_pins: tuple[SourcePin, ...] = Field(min_length=1)
    route_ref: SourcePin | None = None
    intent_refs: tuple[SourcePin, ...] = Field(min_length=1)
    request_ref: SourcePin
    feedback_ref: SourcePin
    intent_coverage: dict[str, Literal['PASS', 'FAIL', 'UNKNOWN']] = Field(min_length=1)
    disposition: DirectorDisposition
    finding_keys: tuple[Text, ...] = ()  # Repair owner/body stay in the original findings.
    reason_summary: Text
    adopted_delta_ref: SourcePin | None = None

    @model_validator(mode='after')
    def coverage(self) -> Self:
        if set(self.intent_coverage) != {p.key for p in self.intent_refs}:
            raise ValueError('Director review must cover every assigned intent')
        if self.disposition == 'APPROVE' and any(v != 'PASS' for v in self.intent_coverage.values()):
            raise ValueError('UNKNOWN or failed intent cannot be approved')
        return self


class FilmReview(ContractModel):
    observed_material_evidence: tuple[ObservedMaterialEvidence, ...] = ()
    adaptive_decisions: tuple[AdaptiveDecision, ...] = ()
    editorial_usability: tuple[EditorialUsability, ...] = ()
    media_hash: Hash
    duration: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    observations: tuple[PlaybackObservation, ...] = ()
    findings: tuple[FilmFinding, ...] = ()
    technical: Literal['PASS', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'
    story_rhythm: Literal['PASS', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'
    visual_continuity: Literal['PASS', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'
    sound: Literal['PASS', 'FAIL', 'UNKNOWN'] = 'UNKNOWN'
    persistence_verified: bool = False
    director: DirectorReviewFacet | None = None
    performance_alignment: dict[str, Literal["PASS", "FAIL", "UNKNOWN"]] = Field(default_factory=dict)
    performance_beats: dict[str, dict[str, Literal["PASS", "FAIL", "UNKNOWN"]]] = Field(default_factory=dict)
    performance_required_beats: tuple[str, ...] = ()
    performance_coverage_fingerprint: Hash | None = None
    performance_coverage_channels: dict[str, tuple[Literal["VISUAL", "VOICE"], ...]] = Field(default_factory=dict)
    performance_refs: tuple[SourcePin, ...] = ()
    performance_observations: tuple[PerformanceObservation, ...] = ()
    performance_review_basis: Literal["DESIGN_ONLY", "OBSERVED_MEDIA"] | None = None
    native_audio_suitability: dict[str, Literal["PASS", "FAIL", "UNKNOWN"]] = Field(default_factory=dict)

    @model_serializer(mode='wrap')
    def legacy_serialization(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if not self.observed_material_evidence:
            data.pop('observedMaterialEvidence', None); data.pop('observed_material_evidence', None)
        if not self.adaptive_decisions:
            data.pop('adaptiveDecisions', None); data.pop('adaptive_decisions', None)
        if not self.editorial_usability:
            data.pop('editorialUsability', None); data.pop('editorial_usability', None)
        if self.director is None:
            data.pop('director', None)
        for snake, camel in [('performance_coverage_channels', 'performanceCoverageChannels'), ('performance_coverage_fingerprint', 'performanceCoverageFingerprint'), ('performance_beats', 'performanceBeats'), ('performance_required_beats', 'performanceRequiredBeats'), ('performance_alignment', 'performanceAlignment'), ('performance_refs', 'performanceRefs'), ('performance_observations', 'performanceObservations'), ('performance_review_basis', 'performanceReviewBasis'), ('native_audio_suitability', 'nativeAudioSuitability')]:
            if not getattr(self, snake):
                data.pop(snake, None); data.pop(camel, None)
        return data

    @model_validator(mode='after')
    def ranges(self) -> Self:
        evidence={e.key:e for e in self.observed_material_evidence}
        if len(evidence)!=len(self.observed_material_evidence):raise ValueError('Duplicate observed evidence')
        for fact in self.observed_material_evidence:
            if fact.media_hash!=self.media_hash or fact.end>self.duration:raise ValueError('Adaptive evidence range/hash mismatch')
            if fact.basis=='OBSERVED_MEDIA':
                cursor=fact.start
                for o in sorted(self.observations,key=lambda x:x.start):
                    if o.mode==fact.method and o.evidence_ref in {p.key for p in fact.evidence_refs} and o.start<=cursor:cursor=max(cursor,o.end)
                if cursor<fact.end:raise ValueError('Adaptive observed fact lacks matching playback evidence')
        for decision in self.adaptive_decisions:
            if not set(decision.evidence_refs)<=set(evidence):raise ValueError('Adaptive decision missing evidence')
            if any(evidence[k].media_ref!=decision.media_ref for k in decision.evidence_refs):raise ValueError('Adaptive decision references other media')
        for e in self.editorial_usability:
            if e.media_hash != self.media_hash or any(r.end > self.duration for r in e.usable_ranges):
                raise ValueError('Editorial usability is outside this FilmReview media/range')
            if e.basis == 'OBSERVED_MEDIA':
                if not self.observations:
                    raise ValueError('Observed editorial usability requires playback evidence')
                for usable in e.usable_ranges:
                    cursor = usable.start
                    for observation in sorted(self.observations, key=lambda o: o.start):
                        if observation.mode == 'NORMAL_AV' and observation.start <= cursor:
                            cursor = max(cursor, observation.end)
                    if cursor < usable.end:
                        raise ValueError('Usable range lacks normal AV observation coverage')
        if any(o.end > self.duration for o in self.observations) or any(f.end > self.duration for f in self.findings):
            raise ValueError('Review range exceeds actual file')
        if self.performance_alignment and (not self.performance_refs or not self.performance_review_basis):
            raise ValueError('AV alignment requires compared source refs and review basis')
        for performance_observation in self.performance_observations:
            if performance_observation.media_hash != self.media_hash or performance_observation.end_ms > self.duration * 1000:
                raise ValueError('Performance observation belongs to different media/range')
            if self.performance_review_basis == 'OBSERVED_MEDIA' and performance_observation.method == 'DESIGN_FIXTURE':
                raise ValueError('Design fixture is not observed media evidence')
        if self.director and not set(self.director.finding_keys) <= {f.key for f in self.findings}:
            raise ValueError('Director finding reference is missing')
        return self
