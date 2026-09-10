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
    'ByteDance2TextToVideoNode': {'model': 'Seedance 2.5', 'prompt': 'model.prompt',
        'duration': 'model.duration', 'resolution': 'model.resolution', 'ports': [], 'mode': 'TEXT_TO_VIDEO'},
    'ByteDance2FirstLastFrameNode': {'model': 'Seedance 2.5', 'prompt': 'model.prompt',
        'duration': 'model.duration', 'resolution': 'model.resolution',
        'ports': ['first_frame', 'last_frame'], 'mode': 'START_END'},
    'ByteDance2ReferenceNodeV2': {'model': 'Seedance 2.5', 'prompt': 'model.prompt',
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
    if model['type'] in {'MinimaxHailuo03FirstLastFrameNode', 'ByteDance2FirstLastFrameNode'} and len(inputs) == 1:
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
    controls = ['TEXT'] if not inputs else ['REFERENCE'] if model['type'] in {'MinimaxHailuo03ReferenceNode','ByteDance2ReferenceNodeV2'} else ['FIRST_FRAME']
    if len(inputs) == 2:
        controls.append('LAST_FRAME')
    return {'model_node': mid, 'class_type': model['type'], 'image_slots': [n for _, n in inputs],
            'controls': controls, 'input_ports': [port for port,_ in inputs],
            'mode': 'TEXT_TO_VIDEO' if not inputs else 'START_END' if len(inputs) == 2 else 'SINGLE_IMAGE',
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
    if not prompt or prompt != expected_prompt:
        raise ValueError('FROZEN_MOTION_PROMPT_REQUIRED')
    params = dict(c.parameters)
    projection = None
    if r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1':
        from drama_plugin.hosts.cinematic_projection import project
        projection = project(r,c,inspected)
        prompt = projection['prompt']
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
    validate_capability(c, r, inspected, prompt, projection)
    if projection:
        validate_reference_transport(r, bindings, inspected)
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


def verify_execution(decision: dict[str, Any], *, allow_dry_run: bool = False) -> None:
    from drama_plugin.visual.video_selection import verify_decision
    verify_decision(decision, allow_dry_run=allow_dry_run)
    a = decision['host_adapter']
    graph = json.loads(Path(a['graph_path']).read_text())
    schema = json.loads(Path(a['schema_path']).read_text())
    r = Requirements.model_validate(decision['requirements'])
    c = Candidate.model_validate(decision['candidate'])
    expected = compile_request(r, c, graph, schema, a['bindings'], r.frozen_creative['motion_prompt'])
    if r.frozen_creative.get('creative_schema') == 'cinematic-shot-v1' and decision.get('execution_contract') != seal_material(r,c,graph,schema):
        raise ValueError('SEALED_EXECUTION_CONTRACT_CHANGED')
    if decision['request'] != expected:
        raise ValueError('SELECTION_EXECUTION_MISMATCH')


def validate_capability(c: Candidate, r: Requirements, inspected: dict[str, Any], prompt: str,
                        projection: dict[str, Any] | None) -> None:
    """L1 current node metadata controls ranges, never marketing or a shared cap."""
    from datetime import datetime, timezone
    from drama_plugin.visual.video_selection import Evidence
    cap = c.capability
    is_seed = inspected['class_type'].startswith('ByteDance2')
    if is_seed and (c.variant != 'Seedance 2.5' or c.parameters.get('model') != c.variant or not cap):
        raise ValueError('SEEDANCE_VARIANT_AND_CURRENT_CAPABILITY_REQUIRED')
    if cap:
        if cap.get('fingerprint') != sha256_canonical({k:v for k,v in cap.items() if k!='fingerprint'}):
            raise ValueError('CAPABILITY_CHANGED_REQUALIFY')
        if not Evidence.model_validate(cap['evidence']).current(datetime.now(timezone.utc)):
            raise ValueError('CAPABILITY_EXPIRED_REQUALIFY')
        node = cap['node_schema']
        if node['name'] != inspected['class_type'] or cap['schema_hash'] != inspected['schema_hash'] or cap['graph_hash'] != inspected['graph_hash']:
            raise ValueError('SCHEMA_DRIFT_REQUALIFY')
        fields = {f['name']:f for f in node['input_details'] if not f.get('applies_when') or c.variant in f['applies_when']}
        for key,value in c.parameters.items():
            field = fields.get(key)
            if field is None:
                raise ValueError('PARAMETER_NOT_IN_CURRENT_NODE_SCHEMA:' + key)
            if 'options' in field and value not in field['options']:
                raise ValueError('PARAMETER_OPTION_UNSUPPORTED:' + key)
            if field['type'] == 'INT' and (type(value) is not int or value < field.get('min',value) or value > field.get('max',value)):
                raise ValueError('PARAMETER_RANGE_UNSUPPORTED:' + key)
            if field['type'] == 'BOOLEAN' and type(value) is not bool:
                raise ValueError('BOOLEAN_PARAMETER_REQUIRED:' + key)
        limit = fields[str(NODES[inspected['class_type']]['prompt'])].get('max_length')
        if limit is not None and len(prompt) > limit:
            raise ValueError('VERIFIED_PROVIDER_PROMPT_LIMIT_EXCEEDED')
    if is_seed:
        params = c.parameters
        if inspected['class_type'] == 'ByteDance2ReferenceNodeV2' and params.get('model.task_type') != 'reference':
            raise ValueError('EDIT_EXTEND_AUTO_DEFERRED')
        if inspected['class_type'] != 'ByteDance2FirstLastFrameNode':
            if params.get('model.ratio') != r.aspect_ratio:
                raise ValueError('ASPECT_RATIO_CHANGED')
        else:
            # This variant derives aspect from its endpoints; ratio is not exposed.
            ratio = r.aspect_ratio.split(':')
            if len(ratio) != 2 or any(not i.width or not i.height or abs(i.width/i.height-float(ratio[0])/float(ratio[1])) > .01 for i in r.inputs):
                raise ValueError('FLF_INPUT_DERIVED_ASPECT_UNVERIFIED')
            if params.get('first_frame_asset_id') or params.get('last_frame_asset_id'):
                raise ValueError('ASSET_ID_INPUT_OUTSIDE_PROJECT_CONTRACT')
        expected = projection['generate_audio'] if projection else r.sound != 'SILENT'
        if params.get('model.generate_audio') is not expected:
            raise ValueError('SOURCE_SOUND_PARAMETER_MISMATCH')
    elif projection:
        key = 'generate_audio' if inspected['class_type'].startswith('Flux') else 'model.generate_audio'
        if key in c.parameters and c.parameters[key] is not projection['generate_audio']:
            raise ValueError('SOURCE_SOUND_PARAMETER_MISMATCH')
        if key not in c.parameters and not projection['generate_audio']:
            raise ValueError('PROVIDER_NATIVE_AUDIO_DISABLE_NOT_EXPOSED')


def validate_reference_transport(r: Requirements, bindings: list[dict[str, Any]], inspected: dict[str, Any]) -> None:
    from drama_plugin.visual.reference_duties import validate_media_snapshot
    for inp,b,port in zip(r.inputs,bindings,inspected['input_ports'],strict=True):
        validate_media_snapshot(inp,b['formal_media'],work_id=r.work_id)
        if b.get('formal_media_fingerprint') != sha256_canonical(b['formal_media']):
            raise ValueError('FORMAL_MEDIA_READBACK_CHANGED')
        for duty in r.reference_duties:
            if duty.media_id == inp.media_id and duty.provider_slot != port:
                raise ValueError('REFERENCE_PROVIDER_SLOT_MISMATCH')


def seal_material(r: Requirements, c: Candidate, graph: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    from drama_plugin.hosts.cinematic_projection import project
    inspected = inspect_graph(graph,schema)
    projected = project(r,c,inspected)
    frozen = r.frozen_creative['cinematic_direction']
    material = {'cinematic_direction_fingerprint': frozen['fingerprint'],
        'canonical_dialogue_fingerprint': sha256_canonical(frozen.get('canonicalDialogue', [])),
        'reference_package_fingerprint': sha256_canonical([d.model_dump(mode='json') for d in r.reference_duties]),
        'qualification_fingerprint': sha256_canonical(c.model_dump(mode='json')),
        'schema_fingerprint': inspected['schema_hash'], 'template_fingerprint': inspected['graph_hash'],
        'capability_fingerprint': c.capability.get('fingerprint'),
        'duration': r.duration_seconds, 'resolution': c.parameters.get(str(NODES[inspected['class_type']]['resolution'])),
        'audio_policy': projected['generate_audio'], 'semantic_projection': projected}
    return {**material,'fingerprint':sha256_canonical(material)}


def bind_capability(node_schema: dict[str, Any], graph: dict[str, Any], schema: dict[str, Any],
                    evidence: dict[str, Any]) -> dict[str, Any]:
    """Freeze current read-only L1/L2 facts. Evidence is Host-owned, not a price."""
    inspected = inspect_graph(graph,schema)
    if node_schema['name'] != inspected['class_type']:
        raise ValueError('NODE_SCHEMA_MISMATCH')
    material = {'node_schema':node_schema,'node_id':inspected['model_node'],'model_key':str(NODES[inspected['class_type']]['model']).lower().replace(' ','-'),
                'schema_hash':inspected['schema_hash'],'graph_hash':inspected['graph_hash'],
                'evidence':evidence,'project_input_ports':inspected['input_ports']}
    return {**material,'fingerprint':sha256_canonical(material)}


def seal_execution(r: Requirements, c: Candidate, request: dict[str, Any], host: dict[str, Any]) -> dict[str, Any]:
    graph = json.loads(Path(host['graph_path']).read_text())
    schema = json.loads(Path(host['schema_path']).read_text())
    expected = compile_request(r,c,graph,schema,host['bindings'],r.frozen_creative['motion_prompt'])
    if request != expected:
        raise ValueError('REQUEST_DOES_NOT_MATCH_CANONICAL_PROJECTION')
    return seal_material(r,c,graph,schema)


# Install this inspected Host at the existing selection boundary. Core never
# imports a provider or dispatches a generation as a side effect of sealing.
from drama_plugin.visual import video_selection as _selection
_selection.execution_sealer = seal_execution
