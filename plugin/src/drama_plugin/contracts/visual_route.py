"""Opt-in visual-route sidecars. Existing canon and approval schemas stay byte-stable."""
from typing import Literal, Self, Annotated
from pydantic import Field, model_validator
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash

VisualRoute = Literal['live_action_realist', 'stylized_cinematic_cg', 'stylized_animation', 'hybrid'] | Annotated[str, Field(pattern=r'^provider:[a-z][a-z0-9_.-]+$')]


class ProjectVisualRoutes(ContractModel):
    work_id: Text
    revision: Text
    # New project declarations require an authored route; never infer medium.
    visual_route: VisualRoute
    enabled_routes: tuple[VisualRoute, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def enabled_default(self) -> Self:
        if self.visual_route not in self.enabled_routes or len(set(self.enabled_routes)) != len(self.enabled_routes):
            raise ValueError('ROUTE_DEFAULT_NOT_ENABLED_OR_DUPLICATED')
        return self


class SequenceVisualRoute(ContractModel):
    work_id: Text
    sequence_key: Text
    visual_route: VisualRoute | None = None
    override_reason: Text | None = None

    @model_validator(mode='after')
    def explicit_reason(self) -> Self:
        if self.visual_route is not None and not self.override_reason:
            raise ValueError('SEQUENCE_ROUTE_OVERRIDE_REASON_REQUIRED')
        return self


class ResolvedVisualRoute(ContractModel):
    work_id: Text
    sequence_key: Text
    visual_route: VisualRoute
    project_fingerprint: Hash
    sequence_fingerprint: Hash
    inherited: bool


class RouteStyleContract(ContractModel):
    visual_route: VisualRoute
    revision: Text
    medium: Literal['PHOTOGRAPHIC', 'DESIGNED_CG', 'DESIGNED_ANIMATION', 'HYBRID', 'PROVIDER_DEFINED']
    rendering: Text
    casting_criteria: tuple[Text, ...] = Field(min_length=1)
    shape_language: Text
    material_palette: Text
    camera_grammar: Text
    performance_grammar: Text
    historical_boundary: Text
    forbidden_drifts: tuple[Text, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def medium_matches(self) -> Self:
        expected = {'live_action_realist':'PHOTOGRAPHIC', 'stylized_cinematic_cg':'DESIGNED_CG', 'stylized_animation':'DESIGNED_ANIMATION', 'hybrid':'HYBRID'}.get(self.visual_route, 'PROVIDER_DEFINED')
        if self.medium != expected:
            raise ValueError('VISUAL_ROUTE_MEDIUM_MISMATCH')
        return self


class RouteContext(ContractModel):
    project: ProjectVisualRoutes
    sequence: SequenceVisualRoute
    style: RouteStyleContract


class RouteCastingContext(RouteContext):
    character_identity: Text
    profile_fingerprint: Hash
    plan_fingerprint: Hash
