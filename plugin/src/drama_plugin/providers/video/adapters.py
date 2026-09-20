"""Official vendor request translations. Endpoint/model data live in registry.json."""
from typing import Any
from .base import HttpVideoProvider, SafeProviderError, prompt_text
from drama_plugin.contracts.video import VideoRequest, ProviderTask


def content_items(r: VideoRequest, urls: dict[str, str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [{'type':'text', 'text':prompt_text(r)}]
    for ref in r.references():
        role = 'first_frame' if ref == r.first_frame else 'last_frame' if ref == r.last_frame else 'reference_' + ref.kind
        kind = ref.kind + '_url'
        items.append({'type':kind, kind:{'url':urls[ref.media_id]}, 'role':role})
    return items


class SeedanceProvider(HttpVideoProvider):
    provider = 'seedance'

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        body = dict(model=self.model_spec['vendor_model'], content=content_items(r, urls), duration=r.duration,
                    resolution=r.resolution.lower(), ratio=r.aspect_ratio, generate_audio=r.native_audio, watermark=False)
        if r.seed is not None:
            body['seed'] = r.seed
        return body

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        return self.result(task, task_id=raw.get('id'), state=raw.get('status'), url=(raw.get('content') or {}).get('video_url'),
                           created=raw.get('created_at'), completed=raw.get('updated_at'), duration=raw.get('duration'),
                           resolution=raw.get('resolution'), fps=raw.get('framespersecond'), usage=raw.get('usage'), error=raw.get('error'))


class MiniMaxProvider(HttpVideoProvider):
    provider = 'minimax'

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        return dict(model=self.model_spec['vendor_model'], content=content_items(r, urls), duration=r.duration,
                    resolution=r.resolution.upper(), ratio='adaptive' if r.first_frame else r.aspect_ratio)

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        value = raw.get('task', raw)
        return self.result(task, task_id=value.get('id', value.get('task_id')), state=value.get('status'),
                           url=(value.get('content') or {}).get('url'), created=value.get('created_at'), completed=value.get('updated_at'),
                           duration=value.get('duration'), resolution=value.get('resolution'), usage=value.get('usage'), error=value.get('error'))


class ViduProvider(HttpVideoProvider):
    provider = 'vidu'

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        body = dict(model=self.model_spec['reference_model'] if r.input_mode == 'reference' else self.model_spec['vendor_model'],
                    prompt=prompt_text(r), duration=r.duration, resolution=r.resolution.lower(), audio=r.native_audio)
        if r.references():
            body['images'] = [urls[x.media_id] for x in r.references()]
        if not r.first_frame:
            body['aspect_ratio'] = r.aspect_ratio
        if r.seed is not None:
            body['seed'] = r.seed
        return body

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        creation: dict[str, Any] = next(iter(raw.get('creations') or []), {})
        video = creation.get('video') or {}
        # Credits are a provider usage unit, never labelled USD/CNY cash.
        credits = raw.get('credits')
        return self.result(task, task_id=raw.get('id', raw.get('task_id')), state=raw.get('state'), url=creation.get('url'),
                           created=raw.get('created_at'), duration=video.get('duration', raw.get('duration')),
                           resolution=raw.get('resolution'), fps=video.get('fps'), error=raw.get('err_code'),
                           usage={'credits':float(credits)} if credits is not None else {})


class WanProvider(HttpVideoProvider):
    provider = 'wan'

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        inp: dict[str, Any] = {'prompt':prompt_text(r)}
        if r.references():
            inp['media'] = [{'type': x['role'], 'url':x[x['type']]['url']} for x in content_items(r, urls)[1:]]
        params = dict(duration=r.duration, resolution=r.resolution.upper(), ratio=r.aspect_ratio,
                      audio=r.native_audio, prompt_extend=False)
        if r.seed is not None:
            params['seed'] = r.seed
        return dict(model=self.model_spec['vendor_model'], input=inp, parameters=params)

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        o, u = raw.get('output') or {}, raw.get('usage') or {}
        return self.result(task, task_id=o.get('task_id'), state=o.get('task_status'), url=o.get('video_url'),
                           created=o.get('submit_time'), started=o.get('scheduled_time'), completed=o.get('end_time'), china=True,
                           duration=u.get('output_video_duration', u.get('duration')), resolution=str(u['SR'])+'p' if u.get('SR') else None,
                           fps=u.get('fps'), usage=u, error=o.get('code', raw.get('code')))


class KlingProvider(HttpVideoProvider):
    provider = 'kling'

    def create_path(self, r: VideoRequest) -> str:
        if self.model_spec['endpoint_reference_mix']:
            return '/omni-video/' + str(self.model_spec['vendor_model'])
        return super().create_path(r)

    def payload(self, r: VideoRequest, urls: dict[str, str], client_id: str) -> dict[str, Any]:
        settings: dict[str, Any] = dict(resolution=r.resolution.lower(), duration=r.duration)
        options = dict(external_task_id=client_id, watermark_info={'enabled':False})
        # Turbo has no documented audio/multi-shot switches.
        if self.model_spec['native_audio'] == [False, True]:
            settings.update(audio='native' if r.native_audio else 'off', multi_shot=r.provider_hints.get('multi_shot', False))
        if r.input_mode == 'text_to_video' and not self.model_spec['endpoint_reference_mix']:
            return dict(prompt=prompt_text(r), settings={**settings, 'aspect_ratio':r.aspect_ratio}, options=options)
        items = [{'type':'prompt', 'text':prompt_text(r)}]
        for ref in r.references():
            kind = 'first_frame' if ref == r.first_frame else 'last_frame' if ref == r.last_frame else 'refer_image' if ref.kind == 'image' else 'base_video' if r.input_mode == 'edit' else 'feature_video'
            if r.input_mode == 'motion_transfer':
                kind = ref.kind
            items.append({'type':kind, 'url':urls[ref.media_id]})
        if r.input_mode == 'motion_transfer':
            settings = dict(resolution=r.resolution.lower(), character_orientation='video', audio='off')
        elif not r.first_frame and not r.reference_videos:
            settings['aspect_ratio'] = r.aspect_ratio
        return dict(contents=items, settings=settings, options=options)

    async def recover_task(self, task: ProviderTask) -> ProviderTask:
        self.check_identity(task)
        try:
            raw = await self._http('GET', '/tasks', params={'external_task_ids':task.client_request_id})
        except SafeProviderError:
            return task
        matches = [x for x in raw.get('data', []) if x.get('external_id') == task.client_request_id]
        if len(matches) != 1:
            return task  # Empty lookup is not proof of non-creation.
        return self.normalize({'code':0,'data':matches[0]}, task)

    def normalize(self, raw: dict[str, Any], task: ProviderTask) -> ProviderTask:
        if raw.get('code', 0) != 0:
            raise SafeProviderError('KLING_API_ERROR', ambiguous=task.provider_task_id is None)
        d = raw.get('data') or {}
        if isinstance(d, list):
            matches = [x for x in d if x.get('id') == task.provider_task_id]
            if len(matches) != 1:
                raise SafeProviderError('KLING_TASK_LOOKUP_UNRESOLVED', retryable=True)
            d = matches[0]
        output: dict[str, Any] = next((x for x in d.get('outputs', []) if x.get('type') == 'video'), {})
        bills = d.get('billing', [])
        currencies = {x.get('currency') for x in bills if x.get('charge_type') == 'cash'}
        cash = sum(float(x['amount']) for x in bills) if bills and all(x.get('charge_type') == 'cash' for x in bills) and len(currencies) == 1 else None
        return self.result(task, task_id=d.get('id'), state=d.get('status'), url=output.get('url'),
                           created=d.get('create_time'), completed=d.get('update_time'), milliseconds=True,
                           duration=output.get('duration'), actual_cost=cash, currency=next(iter(currencies)) if cash is not None else None)


ADAPTERS = {p.provider:p for p in (SeedanceProvider, MiniMaxProvider, ViduProvider, WanProvider, KlingProvider)}
