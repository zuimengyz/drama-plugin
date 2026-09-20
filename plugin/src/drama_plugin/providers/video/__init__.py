"""Official HTTP adapters alongside the existing Comfy MCP Host."""
from .base import VideoProvider
from .adapters import SeedanceProvider, MiniMaxProvider, ViduProvider, WanProvider, KlingProvider

__all__ = ['VideoProvider','SeedanceProvider','MiniMaxProvider','ViduProvider','WanProvider','KlingProvider']
