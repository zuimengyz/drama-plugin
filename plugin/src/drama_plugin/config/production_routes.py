"""Fixed production families with explicit model choices; no credential copies.

This is live admission policy, not historical receipt/replay policy.
"""
from __future__ import annotations
import os
from typing import Mapping, Any

SEEDREAM_MODELS = {
    'Doubao-Seedream-5.0-lite': 'doubao-seedream-5-0-260128',
    'Doubao-Seedream-5.0-pro': 'doubao-seedream-5-0-pro-260628',
    'Doubao-Seedream-5.0-flash': 'doubao-seedream-5-0-flash-260915',
}
ROUTES: dict[str, dict[str, Any]] = {
    'ark_seedream_seedance': dict(enabled=True, image_provider='ark', video_provider='seedance',
        image_models=SEEDREAM_MODELS, video_models=('seedance-2-fast', 'seedance-2-standard', 'seedance-2-mini')),
    'image2_vidu': dict(enabled=False, image_provider='comfy_cloud', video_provider='vidu',
        image_models={'GPT-Image-2': 'gpt-image-2'}, video_models=('vidu-q3-pro', 'vidu-q3-turbo')),
    'image2_minimax_h3': dict(enabled=False, image_provider='comfy_cloud', video_provider='minimax',
        image_models={'GPT-Image-2': 'gpt-image-2'}, video_models=('minimax-h3',)),
}


def selected(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    env = os.environ if environ is None else environ
    name = env.get('DRAMA_PLUGIN_ACTIVE_ROUTE', 'ark_seedream_seedance')
    enabled = [key for key, value in ROUTES.items() if value['enabled']]
    if len(enabled) != 1 or name not in enabled:
        raise ValueError('PRODUCTION_ROUTE_DISABLED_OR_NOT_UNIQUE')
    route = ROUTES[name]
    choice = env.get('DRAMA_PLUGIN_ROUTE_IMAGE_MODEL', 'Doubao-Seedream-5.0-lite')
    model = route['image_models'].get(choice, choice)
    if model == 'doubao-seedream-5-0-lite-260128':
        model = SEEDREAM_MODELS['Doubao-Seedream-5.0-lite']
    if model not in route['image_models'].values():
        raise ValueError('IMAGE_MODEL_OUTSIDE_ACTIVE_ROUTE')
    video = env.get('DRAMA_PLUGIN_ROUTE_VIDEO_MODEL', 'seedance-2-fast')
    if video not in route['video_models']:
        raise ValueError('VIDEO_MODEL_OUTSIDE_ACTIVE_ROUTE')
    return dict(route=name, enabled_route_count=1, image_provider=route['image_provider'],
                image_model=model, video_provider=route['video_provider'], video_model=video)


def require_video(provider: str, model: str) -> None:
    route = selected()
    if (provider, model) != (route['video_provider'], route['video_model']):
        raise ValueError('FIXED_PRODUCTION_VIDEO_ROUTE_MISMATCH')


def require_image(provider: str, model: str) -> None:
    route = selected()
    if (provider, model) != (route['image_provider'], route['image_model']):
        raise ValueError('FIXED_PRODUCTION_IMAGE_ROUTE_MISMATCH')
