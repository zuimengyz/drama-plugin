"""Source-pinned visual choices, not another character or approval authority."""
from typing import Literal, Self
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash

ProofStage = Literal['FACE', 'SCALE', 'SOCIAL', 'PERFORMANCE']
Responsibility = Literal['DIRECTLY_VISUALIZABLE', 'BODY_SPATIAL_ONLY',
                         'PERFORMANCE_DEPENDENT', 'STORY_DEPENDENT',
                         'FACE_DIRECT', 'BODY_SPATIAL', 'SOCIAL_RELATIONAL', 'PERFORMANCE', 'STORY_ONLY']
APPEAL_MODES = ('refined_attractive', 'heroic_attractive', 'regal_attractive',
    'martial_attractive', 'commanding_attractive', 'dangerous_attractive',
    'charismatic_attractive', 'gentle_attractive', 'intellectual_attractive', 'tragic_attractive')

class TransferablePrinciple(ContractModel):
    key: Text
    mechanism: Text
    discriminant_ids: tuple[Text, ...] = Field(min_length=1)

class ArchetypeReference(ContractModel):
    role_identity: Text
    reference_id: Text
    source_ref: Text
    source_fingerprint: Hash
    proper_names: tuple[Text, ...] = Field(min_length=1)
    interpretation: Text
    transferable_principles: tuple[TransferablePrinciple, ...] = Field(min_length=1)
    do_not_transfer: tuple[Text, ...] = Field(min_length=1)
    scope: Literal['ROLE_SCOPED'] = 'ROLE_SCOPED'
    inherit_by_default: Literal[False] = False
    usage: Literal['MECHANISM_REFERENCE'] = 'MECHANISM_REFERENCE'

class ControlledArchetypalExaggeration(ContractModel):
    mode: Literal['DOCUMENTARY_REALISM', 'GROUNDED_CINEMATIC', 'HEROIC_STYLIZATION', 'MYTHIC_STYLIZATION']
    defining_discriminant_ids: tuple[Text, ...] = Field(min_length=1)
    anatomical_limit: Text
    realism_observations: tuple[Text, ...] = Field(min_length=1)
    forbidden_drifts: tuple[Text, ...] = Field(min_length=1)

class RoleSaliencePolicy(ContractModel):
    principle: Literal['ROLE_SALIENCE_BEFORE_BEAUTY'] = 'ROLE_SALIENCE_BEFORE_BEAUTY'
    defining_discriminant_ids: tuple[Text, ...] = Field(min_length=1)
    beauty_is_search_gate: Literal[False] = False
    optimization_may_reduce_salience: Literal[False] = False

class GeometricRegion(ContractModel):
    measure: Text
    lower: float = Field(allow_inf_nan=False)
    upper: float = Field(allow_inf_nan=False)

    @model_validator(mode='after')
    def interval(self) -> Self:
        if self.lower > self.upper:
            raise ValueError('Invalid geometric region')
        return self

class AppealChannel(ContractModel):
    mode: Text  # Open vocabulary: these modes are examples, not a personality taxonomy.
    audience_effect: Text
    discriminant_ids: tuple[Text, ...] = Field(min_length=1)

class AudienceAppealMode(ContractModel):
    channels: tuple[AppealChannel, ...] = Field(min_length=1)
    primary_response: Literal['LIKING', 'RESPECT', 'MIXED', 'ADMIRATION', 'AWE', 'AUTHORITY', 'SUBMISSION_ORIENTED_APPEAL']
    selection_principle: Text
    # Channels are ordered. No numerical attractiveness score or universal beauty default.

class CastingIntent(ContractModel):
    basis: dict[Literal['excavation', 'identity_era_social', 'counter_stereotype',
                        'role_obligations'], tuple[Text, ...]]
    search_question: Text
    selection_question: Text

    @model_validator(mode='after')
    def complete_basis(self) -> Self:
        if set(self.basis) != {'excavation', 'identity_era_social', 'counter_stereotype', 'role_obligations'} or not all(self.basis.values()):
            raise ValueError('Casting intent must consume all four interpretation sources')
        return self

class VisualDiscriminant(ContractModel):
    key: Text
    responsibility: Responsibility
    stage: ProofStage | None
    basis_pointers: tuple[Text, ...] = Field(min_length=1)
    axis: Text
    choices: dict[str, Text] = Field(min_length=1)
    observation: Text
    geometric_regions: dict[str, GeometricRegion] = Field(default_factory=dict)

    @model_validator(mode='after')
    def responsibility_matches(self) -> Self:
        allowed: dict[str, set[ProofStage | None]] = {'DIRECTLY_VISUALIZABLE': {'FACE', 'SCALE'},
                   'BODY_SPATIAL_ONLY': {'SCALE', 'SOCIAL'},
                   'PERFORMANCE_DEPENDENT': {'PERFORMANCE'}, 'STORY_DEPENDENT': {None},
                   'FACE_DIRECT': {'FACE'}, 'BODY_SPATIAL': {'SCALE'},
                   'SOCIAL_RELATIONAL': {'SOCIAL'}, 'PERFORMANCE': {'PERFORMANCE'}, 'STORY_ONLY': {None}}
        if self.stage not in allowed[self.responsibility]:
            raise ValueError('Wrong proof responsibility: story/behavior cannot become a face criterion')
        if self.geometric_regions and set(self.geometric_regions) != set(self.choices):
            raise ValueError('Geometric regions must cover every alternative')
        return self

class ContrastiveVariant(ContractModel):
    key: Text
    assignments: dict[str, str] = Field(min_length=1)

class CompleteCandidateProofSet(ContractModel):
    required_stages: tuple[ProofStage, ...] = Field(min_length=1)
    social_identity_essential: bool
    scope: Literal['COMPLETE', 'REDUCED']
    omitted_reasons: dict[ProofStage, Text] = Field(default_factory=dict)
    rationale: Text

    @model_validator(mode='after')
    def scope_coherent(self) -> Self:
        required = set(self.required_stages)
        if len(required) != len(self.required_stages) or required & self.omitted_reasons.keys():
            raise ValueError('Ambiguous proof scope')
        if required | self.omitted_reasons.keys() != {'FACE', 'SCALE', 'SOCIAL', 'PERFORMANCE'}:
            raise ValueError('Explain all proof responsibilities')
        if self.scope == 'COMPLETE' and not {'FACE', 'SCALE', 'SOCIAL'} <= required:
            raise ValueError('Complete candidate needs face, body/scale and social evidence')
        if self.social_identity_essential and 'SOCIAL' not in required:
            raise ValueError('Key social identity requires SOCIAL proof')
        return self

class VisualCastingPlan(ContractModel):
    profile_fingerprint: Hash
    intent: CastingIntent
    appeal: AudienceAppealMode
    discriminants: tuple[VisualDiscriminant, ...] = Field(min_length=1)
    variants: tuple[ContrastiveVariant, ...] = Field(min_length=2)
    contrast_axes: tuple[Text, ...] = Field(min_length=1)
    proof_set: CompleteCandidateProofSet
    salience_policy: RoleSaliencePolicy | None = None

    @model_validator(mode='after')
    def actual_contrast(self) -> Self:
        ds = {d.key: d for d in self.discriminants}
        if len(ds) != len(self.discriminants) or len({v.key for v in self.variants}) != len(self.variants):
            raise ValueError('Duplicate discriminant or variant')
        for channel in self.appeal.channels:
            if not set(channel.discriminant_ids) <= ds.keys():
                raise ValueError('Appeal must change a known visual/proof choice')
        if self.salience_policy and not set(self.salience_policy.defining_discriminant_ids) <= ds.keys():
            raise ValueError('Salience must preserve known discriminants')
        for axis in self.contrast_axes:
            if axis not in ds or ds[axis].stage != 'FACE' or len(set(ds[axis].choices.values())) < 2:
                raise ValueError('Contrast requires distinct face alternatives')
        for v in self.variants:
            if set(v.assignments) != {k for k, d in ds.items() if d.stage is not None}:
                raise ValueError('Every candidate must assign each visual obligation')
            if any(option not in ds[k].choices for k, option in v.assignments.items()):
                raise ValueError('Unknown visual option')
        for i, a in enumerate(self.variants):
            for b in self.variants[i + 1:]:
                if not any(a.assignments[k] != b.assignments[k] for k in self.contrast_axes):
                    raise ValueError('Candidates share all contrastive choices')
                if self.salience_policy:
                    exclusive = False
                    for k in self.contrast_axes:
                        regions = ds[k].geometric_regions
                        x, y = regions.get(a.assignments[k]), regions.get(b.assignments[k])
                        if x and y and x.measure == y.measure and (x.upper < y.lower or y.upper < x.lower):
                            exclusive = True
                    if not exclusive:
                        raise ValueError('Search requires mutually exclusive geometric regions, not different labels')
        return self

class AudienceAppealFinding(ContractModel):
    plan_fingerprint: Hash
    primary_response: Literal['LIKING', 'RESPECT', 'MIXED', 'ADMIRATION', 'AWE', 'AUTHORITY', 'SUBMISSION_ORIENTED_APPEAL']
    status: Literal['PASS', 'SHORTLIST', 'PARTIAL', 'REJECT']
    observation: Text
    proof_limit: Text
