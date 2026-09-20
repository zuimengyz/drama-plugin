"""Data-backed capabilities. Admission only; selection remains visual.video_selection."""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, cast
from urllib.parse import urlsplit
from pydantic import BaseModel, SecretStr, Field
from drama_plugin.contracts.video import VideoRequest
from drama_plugin.contracts.base import sha256_canonical


def registry() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(__file__).with_name('registry.json').read_text()))


def model_keys() -> frozenset[str]:
    data = registry()
    return frozenset(set(data['models']) | set(data['legacy_model_keys']))


def model_enabled_env(model: str) -> str:
    key = model.strip().lower().replace(' ', '-')
    if key not in model_keys():
        raise ValueError('UNKNOWN_MODEL_KEY:' + key)
    return 'DRAMA_VIDEO_MODEL_' + re.sub(r'[^A-Z0-9]', '_', key.upper()) + '_ENABLED'


def model_enabled(model: str, environ: Mapping[str, str] | None = None) -> bool:
    """An explicit false/empty/invalid flag fails closed; old deployments default true."""
    env = os.environ if environ is None else environ
    return env.get(model_enabled_env(model), 'true').strip().lower() == 'true'


def model_availability(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    configuration = settings(environ)
    models = registry()['models']
    return {key: {'enabled': model_enabled(key, environ), 'enabled_env': model_enabled_env(key),
                  'status': ('DISABLED' if not model_enabled(key, environ) else
                             configuration[models[key]['provider']].status(models[key]['provider']) if key in models else 'MCP_DISCOVERY_REQUIRED')}
            for key in sorted(model_keys())}


class ProviderSettings(BaseModel):
    api_key: SecretStr | None = Field(default=None, repr=False)
    base_url: str = ''

    def status(self, provider: str) -> str:
        if not self.api_key or not self.api_key.get_secret_value().strip() or not self.base_url:
            return 'NOT_CONFIGURED'
        spec = registry()['providers'][provider]
        try:
            u = urlsplit(self.base_url)
            port = u.port
        except ValueError:
            return 'INVALID_ENDPOINT'
        official = u.hostname in spec['hosts'] or bool(spec.get('host_pattern') and re.fullmatch(spec['host_pattern'], u.hostname or ''))
        if not official or u.scheme != 'https' or u.username or u.password or u.query or u.fragment or port not in (None, 443):
            return 'INVALID_ENDPOINT'
        if provider == 'wan' and u.path.rstrip('/') != '/api/v1':
            return 'INVALID_ENDPOINT'
        return 'READY'


def settings(environ: Mapping[str, str] | None = None) -> dict[str, ProviderSettings]:
    env = os.environ if environ is None else environ
    return {p: ProviderSettings(api_key=SecretStr(env[f'DRAMA_VIDEO_{p.upper()}_API_KEY']) if env.get(f'DRAMA_VIDEO_{p.upper()}_API_KEY') else None,
                               base_url=env.get(f'DRAMA_VIDEO_{p.upper()}_BASE_URL', spec['base_url']).rstrip('/'))
            for p, spec in registry()['providers'].items() if spec['transport'] == 'http'}


def capability_errors(request: VideoRequest, model: str) -> list[str]:
    m = registry()['models'].get(model)
    if m is None:
        return ['UNKNOWN_OFFICIAL_MODEL']
    r = request
    errors = []
    for valid, code in ((r.input_mode in m['input_modes'], 'INPUT_MODE'),
                        (r.duration in m['durations'], 'DURATION'),
                        (r.resolution.lower() in m['resolutions'], 'RESOLUTION'),
                        (r.aspect_ratio in m['aspect_ratios'], 'ASPECT_RATIO'),
                        (r.native_audio in m['native_audio'], 'NATIVE_AUDIO'),
                        (r.seed is None or m['seed'], 'SEED')):
        if not valid:
            errors.append('UNSUPPORTED_' + code)
    collections = (r.reference_images, r.reference_videos, r.reference_audios)
    if any(len(refs) > maximum for refs, maximum in zip(collections, m['reference_limits'])):
        errors.append('REFERENCE_COUNT_EXCEEDED')
    if sum(map(len, collections)) > m.get('reference_total', 100):
        errors.append('REFERENCE_TOTAL_EXCEEDED')
    if (r.first_frame or r.last_frame) and any(collections) and not m['endpoint_reference_mix']:
        errors.append('ENDPOINT_REFERENCE_MODES_EXCLUSIVE')
    if r.reference_audios and m.get('audio_requires_visual') and not (r.reference_images or r.reference_videos):
        errors.append('AUDIO_REQUIRES_VISUAL_REFERENCE')
    for refs, total in ((r.reference_videos, m.get('reference_video_total')), (r.reference_audios, m.get('reference_audio_total'))):
        if refs and total:
            if any(x.duration is None or x.duration < m.get('reference_min_duration', 0) for x in refs):
                errors.append('REFERENCE_DURATION_UNVERIFIED')
            elif sum(x.duration or 0 for x in refs) > total:
                errors.append('REFERENCE_DURATION_EXCEEDED')
    if r.reference_videos and m.get('input_output_video_total') and r.duration + sum(x.duration or 0 for x in r.reference_videos) > m['input_output_video_total']:
        errors.append('INPUT_OUTPUT_DURATION_EXCEEDED')
    if r.input_mode == 'reference' and r.duration < m.get('reference_min_output_duration', 0):
        errors.append('REFERENCE_OUTPUT_DURATION_UNSUPPORTED')
    if r.reference_videos and len(r.reference_images) > m.get('reference_video_images', 100):
        errors.append('REFERENCE_VIDEO_IMAGE_COMBINATION_EXCEEDED')
    if r.reference_videos and r.native_audio not in m.get('reference_video_audio', [False, True]):
        errors.append('REFERENCE_VIDEO_AUDIO_UNSUPPORTED')
    if r.reference_videos and m.get('feature_video_requires_multi_shot') and r.input_mode != 'edit' and r.provider_hints.get('multi_shot') is not True:
        errors.append('REFERENCE_VIDEO_REQUIRES_EXPLICIT_MULTI_SHOT')
    if r.input_mode in {'edit','extend'} and not r.reference_videos:
        errors.append('VIDEO_REQUIRED_FOR_EDIT_OR_EXTEND')
    if r.input_mode == 'edit' and m.get('feature_video_requires_multi_shot') and r.provider_hints.get('multi_shot'):
        errors.append('EDIT_FORBIDS_MULTI_SHOT')
    if m.get('duration_from_video') and (len(r.reference_images) != 1 or len(r.reference_videos) != 1 or r.reference_audios
            or r.reference_videos[0].duration != r.duration or r.provider_hints.get('allow_duration_truncation') is not True):
        errors.append('MOTION_TRANSFER_REQUIRES_ONE_IMAGE_VIDEO_AND_DURATION_CONSENT')
    allowed_hints = set(m.get('provider_hints', []))
    if set(r.provider_hints) - allowed_hints or any(not isinstance(v, bool) for v in r.provider_hints.values()):
        errors.append('UNSUPPORTED_PROVIDER_HINT')
    if r.first_frame and m.get('endpoint_ratio'):
        if not r.first_frame.width or not r.first_frame.height:
            errors.append('ENDPOINT_ASPECT_UNVERIFIED')
        else:
            a, b = map(int, r.aspect_ratio.split(':'))
            if abs(r.first_frame.width / r.first_frame.height - a / b) > .02:
                errors.append('ENDPOINT_ASPECT_MISMATCH')
    return errors


def continuity_errors(r: VideoRequest, provider: str, model: str) -> list[str]:
    p = r.continuity
    canonical = {x.media_id: x for x in p.references}
    if p.accepted_previous_last_frame:
        canonical[p.accepted_previous_last_frame.media_id] = p.accepted_previous_last_frame
    supplied = {x.media_id: x for x in r.references()}
    errors = []
    if p.primary_provider != 'comfy_cloud' and registry()['models'].get(p.primary_model, {}).get('provider') != p.primary_provider:
        errors.append('PRIMARY_MODEL_PROVIDER_INVALID')
    if any(canonical.get(k) != v for k, v in supplied.items()):
        errors.append('NON_CANONICAL_REFERENCE')
    if not set(p.required_reference_ids) <= set(supplied):
        errors.append('REQUIRED_CONTINUITY_BUNDLE_MISSING')
    if p.characters and p.identity_critical and not any('identity' in x.semantics and x.kind == 'image' for x in supplied.values()):
        errors.append('IDENTITY_CRITICAL_REQUIRES_VISUAL_ANCHOR')
    switching = (provider, model) != (p.primary_provider, p.primary_model)
    if switching:
        evidence = r.switch_evidence
        if not evidence or (not evidence.at_shot_boundary and r.input_mode not in {'edit','extend'}):
            errors.append('SWITCH_REQUIRES_BOUNDARY_AND_CAPABILITY_GAP')
        elif p.primary_provider != 'comfy_cloud' and (evidence.primary_capability_gap == 'UNKNOWN_OFFICIAL_MODEL' or evidence.primary_capability_gap not in capability_errors(r, p.primary_model)):
            errors.append('PRIMARY_CAPABILITY_GAP_NOT_PROVEN')
        if not any(x.kind == 'image' for x in supplied.values()):
            errors.append('TEXT_ONLY_MODEL_SWITCH_FORBIDDEN')
        previous = p.accepted_previous_last_frame
        if previous and (not r.first_frame or r.first_frame != previous):
            # Reference mode may consume the bridge when strict endpoints exclude
            # the required canonical bundle. Record it, never silently drop it.
            if previous.media_id not in supplied:
                errors.append('PREVIOUS_ACCEPTED_FRAME_BRIDGE_REQUIRED')
    return errors


def validate_request(request: VideoRequest, provider: str, model: str) -> VideoRequest:
    r = VideoRequest.model_validate(request.model_dump())
    m = registry()['models'].get(model, {})
    errors = capability_errors(r, model) + continuity_errors(r, provider, model)
    if model in model_keys() and not model_enabled(model):
        errors.append('MODEL_DISABLED')
    if m.get('provider') != provider:
        errors.append('MODEL_PROVIDER_MISMATCH')
    if errors:
        raise ValueError(';'.join(dict.fromkeys(errors)))
    return r


def fingerprint(model: str) -> str:
    import hashlib
    data = registry()
    m = data['models'][model]
    code = {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in ('base.py','adapters.py','registry.py')}
    return sha256_canonical({'model': m, 'provider': data['providers'][m['provider']], 'checked_at': data['checked_at'],
                             'adapter_code':code, 'contract_schema':VideoRequest.model_json_schema()})
