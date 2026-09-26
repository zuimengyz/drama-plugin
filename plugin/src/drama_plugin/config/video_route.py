"""Runtime provider authority and model preference; qualification stays in V2-06.

The closed model-key vocabulary reconciles the existing adapter's NODES model
labels using its existing lower/space-to-hyphen identity rule. It is not a second
capability registry; an architecture test compares it with that registry.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Any, Self, Literal
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from drama_plugin.providers.video.registry import model_keys

# Existing MCP labels remain valid. New official IDs come from the same model
# catalogue used by the adapters, never another list in Director or environment.
MODEL_KEYS = model_keys()


def canonical_model_key(model: str) -> str:
    key = model.strip().lower().replace(' ', '-')
    if key not in MODEL_KEYS:
        raise ValueError('UNKNOWN_MODEL_KEY:' + key)
    return key


class RouteMode(StrEnum):
    AUTO = 'AUTO'
    PREFER = 'PREFER'
    PIN = 'PIN'


class PolicySource(StrEnum):
    DEFAULT_AUTO = 'DEFAULT_AUTO'
    PLUGIN_CONFIG = 'PLUGIN_CONFIG'
    PLUGIN_ENV_DEFAULT = 'PLUGIN_ENV_DEFAULT'
    TASK_OVERRIDE = 'TASK_OVERRIDE'


class VideoRoutePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    mode: RouteMode = RouteMode.AUTO
    provider: Literal['auto', 'official', 'comfy_cloud', 'seedance', 'minimax', 'vidu', 'wan', 'kling'] = 'auto'
    preferred_model: str | None = None
    fallbacks: tuple[str, ...] = ()
    source: PolicySource = PolicySource.DEFAULT_AUTO

    @field_validator('provider', mode='before')
    @classmethod
    def normalize_provider(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator('mode', mode='before')
    @classmethod
    def normalize_mode(cls, value: Any) -> Any:
        return (value.strip().upper() or 'AUTO') if isinstance(value, str) else value

    @field_validator('preferred_model', mode='before')
    @classmethod
    def preferred(cls, value: Any) -> Any:
        if value is None or isinstance(value, str) and not value.strip():
            return None
        if not isinstance(value, str) or value.strip() not in MODEL_KEYS:
            raise ValueError('UNKNOWN_MODEL_KEY:' + str(value))
        return value.strip()

    @field_validator('fallbacks', mode='before')
    @classmethod
    def fallback_list(cls, value: Any) -> tuple[str, ...]:
        values = value.split(',') if isinstance(value, str) else value or ()
        cleaned = tuple(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))
        for key in cleaned:
            if key not in MODEL_KEYS:
                raise ValueError('UNKNOWN_MODEL_KEY:' + key)
        return cleaned

    @model_validator(mode='after')
    def consistent(self) -> Self:
        if self.mode != RouteMode.AUTO and not self.preferred_model:
            raise ValueError('PREFERRED_MODEL_REQUIRED')
        object.__setattr__(self, 'fallbacks', tuple(k for k in self.fallbacks if k != self.preferred_model))
        return self

    def sequence(self) -> tuple[str, ...]:
        if self.mode == RouteMode.AUTO:
            return ()
        assert self.preferred_model
        return (self.preferred_model,) + (self.fallbacks if self.mode == RouteMode.PREFER else ())


def resolve_policy(configured: VideoRoutePolicy, task: VideoRoutePolicy | None = None) -> VideoRoutePolicy:
    # Revalidate copied models: model_copy(update=...) itself bypasses validation.
    configured = VideoRoutePolicy.model_validate(configured.model_dump())
    if task is not None and configured.source in {PolicySource.PLUGIN_CONFIG, PolicySource.PLUGIN_ENV_DEFAULT}:
        task = VideoRoutePolicy.model_validate(task.model_dump())
        if task.model_dump(exclude={'source'}) != configured.model_dump(exclude={'source'}):
            raise ValueError('EXTERNAL_ROUTE_POLICY_CONFLICT: task cannot override runtime configuration')
        return configured
    value = (task or configured).model_dump()
    if task is not None:
        value['source'] = PolicySource.TASK_OVERRIDE
    return VideoRoutePolicy.model_validate(value)


def runtime_policy(policy: VideoRoutePolicy | None = None) -> VideoRoutePolicy:
    """Re-read external authority; an omitted argument never means default AUTO.

    Explicit YAML policy can still be supplied by the normal config loader.
    Current process configuration cannot be replaced by a caller's default/PIN.
    Historical seal verification deliberately continues to use resolve_policy.
    """
    from drama_plugin.config.loader import load_config
    current = load_config().video_route_policy
    if current.source in {PolicySource.PLUGIN_CONFIG, PolicySource.PLUGIN_ENV_DEFAULT}:
        return resolve_policy(current, policy)
    return resolve_policy(policy or current)


def provider_allowed(policy: VideoRoutePolicy, provider: str) -> bool:
    from drama_plugin.providers.video.registry import registry
    if policy.provider == 'auto':
        return True
    if policy.provider == 'official':
        return registry()['providers'].get(provider, {}).get('transport') == 'http'
    return policy.provider == provider


def require_runtime_route(provider: str, model: str, *, policy: VideoRoutePolicy | None = None) -> None:
    """Live admission only; never use this to prevent polling a paid old task."""
    from drama_plugin.providers.video.registry import model_enabled, registry
    effective = runtime_policy(policy)
    key = canonical_model_key(model)
    if not provider_allowed(effective, provider):
        raise ValueError('RUNTIME_VIDEO_PROVIDER_POLICY_CONFLICT')
    if effective.mode != RouteMode.AUTO and key not in effective.sequence():
        raise ValueError('RUNTIME_VIDEO_MODEL_POLICY_CONFLICT')
    if not model_enabled(key):
        raise ValueError('MODEL_DISABLED')
    if provider != 'comfy_cloud' and registry()['models'].get(key, {}).get('provider') != provider:
        raise ValueError('MODEL_PROVIDER_MISMATCH')
