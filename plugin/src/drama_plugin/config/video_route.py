"""Typed preference only. Capability, cost and quality belong to V2-06.

The closed model-key vocabulary reconciles the existing adapter's NODES model
labels using its existing lower/space-to-hyphen identity rule. It is not a second
capability registry; an architecture test compares it with that registry.
"""
from __future__ import annotations
from enum import StrEnum
from typing import Any, Self
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

MODEL_KEYS = frozenset({'seedance-2.5', 'minimax-h3', 'flux-3'})


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
    PLUGIN_ENV_DEFAULT = 'PLUGIN_ENV_DEFAULT'
    TASK_OVERRIDE = 'TASK_OVERRIDE'


class VideoRoutePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    mode: RouteMode = RouteMode.AUTO
    preferred_model: str | None = None
    fallbacks: tuple[str, ...] = ()
    source: PolicySource = PolicySource.DEFAULT_AUTO

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
    value = (task or configured).model_dump()
    if task is not None:
        value['source'] = PolicySource.TASK_OVERRIDE
    return VideoRoutePolicy.model_validate(value)
