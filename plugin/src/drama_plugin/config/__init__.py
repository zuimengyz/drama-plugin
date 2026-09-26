"""Lazy public exports keep language contracts independent of video adapters."""
from importlib import import_module
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from drama_plugin.config.video_route import VideoRoutePolicy, RouteMode, PolicySource
    from drama_plugin.config.loader import load_config
    from drama_plugin.config.models import (
        ContextProviderConfig, DomainProviderConfig, DramaPluginConfig,
        ProvidersConfig, ServiceConfig, ServicesConfig,
    )


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    module = ('loader' if name == 'load_config' else 'video_route'
              if name in {'VideoRoutePolicy', 'RouteMode', 'PolicySource'} else 'models')
    return getattr(import_module('drama_plugin.config.' + module), name)

__all__ = [
    "ContextProviderConfig",
    "DomainProviderConfig",
    "DramaPluginConfig",
    "ProvidersConfig",
    "ServiceConfig",
    "ServicesConfig",
    "load_config",
    "VideoRoutePolicy", "RouteMode", "PolicySource",
]
