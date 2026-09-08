"""Narrow inspected-template adapter. No network or workflow construction.

Only direct LoadImage -> supported video node -> SaveVideo graphs execute.
Unknown nodes (including enhancement and regeneration branches) fail closed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.visual.video_selection import Candidate, Requirements, validate_requirements

# Provider-specific semantics stay here, never in Skill Core.
NODES = {
    'Flux3ImageToVideoNode': {'model': 'FLUX 3', 'prompt': 'prompt', 'duration': 'duration',
        'resolution': 'resolution', 'ports': ['keyframes.image_0'], 'mode': 'SINGLE_IMAGE'},
    'MinimaxHailuo03FirstLastFrameNode': {'model': 'MiniMax H3', 'prompt': 'model.prompt',
        'duration': 'model.duration', 'resolution': 'model.resolution',
        'ports': ['first_frame', 'last_frame'], 'mode': 'START_END'},
    'MinimaxHailuo03ReferenceNode': {'model': 'MiniMax H3', 'prompt': 'model.prompt',
        'duration': 'model.duration', 'resolution': 'model.resolution',
        'ports': ['model.reference_images.image_1'], 'mode': 'SINGLE_IMAGE'},
}


def inspect_graph(graph: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if graph.get('definitions') or graph.get('subgraphs'):
        raise ValueError('UNINSPECTED_SUBGRAPH')
    nodes = {str(n['id']): n for n in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        raise ValueError('DUPLICATE_GRAPH_NODE')
    models = [n for n in nodes.values() if n['type'] in NODES]
    if len(models) != 1 or any(n['type'] not in {*NODES, 'LoadImage', 'SaveVideo', 'MarkdownNote'} for n in nodes.values()):
        raise ValueError('UNVERIFIED_OR_ADDITIONAL_PAID_NODE')
    if any(n.get('mode', 0) != 0 for n in nodes.values()):
        raise ValueError('UNVERIFIED_BYPASS_MODE')
    model = models[0]; mid = str(model['id']); semantics = NODES[model['type']]
    links = {link[0]: link for link in graph['links']}
    schemas = {str(n['id']): n for n in schema['nodes']}
    if set(schemas) != {nid for nid, n in nodes.items() if n['type'] != 'MarkdownNote'}:
        raise ValueError('SCHEMA_GRAPH_NODE_MISMATCH')
    for nid, n in schemas.items():
        if n['class_type'] != nodes[nid]['type'] or n.get('inputs_truncated'):
            raise ValueError('SCHEMA_GRAPH_TYPE_OR_COMPLETENESS')
    inputs = []
    for idx, port in enumerate(model.get('inputs', [])):
        if port.get('link') is None:
            continue
        link = links[port['link']]
        if port['name'] not in semantics['ports'] or link[2] != 0 or str(link[3]) != mid or link[4] != idx or link[5] != 'IMAGE':
            raise ValueError('UNVERIFIED_INPUT_COMBINATION_OR_WIRING')
        source = str(link[1])
        if nodes[source]['type'] != 'LoadImage':
            raise ValueError('INPUT_MUST_BE_DIRECT_IMAGE')
        inputs.append((port['name'], source))
    expected = list(semantics['ports'])
    if model['type'] == 'MinimaxHailuo03FirstLastFrameNode' and len(inputs) == 1:
        expected = ['first_frame']
    if [p for p, _ in inputs] != expected:
        raise ValueError('UNVERIFIED_INPUT_MODE')
    if {n for _, n in inputs} != {nid for nid, n in nodes.items() if n['type'] == 'LoadImage'}:
        raise ValueError('UNBOUND_OR_DUPLICATE_INPUT')
    saves = [n for n in nodes.values() if n['type'] == 'SaveVideo']
    if not saves:
        raise ValueError('NO_VIDEO_OUTPUT')
    used_links = {p['link'] for p in model.get('inputs', []) if p.get('link') is not None}
    for n in saves:
        port = next(p for p in n['inputs'] if p['name'] == 'video')
        link = links[port['link']]
        if str(link[1]) != mid or link[2] != 0 or str(link[3]) != str(n['id']) or link[4] != 0 or link[5] != 'VIDEO':
            raise ValueError('OUTPUT_NOT_NATIVE_VIDEO')
        used_links.add(port['link'])
    if set(links) != used_links:
        raise ValueError('UNINSPECTED_GRAPH_LINK')
    controls = ['REFERENCE'] if model['type'] == 'MinimaxHailuo03ReferenceNode' else ['FIRST_FRAME']
    if len(inputs) == 2:
        controls.append('LAST_FRAME')
    return {'model_node': mid, 'class_type': model['type'], 'image_slots': [n for _, n in inputs],
            'controls': controls, 'mode': 'START_END' if len(inputs) == 2 else 'SINGLE_IMAGE',
            'adapter_source_hash': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'graph_hash': sha256_canonical(graph), 'schema_hash': sha256_canonical(schema),
            'paid_nodes': [mid], 'output_copies': len(saves)}


def compile_request(r: Requirements, c: Candidate, graph: dict[str, Any], schema: dict[str, Any],
                    bindings: list[dict[str, Any]], prompt: str) -> dict[str, Any]:
    validate_requirements(r)
    inspected = inspect_graph(graph, schema)
    if schema['id'] != c.template:
        raise ValueError('TEMPLATE_ID_CHANGED')
    if c.graph_hash != inspected['graph_hash'] or c.adapter_fingerprint != sha256_canonical(inspected):
        raise ValueError('ADAPTER_OR_GRAPH_CHANGED')
    if (r.mode != inspected['mode'] or not set(inspected['controls']) <= set(r.controls)
            or not set(r.controls) <= set(inspected['controls']) | {'NATIVE_AUDIO'}):
        raise ValueError('REQUEST_CONTROL_MISMATCH')
    if len(bindings) != len(r.inputs) or len(bindings) != len(inspected['image_slots']):
        raise ValueError('INPUT_COUNT_MISMATCH')
    mid = inspected['model_node']; kind = inspected['class_type']; semantics = NODES[kind]
    if c.model != semantics['model']:
        raise ValueError('MODEL_MISMATCH')
    if kind.startswith('Minimax') and c.variant != 'MiniMax H3':
        raise ValueError('VARIANT_REQUIRES_SEPARATE_ADAPTER')
    if kind.startswith('Flux') and c.variant != 'FLUX 3':
        raise ValueError('VARIANT_MISMATCH')
    expected_prompt = r.frozen_creative.get('motion_prompt')
    if not prompt or prompt != expected_prompt or len(prompt) > 2000:
        raise ValueError('FROZEN_MOTION_PROMPT_REQUIRED')
    params = dict(c.parameters)
    if str(params.get(str(semantics['duration']))) != str(r.duration_seconds):
        raise ValueError('NARRATIVE_DURATION_CHANGED')
    if semantics['prompt'] in params or 'seed' not in params:
        raise ValueError('PROMPT_OVERRIDE_OR_SEED_MISSING')
    schema_node = next(n for n in schema['nodes'] if str(n['id']) == mid)
    allowed = set(schema_node['inputs'])
    if not set(params) <= allowed:
        raise ValueError('UNEXPOSED_PARAMETER')
    # Do not inherit unrecorded defaults, price controls, or a demo prompt.
    if set(params) | {str(semantics['prompt'])} != allowed:
        raise ValueError('UNFROZEN_TEMPLATE_DEFAULT')
    if kind.startswith('Minimax') and params.get('model') != c.variant:
        raise ValueError('REQUEST_VARIANT_MISMATCH')
    if kind.startswith('Flux'):
        if params.get('placement') != 'spread across the clip' or params.get('aspect_ratio') != r.aspect_ratio:
            raise ValueError('PLACEMENT_OR_ASPECT_CHANGED')
        if params.get('generate_audio') is not (r.sound != 'SILENT'):
            raise ValueError('SOUND_SCHEME_CHANGED')
    overrides: dict[str, Any] = {mid: {**params, str(semantics['prompt']): prompt}}
    for inp, b, slot in zip(r.inputs, bindings, inspected['image_slots'], strict=True):
        if any(b.get(k) != getattr(inp, k) for k in ['media_id', 'version', 'content_hash', 'state']):
            raise ValueError('REFERENCE_STATE_CHANGED')
        digest = hashlib.sha256(Path(b['local_path']).read_bytes()).hexdigest()
        receipt = json.loads(Path(b['upload_receipt']).read_text())
        if digest != inp.content_hash or receipt.get('content_hash') != digest or receipt.get('name') != b['upload_name']:
            raise ValueError('INPUT_BYTES_OR_UPLOAD_RECEIPT_MISMATCH')
        overrides[slot] = {'image': b['upload_name']}
    if len({b['upload_name'] for b in bindings}) != len(bindings):
        raise ValueError('DUPLICATE_UPLOAD')
    return {'tool': 'run_template', 'name': c.template, 'description': r.target_id + '-video',
            'input_overrides': overrides}


def verify_execution(decision: dict[str, Any]) -> None:
    from drama_plugin.visual.video_selection import verify_decision
    verify_decision(decision)
    a = decision['host_adapter']
    graph = json.loads(Path(a['graph_path']).read_text())
    schema = json.loads(Path(a['schema_path']).read_text())
    r = Requirements.model_validate(decision['requirements'])
    c = Candidate.model_validate(decision['candidate'])
    expected = compile_request(r, c, graph, schema, a['bindings'], r.frozen_creative['motion_prompt'])
    if decision['request'] != expected:
        raise ValueError('SELECTION_EXECUTION_MISMATCH')
