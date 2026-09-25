"""One implemented translator per model family; no creative ownership."""
from .registry import get_generator, registry

__all__ = ['get_generator', 'registry']
