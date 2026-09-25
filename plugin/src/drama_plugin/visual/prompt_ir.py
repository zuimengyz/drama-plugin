"""Task-specific projection of typed visual facts, with an auditable priority budget."""
from __future__ import annotations
from typing import Any
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.visual_prompt import VisualPromptIR, Fact
from drama_plugin.visual.payload_scope import review_text

RANK = {'CRITICAL': 0, 'IMPORTANT': 1, 'SECONDARY': 2}
STATIC = {'TEXT_TO_IMAGE', 'IMAGE_EDIT', 'REFERENCE_EDIT', 'FIRST_FRAME', 'KEY_FRAME'}


def compile_ir(raw: VisualPromptIR | dict[str, Any], *, provider_family: str,
               audio_supported: bool = False, hard_limit: int | None = None,
               model: str = 'visual', limit_source: str = 'provider capability',
               generator_context: dict[str, Any] | None = None,
               legacy_replay: bool = False) -> dict[str, Any]:
    ir = VisualPromptIR.model_validate(raw.model_dump() if isinstance(raw, VisualPromptIR) else raw)
    if ir.task.provider_family.casefold() != provider_family.casefold():
        raise ValueError('VISUAL_PROMPT_PROVIDER_FAMILY_MISMATCH')
    task = ir.task.task_type
    from drama_plugin.prompt_generators.registry import is_seedance2, get_generator
    seedance = task == 'VIDEO' and is_seedance2(model) and not legacy_replay
    if task == 'VIDEO' and provider_family.casefold() == 'seedance' and not seedance and not legacy_replay:
        raise ValueError('SEEDANCE_MODEL_GENERATOR_NOT_IMPLEMENTED:' + model)
    scope_task = 'VIDEO' if task == 'VIDEO' else 'IMAGE'
    rows: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []

    def add(path: str, fact: Fact, minimum: str = 'SECONDARY', *, required: bool = True,
            prefix: str = '') -> None:
        visible = fact.scope == 'CURRENT' or task == 'VIDEO' and fact.scope == 'CLIP'
        if not visible:
            if required:
                raise ValueError('VISUAL_PROMPT_REQUIRED_FIELD_NOT_EXECUTABLE:' + path)
            omitted.append({'path': path, 'reason': fact.scope}); return
        if RANK[fact.priority] > RANK[minimum]:
            raise ValueError('VISUAL_PROMPT_PRIORITY_TOO_LOW:' + path)
        review_text(fact.text, scope_task, audio=audio_supported)
        rows.append({'path': path, 'priority': fact.priority, 'text': prefix + fact.text,
                     'required': required, 'source': fact.source})
        if seedance:
            rows[-1]['scope'] = fact.scope

    add('medium', Fact(text=ir.task.visual_medium, priority='CRITICAL', source='task.visual_medium'), 'CRITICAL')
    for key in ('era', 'location', 'historical_context'):
        add('world.' + key, getattr(ir.world, key), 'CRITICAL')
    for i, fact in enumerate(ir.world.environment_rules):
        add(f'world.environment_rules[{i}]', fact, 'CRITICAL')
    for subject in ir.subjects:
        for key in ('role', 'apparent_age', 'face', 'hair', 'beard', 'body_proportions', 'costume', 'visible_condition'):
            fact = getattr(subject, key)
            if fact is not None:
                add(f'subject.{subject.id}.{key}', fact,
                    'CRITICAL' if key in {'apparent_age', 'face', 'hair', 'beard', 'body_proportions'} else 'IMPORTANT')
    for group in ('blocking', 'action', 'environment', 'camera', 'lighting'):
        obj = getattr(ir, group)
        if obj is None:
            continue
        for key in type(obj).model_fields:
            value = getattr(obj, key)
            values = value if isinstance(value, tuple) else (value,)
            for i, fact in enumerate(values):
                path = f'{group}.{key}' + (f'[{i}]' if isinstance(value, tuple) else '')
                if key == 'non_current':
                    omitted.append({'path': path, 'reason': 'NON_CURRENT_SOURCE_ONLY'}); continue
                add(path, fact, 'CRITICAL' if group in {'blocking', 'action'} else 'IMPORTANT',
                    prefix='AT CLIP START: ' if task == 'VIDEO' and group in {'blocking', 'action'} else '')
    for group in ('continuity', 'preserve'):
        for i, fact in enumerate(getattr(ir, group)):
            add(f'{group}[{i}]', fact, 'CRITICAL')
    for i, negative in enumerate(ir.negative_constraints):
        if negative.constraint.scope not in ({'CURRENT', 'CLIP'} if task == 'VIDEO' else {'CURRENT'}):
            raise ValueError('VISUAL_PROMPT_NEGATIVE_NOT_CURRENT')
        if RANK[negative.positive_target.priority] > RANK[negative.constraint.priority]:
            raise ValueError('VISUAL_PROMPT_NEGATIVE_PRIORITY_LOSS')
        add(f'positive_target[{i}]', negative.positive_target, negative.constraint.priority)
    for i, delta in enumerate(ir.edit_delta):
        # Never run positive normalization on source issues or edit operations.
        review_text(delta.region, 'IMAGE')
        add(f'edit_delta[{i}].source_issue', delta.source_issue, 'CRITICAL', prefix=delta.region + ': ')
        add(f'edit_delta[{i}].{delta.operation}', delta.target_correction, 'CRITICAL', prefix=delta.operation.upper() + ': ')
    if ir.video_temporal:
        for key in type(ir.video_temporal).model_fields:
            value = getattr(ir.video_temporal, key)
            if key == 'audio_requirements' and value and not audio_supported:
                raise ValueError('VISUAL_PROMPT_AUDIO_UNSUPPORTED')
            for i, fact in enumerate(value if isinstance(value, tuple) else (value,)):
                add(f'video.{key}[{i}]', fact, 'CRITICAL')
    for i, fact in enumerate(ir.secondary_details):
        add(f'secondary[{i}]', fact, required=False)

    if seedance:
        if provider_family.casefold() != 'seedance' or generator_context is None or hard_limit is None:
            raise ValueError('SEEDANCE_GENERATOR_CONTEXT_REQUIRED')
        generated = get_generator('seedance_2').generate(ir, rows, context=generator_context, hard_limit=hard_limit)
        prompt = generated['prompt']
        review_text(prompt, scope_task, audio=audio_supported)
        from drama_plugin.hosts.prompt_budget import budget_prompt
        _, budget = budget_prompt(prompt, prompt, model=model, limit=hard_limit, source=limit_source)
        budget['soft_budget'] = 'UNVALIDATED'
        return {'schema': 'visual-prompt-compilation-v1', 'ir': ir.model_dump(mode='json'),
                'ir_fingerprint': fp(ir.model_dump(mode='json')), 'prompt_fingerprint': fp(prompt),
                'provider_family': provider_family, 'audio_supported': audio_supported,
                'hard_limit': hard_limit, 'model': model, 'limit_source': limit_source,
                'generator_context': generator_context, **generated,
                'omitted': omitted + generated['omitted'],
                'prompt_budget': budget}

    # Edits lead with the correction operations, followed by what must survive.
    def order(row: dict[str, Any]) -> tuple[int, int]:
        path = row['path']
        group = (0 if path.startswith('edit_delta') else 1 if path.startswith('preserve') else 2) if ir.edit_delta else 0
        return group, RANK[row['priority']]
    rows.sort(key=order)
    vidu = task == 'VIDEO' and provider_family.casefold().startswith('vidu')
    if vidu:
        from drama_plugin.visual.vidu_serializer import select_rows
        rows, excluded = select_rows(ir, rows)
        omitted.extend(excluded)
    if task in STATIC:
        from drama_plugin.visual.image_serializer import select_image_rows
        rows, excluded = select_image_rows(ir, rows)
        omitted.extend(excluded)
    heading = ('IMAGE EDIT: SOURCE DELTA + PRESERVE + TARGET' if ir.edit_delta else
               'VIDEO CLIP' if task == 'VIDEO' else 'CURRENT VISIBLE FRAME' if task in {'FIRST_FRAME', 'KEY_FRAME'} else
               'TEXT TO IMAGE TARGET')
    def render(selected: list[dict[str, Any]]) -> str:
        if vidu:
            from drama_plugin.visual.vidu_serializer import render as render_vidu
            return render_vidu(ir, selected)
        if task in STATIC:
            from drama_plugin.visual.image_serializer import render_image
            return render_image(ir, selected)
        return heading + '\n' + '\n'.join(f"{r['priority']} {r['path']}: {r['text']}" for r in selected)
    full = render(rows)
    kept = list(rows)
    # Only explicitly optional SECONDARY details may leave the executable text.
    if hard_limit is not None and len(full) > hard_limit:
        for row in reversed(rows):
            if row['priority'] == 'SECONDARY' and not row['required']:
                kept.remove(row)
                omitted.append({'path': row['path'], 'reason': 'SECONDARY_BUDGET'})
                if len(render(kept)) <= hard_limit:
                    break
    from drama_plugin.hosts.prompt_budget import budget_prompt
    prompt, budget = budget_prompt(full, render(kept), model=model, limit=hard_limit, source=limit_source)
    review_text(prompt, scope_task, audio=audio_supported)
    return {'schema': 'visual-prompt-compilation-v1', 'ir': ir.model_dump(mode='json'),
            'ir_fingerprint': fp(ir.model_dump(mode='json')), 'prompt': prompt, 'prompt_fingerprint': fp(prompt),
            'provider_family': provider_family, 'audio_supported': audio_supported,
            'hard_limit': hard_limit, 'model': model, 'limit_source': limit_source,
            'retained': kept, 'omitted': omitted, 'prompt_budget': budget}


def verify_compilation(record: dict[str, Any], prompt: str, *, legacy_replay: bool = False) -> None:
    expected = compile_ir(record['ir'], provider_family=record['provider_family'],
                          audio_supported=record['audio_supported'], hard_limit=record['hard_limit'],
                          model=record['model'], limit_source=record['limit_source'],
                          generator_context=record.get('generator_context'), legacy_replay=legacy_replay)
    if expected != record or prompt != expected['prompt']:
        raise ValueError('VISUAL_PROMPT_IR_COMPILATION_CHANGED')


def require_submission_ir(snapshot: dict[str, Any], request: dict[str, Any]) -> None:
    """Legacy snapshots remain replayable, but cannot authorize new paid dispatch."""
    record = snapshot.get('prompt_ir_compilation')
    if record is None:
        record = snapshot.get('execution_contract', {}).get('semantic_projection', {}).get('prompt_ir_compilation')
    if record is None and request.get('promptCompilation', {}).get('schema') == 'visual-prompt-compilation-v1':
        record = request['promptCompilation']
    if record is None:
        raise ValueError('VISUAL_PROMPT_IR_REQUIRED_BEFORE_SUBMISSION')
    prompts: list[str] = []
    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {'prompt', 'model.prompt'} and isinstance(item, str):
                    prompts.append(item)
                else:
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
    # HTTP intent retains complete source facts; only promptCompilation is emitted.
    if request.get('tool') == 'video.create_task':
        from drama_plugin.contracts.video import VideoRequest
        from drama_plugin.visual.video_prompt import compile_request_ir
        if compile_request_ir(VideoRequest.model_validate(request['videoRequest']),
                              provider=record['provider_family'], model=record['model']) != record:
            raise ValueError('VISUAL_PROMPT_IR_COMPILATION_CHANGED')
        prompts.append(record['prompt'])
    else:
        collect(request)
    if not prompts or any(p != record['prompt'] for p in prompts):
        raise ValueError('VISUAL_PROMPT_IR_PAYLOAD_MISMATCH')
    verify_compilation(record, prompts[0])
    if snapshot.get('schema') == 'visual-frame-preflight-v1':
        # Historical frame compilations remain replayable, but new formal frame
        # dispatch must follow the selected default rather than an old Flux template.
        nodes = list(request.get('workflow', {}).values())
        generation = [n for n in nodes if n.get('class_type') not in {'LoadImage', 'SaveImage'}]
        if (snapshot.get('template', {}).get('model') != 'gpt-image-2' or len(generation) != 1
                or generation[0].get('class_type') != 'OpenAIGPTImageNodeV2'
                or generation[0].get('inputs', {}).get('model') != 'gpt-image-2'):
            raise ValueError('HERO_KEYFRAME_ROUTE_REQUIRES_GPT_IMAGE2')
