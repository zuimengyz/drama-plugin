"""Default formal frame route. Explicit retained templates remain replayable."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING
from drama_plugin.contracts.base import sha256_canonical
if TYPE_CHECKING:
    from drama_plugin.visual.frame_request import FrameSpec, Template, EditSource, Reference


def execution_identity(compiled: dict[str, Any]) -> dict[str, Any]:
    """Existing image adapter identity; does not mutate or reseal the frame."""
    model = compiled['template']['model']
    if compiled['template'].get('http_provider') == 'ark':
        return {'transport': 'HTTP', 'backend': {'provider': 'ark', 'backend_key': 'ark'},
                'capability': {'kind': 'image_generation', 'model_key': model}, 'mcp': None}
    return {'transport': 'MCP', 'backend': {'provider': 'comfy_cloud', 'backend_key': 'comfy_cloud'},
            'capability': {'kind': 'image_generation', 'model_key': model},
            'mcp': {'capability_key': 'image_generation:' + model}}


def select_frame_template(spec: FrameSpec) -> Template:
    from drama_plugin.visual.frame_request import Template
    from drama_plugin.config.production_routes import selected
    from drama_plugin.providers.ark_image import CAPABILITY
    route = selected()
    if route['image_provider'] == 'ark':
        import math
        width, height = spec.target_size
        if min(width, height) <= 0:
            raise ValueError('INVALID_FRAME_SIZE')
        # Preserve framing/aspect; only raise raster resolution to the API minimum.
        minimum = CAPABILITY['pixel_ranges'][route['image_model']][0]
        factor = max(1, math.ceil(math.sqrt(minimum/(width*height))))
        return Template(name='ark-official-seedream', model=route['image_model'],
            evidence='Ark official image-generation-api and model-list; no realized quality claim',
            graph_hash=sha256_canonical(CAPABILITY), graph_path='ark:image-generation-v1',
            image_slots=(), prompt_node='prompt', output_size=(width*factor, height*factor),
            supported_types=(spec.shot_type,), http_provider='ark')
    width, height = spec.target_size
    if any(v < 480 or v > 3840 or v % 16 for v in (width, height)):
        raise ValueError('GPT_IMAGE2_CUSTOM_SIZE_UNSUPPORTED')
    source = Path(__file__).with_name('gpt_image2_template.json')
    graph = json.loads(source.read_text())
    refs: tuple[EditSource | Reference, ...] = (spec.edit_source,) if spec.edit_source else spec.references
    slots = tuple(f'ref{i+1}' for i in range(len(refs)))
    inputs: dict[str, Any] = {'prompt': '', 'model': 'gpt-image-2', 'model.size': 'Custom',
        'model.custom_width': width, 'model.custom_height': height, 'model.background': 'opaque',
        'model.quality': 'high', 'n': 1, 'seed': spec.seed}
    api: dict[str, Any] = {'271': {'class_type': 'OpenAIGPTImageNodeV2', 'inputs': inputs},
                          'output': {'class_type': 'SaveImage', 'inputs': {'images': ['271', 0],
                                                                       'filename_prefix': 'hero_keyframe'}}}
    for i, (slot, ref) in enumerate(zip(slots, refs), 1):
        api[slot] = {'class_type': 'LoadImage', 'inputs': {'image': ref.upload_name}}
        inputs[f'model.images.image_{i}'] = [slot, 0]
    return Template(name='api_openai_gpt_image_2_t2i', model='gpt-image-2',
        evidence='Comfy MCP 2026-09-24 get_template_schema + OpenAIGPTImageNodeV2; explicit GPT Image 2, optional reference inputs; no quality PASS claim',
        graph_hash=sha256_canonical(graph), graph_path=str(source), image_slots=slots,
        prompt_node='271', output_size=spec.target_size, supported_types=(spec.shot_type,), api_workflow=api)
