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

# Keep the original T2I capability seal for retained frames/bindings.
IMAGE_TO_IMAGE_CAPABILITY = {**CAPABILITY, 'input': 'image_to_image',
    'image': 'ordered_inline_base64', 'max_reference_images': 3,
    'evidence': 'https://docs.volcengine.com/docs/ark/image-generation-api?lang=zh'}
# Four distinct adopted actors need four originals. Keep retained <=3-input
# capability seals unchanged; the official Pro API permits up to ten inputs.
FOUR_REFERENCE_CAPABILITY = {**IMAGE_TO_IMAGE_CAPABILITY, 'max_reference_images': 4}


def image_capability(mode: str = 'text_to_image', *, reference_count: int = 0) -> dict[str, Any]:
    if reference_count > 4:
        raise ValueError('EXISTING_REFERENCE_PLAN_CAP_EXCEEDED')
    if mode == 'text_to_image':
        return CAPABILITY
    if mode == 'image_to_image':
        return FOUR_REFERENCE_CAPABILITY if reference_count == 4 else IMAGE_TO_IMAGE_CAPABILITY
    raise ValueError('UNKNOWN_SEEDREAM_IMAGE_MODE')


def inline_image(data: bytes) -> str:
    """Deliver exact retained PNG/JPEG bytes; no resize, crop or upload fiction."""
    import base64
    import struct
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('SEEDREAM_REFERENCE_TOO_LARGE')
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        mime='png'; width,height=struct.unpack('>II',data[16:24])
    else:
        if not data.startswith(b'\xff\xd8\xff'):
            raise ValueError('SEEDREAM_REFERENCE_FORMAT_UNSUPPORTED')
        mime='jpeg'; width=height=0; offset=2
        while offset+4<=len(data):
            if data[offset]!=255:
                break
            while offset<len(data) and data[offset]==255:
                offset+=1
            if offset>=len(data):
                break
            marker=data[offset]; offset+=1
            if marker in {0xD8,0xD9}:
                continue
            if marker==0xDA or offset+2>len(data):
                break
            length=struct.unpack('>H',data[offset:offset+2])[0]
            if length<2 or offset+length>len(data):
                break
            if marker in {0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF} and length>=7:
                height,width=struct.unpack('>HH',data[offset+3:offset+7]); break
            offset+=length
    if min(width,height)<=14 or width*height>36_000_000 or not 1/16<=width/height<=16:
        raise ValueError('SEEDREAM_REFERENCE_DIMENSIONS_UNSUPPORTED')
    return 'data:image/'+mime+';base64,'+base64.b64encode(data).decode('ascii')


def credential() -> ProviderSettings:
    value = settings()['seedance']
    if value.status('seedance') != 'READY' or value.base_url != BASE_URL:
        raise ValueError('ARK_CREDENTIAL_OR_ENDPOINT_REQUIRED')
    return value


def image_payload(model: str, prompt: str, size: tuple[int, int], seed: int,
                  *, images: tuple[str, ...] = ()) -> dict[str, Any]:
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
    if images:
        import base64
        if len(images)>4:
            raise ValueError('EXISTING_REFERENCE_PLAN_CAP_EXCEEDED')
        for value in images:
            prefix, encoded=value.split(';base64,',1)
            data=base64.b64decode(encoded,validate=True)
            if inline_image(data)!=value or prefix not in {'data:image/png','data:image/jpeg'}:
                raise ValueError('SEEDREAM_INLINE_INPUT_MISMATCH')
        body['image'] = images[0] if len(images)==1 else list(images)
    return body


def binding(frame: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    from drama_plugin.visual.frame_request import verify_compiled
    from drama_plugin.visual.image_route import execution_identity
    verify_compiled(frame)
    config = credential()
    spec=frame['spec']
    count=1 if spec.get('edit_source') else len(spec.get('references',()))
    capability=image_capability(spec.get('image_mode','text_to_image'),reference_count=count)
    return dict(execution=execution_identity(frame), operation='image.create',
                provider_schema=capability, provider_schema_fingerprint=sha256_canonical(capability),
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
