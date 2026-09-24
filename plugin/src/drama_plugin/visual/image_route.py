"""Default formal frame route. Explicit retained templates remain replayable."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING
from drama_plugin.contracts.base import sha256_canonical
if TYPE_CHECKING:
    from drama_plugin.visual.frame_request import FrameSpec, Template, EditSource, Reference


def select_frame_template(spec: FrameSpec) -> Template:
    from drama_plugin.visual.frame_request import Template
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
