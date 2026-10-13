"""Default formal frame route. Explicit retained templates remain replayable."""
from __future__ import annotations
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
    from drama_plugin.providers.ark_image import CAPABILITY, image_capability
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
            graph_hash=sha256_canonical(image_capability(spec.image_mode,
                reference_count=len((spec.edit_source,) if spec.edit_source else spec.references))), graph_path='ark:image-generation-v1',
            image_slots=tuple(f'ref{i+1}' for i in range(len((spec.edit_source,) if spec.edit_source else spec.references))),
            prompt_node='prompt', output_size=(width*factor, height*factor),
            supported_types=(spec.shot_type,), http_provider='ark')
    # Explicit historical templates still replay through compile_frame. The
    # default new-image selector must never rebuild a retired Comfy fallback.
    raise ValueError('COMFY_CLOUD_RETIRED')
