"""Readiness is explicit. Reserved directories never imply a working generator."""
from typing import Any
from drama_plugin.prompt_generators.base import ModelPromptGenerator

RESERVED = ('gpt_image_2', 'vidu', 'flux', 'minimax', 'wan', 'kling', 'seedance_2_5')


def is_seedance2(model: str) -> bool:
    from drama_plugin.providers.video.registry import registry
    spec = registry()['models'].get(model, {})
    return bool(spec.get('provider') == 'seedance' and spec.get('vendor_model', '').startswith('doubao-seedance-2-0-'))


def get_generator(family: str) -> ModelPromptGenerator:
    if family != 'seedance_2':
        raise ValueError('MODEL_PROMPT_GENERATOR_NOT_IMPLEMENTED:' + family)
    from drama_plugin.prompt_generators.seedance_2.generator import Seedance2PromptGenerator
    return Seedance2PromptGenerator()


def registry() -> dict[str, Any]:
    generator = get_generator('seedance_2')
    return {'seedance_2': dict(implemented=True, supported_modes=generator.supported_modes,
                              generator_version=generator.version, policy_status='LOCAL_EXPERIMENTAL'),
            **{name: dict(implemented=False, supported_modes=(), generator_version=None,
                          policy_status='RESERVED', runtime_dispatch=False) for name in RESERVED}}
