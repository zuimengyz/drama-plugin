"""Official Ark image projection using the existing Ark/Seedance credential owner."""
from __future__ import annotations
from typing import Any
from drama_plugin.config.production_routes import SEEDREAM_MODELS
from drama_plugin.providers.video.registry import settings, ProviderSettings
from drama_plugin.contracts.base import sha256_canonical

BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
ENDPOINT = '/images/generations'
CAPABILITY: dict[str, Any] = dict(provider='ark', endpoint=ENDPOINT, models=SEEDREAM_MODELS,
                  input='text_to_image', response_format='b64_json', output_format='png',
                  pixel_ranges={model: ([3686400, 16777216] if name.endswith('lite') else [921600, 4624220])
                                for name, model in SEEDREAM_MODELS.items()})


def credential() -> ProviderSettings:
    value = settings()['seedance']
    if value.status('seedance') != 'READY' or value.base_url != BASE_URL:
        raise ValueError('ARK_CREDENTIAL_OR_ENDPOINT_REQUIRED')
    return value


def image_payload(model: str, prompt: str, size: tuple[int, int], seed: int) -> dict[str, Any]:
    if model not in SEEDREAM_MODELS.values():
        raise ValueError('UNKNOWN_OFFICIAL_SEEDREAM_MODEL')
    w, h = size
    low, high = CAPABILITY['pixel_ranges'][model]
    if min(w, h) <= 0 or not 1/16 <= w/h <= 16 or not low <= w*h <= high:
        raise ValueError('SEEDREAM_SIZE_UNSUPPORTED')
    if not prompt.strip():
        raise ValueError('SEEDREAM_PROMPT_LIMIT')
    body: dict[str, Any] = dict(model=model, prompt=prompt, size=f'{w}x{h}',
                               response_format='b64_json', output_format='png', watermark=False)
    if model == SEEDREAM_MODELS['Doubao-Seedream-5.0-lite']:
        if not 0 <= seed <= 2147483647:
            raise ValueError('SEEDREAM_SEED_UNSUPPORTED')
        body.update(seed=seed, sequential_image_generation='disabled', stream=False)
    return body


def binding(frame: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    from drama_plugin.visual.frame_request import verify_compiled
    from drama_plugin.visual.image_route import execution_identity
    verify_compiled(frame)
    config = credential()
    return dict(execution=execution_identity(frame), operation='image.create',
                provider_schema=CAPABILITY, provider_schema_fingerprint=sha256_canonical(CAPABILITY),
                request_fingerprint=sha256_canonical(frame['request']),
                endpoint_fingerprint=sha256_canonical(config.base_url+ENDPOINT),
                authentication_status='CONFIGURED_NOT_VERIFIED', evidence=evidence)


def validate_binding(frame: dict[str, Any], value: dict[str, Any] | None) -> None:
    from datetime import datetime, timezone
    from drama_plugin.visual.video_selection import Evidence
    if not value or value != binding(frame, value.get('evidence', {})):
        raise ValueError('ARK_IMAGE_EXECUTION_BINDING_MISMATCH')
    if not Evidence.model_validate(value['evidence']).current(datetime.now(timezone.utc)):
        raise ValueError('ARK_IMAGE_BINDING_EXPIRED')
