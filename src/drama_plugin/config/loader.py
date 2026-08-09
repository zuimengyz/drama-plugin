from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.exceptions import ConfigurationError


_SERVICE_NAMES = ("project", "asset", "history", "generation", "media", "context")


def _environment_overrides(environment: Mapping[str, str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    providers: dict[str, dict[str, str]] = {}
    services: dict[str, dict[str, Any]] = {}
    for service in _SERVICE_NAMES:
        if mode := environment.get(f"DRAMA_PLUGIN_PROVIDER_{service.upper()}_MODE"):
            providers[service] = {"mode": mode.lower()}
        prefix = f"DRAMA_PLUGIN_SERVICE_{service.upper()}_"
        values: dict[str, Any] = {}
        if base_url := environment.get(prefix + "BASE_URL"):
            values["base_url"] = base_url
        if token := environment.get(prefix + "API_TOKEN"):
            values["api_token"] = token
        if timeout := environment.get(prefix + "TIMEOUT_SECONDS"):
            try:
                values["timeout_seconds"] = float(timeout)
            except ValueError as exc:
                raise ConfigurationError(f"Invalid timeout for service {service}") from exc
        if values:
            services[service] = values
    if providers:
        overrides["providers"] = providers
    if services:
        overrides["services"] = services
    return overrides


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    path: Path | str | None = None,
    environment: Mapping[str, str] | None = None,
) -> DramaPluginConfig:
    payload: dict[str, Any] = {}
    if path is not None:
        config_path = Path(path)
        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Cannot load configuration: {config_path}") from exc
        if not isinstance(raw, dict):
            raise ConfigurationError("Configuration root must be a mapping")
        payload = raw
    source_environment = environment if environment is not None else os.environ
    merged = _deep_merge(payload, _environment_overrides(source_environment))
    try:
        return DramaPluginConfig.model_validate(merged)
    except ValidationError as exc:
        raise ConfigurationError("Invalid Drama Plugin configuration") from exc
