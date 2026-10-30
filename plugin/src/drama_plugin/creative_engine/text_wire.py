"""Small protocol helpers for the existing OpenAI-compatible text author backend."""
import json
from pydantic import JsonValue, TypeAdapter
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.creative_engine.diagnostics import AuthorResultFailure, failure


def validate_reasoning(config, role):
    effort = config.reasoning_effort
    if effort is None:
        return
    model, provider = config.model_for(role), config.provider.strip().lower()
    # xAI official reasoning docs, checked 2026-10-30. Unknown models fail explicitly;
    # never drop or downgrade a requested setting. Existing DeepSeek policy retained.
    allowed = {'none', 'low', 'high', 'max'} if provider == 'deepseek' else set()
    if provider in {'grok', 'xai', 'x.ai'}:
        if model in {'grok-4.7', 'grok-4.6'}:
            allowed = {'low', 'medium', 'high', 'xhigh'}
        elif model == 'grok-4.5':
            allowed = {'low', 'medium', 'high'}
    if effort not in allowed:
        raise CapabilityAbsent('FORMAL_AUTHOR_REASONING_POLICY_UNSUPPORTED')


def decode_completion(content: bytes, *, streamed: bool):
    if not streamed:
        return TypeAdapter(dict[str, JsonValue]).validate_json(content)
    result = {}; text = []; finish = None; refusal = None; done = False
    for line in content.decode('utf-8').splitlines():
        if not line.startswith('data:'):
            continue  # SSE heartbeat/comments do not constitute completion.
        data = line[5:].strip()
        if data == '[DONE]':
            done = True
            break
        if not data:
            continue
        chunk = json.loads(data)
        if not isinstance(chunk, dict) or chunk.get('error'):
            raise AuthorResultFailure(failure('PROVIDER_PROTOCOL', 'AUTHOR_STREAM_INVALID'))
        for key in ('id', 'model', 'usage'):
            if key in chunk:
                if key in ('id', 'model') and key in result and result[key] != chunk[key]:
                    raise AuthorResultFailure(failure('PROVIDER_PROTOCOL', 'AUTHOR_STREAM_IDENTITY_CHANGED'))
                result[key] = chunk[key]
        for choice in chunk.get('choices', []):
            if choice.get('index', 0) != 0:
                raise AuthorResultFailure(failure('PROVIDER_PROTOCOL', 'AUTHOR_STREAM_MULTIPLE_CHOICES'))
            delta = choice.get('delta', {})
            if isinstance(delta.get('content'), str):
                text.append(delta['content'])
            if delta.get('refusal'):
                refusal = delta['refusal']
            if choice.get('finish_reason'):
                finish = choice['finish_reason']
    if not done or finish is None:
        raise AuthorResultFailure(failure('INCOMPLETE_OUTPUT', 'AUTHOR_STREAM_INCOMPLETE'))
    result['choices'] = [{'finish_reason': finish, 'message': {'role': 'assistant', 'content': ''.join(text), 'refusal': refusal}}]
    return TypeAdapter(dict[str, JsonValue]).validate_python(result)
