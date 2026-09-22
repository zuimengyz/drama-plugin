from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.exceptions import ConfigurationError


_SERVICE_NAMES = ("memory", "asset", "research", "production", "media", "context", "voice")


def _environment_overrides(environment: Mapping[str, str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if "DRAMA_PLUGIN_VISUAL_MEDIUM" in environment:
        medium = environment["DRAMA_PLUGIN_VISUAL_MEDIUM"].strip()
        if medium not in {"live_action", "cg"}:
            raise ConfigurationError("Invalid DRAMA_PLUGIN_VISUAL_MEDIUM: expected live_action or cg")
        overrides["visual_medium"] = medium
    if "DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT" in environment:
        overrides["visual_authority_root"] = environment["DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT"].strip()

    if "DRAMA_CHARACTER_REPOSITORY_ROOT" in environment:
        overrides["character_repository_root"] = environment["DRAMA_CHARACTER_REPOSITORY_ROOT"].strip()
    if "rhythm_speed" in environment:
        rhythm_value = environment["rhythm_speed"].strip()
        if rhythm_value not in {"work_defined", "slow", "medium", "fast"}:
            raise ConfigurationError("Invalid rhythm_speed in environment: expected work_defined, slow, medium or fast")
        overrides["rhythm_speed"] = rhythm_value
    route = {field: environment[key].strip() for field, key in {
        "mode": "DRAMA_PLUGIN_VIDEO_ROUTE_MODE",
        "preferred_model": "DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED",
        "fallbacks": "DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS",
    }.items() if key in environment}
    if route:
        overrides["video_route_policy"] = {**route, "source": "PLUGIN_ENV_DEFAULT"}
    providers: dict[str, dict[str, str]] = {}
    services: dict[str, dict[str, Any]] = {}
    for service in _SERVICE_NAMES:
        mode_key = f"DRAMA_PLUGIN_PROVIDER_{service.upper()}_MODE"
        if mode_key in environment:
            providers[service] = {"mode": environment[mode_key].strip().lower()}
        prefix = f"DRAMA_PLUGIN_SERVICE_{service.upper()}_"
        values: dict[str, Any] = {}
        if prefix + "BASE_URL" in environment:
            values["base_url"] = environment[prefix + "BASE_URL"].strip()
        if prefix + "API_TOKEN" in environment:
            values["api_token"] = environment[prefix + "API_TOKEN"].strip() or None
        if prefix + "TIMEOUT_SECONDS" in environment:
            try:
                values["timeout_seconds"] = float(environment[prefix + "TIMEOUT_SECONDS"])
            except ValueError as exc:
                raise ConfigurationError(f"Invalid timeout for service {service}") from exc
        if values:
            services[service] = values
    if providers:
        overrides["providers"] = providers
    if services:
        overrides["services"] = services
    role_values: dict[str, Any] = {}
    for key, field in {
        "FISH_AUDIO_API_KEY": "api_key", "FISH_AUDIO_BASE_URL": "base_url",
        "FISH_TTS_MODEL": "tts_model",
        "DRAMA_PLUGIN_ROLE_DUBBING_OUTPUT_DIRECTORY": "output_directory",
    }.items():
        if key in environment:
            role_values[field] = environment[key].strip()
    if role_values.get('api_key') == '':
        role_values['api_key'] = None
    if "DRAMA_PLUGIN_ROLE_DUBBING_TIMEOUT_SECONDS" in environment:
        try:
            role_values["timeout_seconds"] = float(environment["DRAMA_PLUGIN_ROLE_DUBBING_TIMEOUT_SECONDS"])
        except ValueError as exc:
            raise ConfigurationError("Invalid Fish Role Dubbing timeout") from exc
    if role_values:
        overrides.setdefault("services", {})["role_dubbing"] = role_values
    if 'DRAMA_PLUGIN_PROVIDER_AUDIO_SEMANTIC_MODE' in environment:
        overrides.setdefault('providers', {})['audio_semantic'] = {
            'mode': environment['DRAMA_PLUGIN_PROVIDER_AUDIO_SEMANTIC_MODE'].strip().lower()}
    audio_values = {field: environment[key].strip() for field, key in {
        'api_key': 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_API_KEY',
        'base_url': 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_BASE_URL',
        'model': 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_MODEL',
        'reasoning_effort': 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_REASONING_EFFORT',
        'use_multichannel': 'DRAMA_PLUGIN_PROVIDER_QWEN_OMNI_USE_MULTICHANNEL',
    }.items() if key in environment}
    if audio_values:
        overrides.setdefault('services', {})['qwen_omni'] = audio_values
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
        if isinstance(payload.get("video_route_policy"), dict):
            payload["video_route_policy"] = {**payload["video_route_policy"], "source": "PLUGIN_CONFIG"}
    source_environment = environment if environment is not None else os.environ
    merged = _deep_merge(payload, _environment_overrides(source_environment))
    try:
        config = DramaPluginConfig.model_validate(merged)
        config._visual_medium_source = ("environment:DRAMA_PLUGIN_VISUAL_MEDIUM"
            if "DRAMA_PLUGIN_VISUAL_MEDIUM" in source_environment else
            f"config:{path}:visual_medium" if "visual_medium" in payload else "UNCONFIGURED")
        config._rhythm_source = ("environment:rhythm_speed" if "rhythm_speed" in source_environment else
                                f"config:{path}:rhythm_speed" if "rhythm_speed" in payload else "default:work_defined")
        return config
    except ValidationError as exc:
        errors = exc.errors()
        if any(e['loc'][:2] in {('services', 'qwen_omni'), ('providers', 'audio_semantic')}
               or not e['loc'] for e in errors):
            # Do not chain a Pydantic exception containing the original secret input.
            raise ConfigurationError('Invalid audio semantic configuration; enabled mode requires API_KEY + HTTPS BASE_URL and valid options') from None
        if any(e["loc"] and e["loc"][0] == "rhythm_speed" for e in errors):
            raise ConfigurationError(f"Invalid rhythm_speed in configuration {path}: expected work_defined, slow, medium or fast") from None
        route_errors = [e["msg"] for e in errors if e["loc"] and e["loc"][0] == "video_route_policy"]
        if route_errors:
            raise ConfigurationError("Invalid video route policy: " + "; ".join(route_errors)) from None
        raise ConfigurationError("Invalid Drama Plugin configuration") from None
