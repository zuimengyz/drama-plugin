"""MIGRATION_ONLY: sole legacy department-to-Target production domain mapping.

This is a read selection catalog, not the full authoring registry or a mandatory DAG.
Unbound capabilities are never executed. Canon authors, QA and future compilers retain
their own interfaces; T4 does not turn their presence into production dependencies.
"""
from types import MappingProxyType

from drama_plugin.production.contracts import SourceDomain as D

DEPARTMENT_DOMAINS = MappingProxyType({
    "director": D.DIRECTION, "shot-design": D.DIRECTION, "editorial-design": D.EDITORIAL,
    "cinematography": D.CAMERA, "lighting-design": D.LIGHTING, "color-design": D.COLOR,
    "color-grading": D.COLOR, "dramatic-performance-direction": D.PERFORMANCE,
    "blocking": D.PERFORMANCE, "action-choreography": D.ACTION,
    "character-art": D.SUBJECTS, "costume-design": D.SUBJECTS, "look-continuity": D.SUBJECTS,
    "environment-design": D.WORLD, "environment-art": D.WORLD, "scene-layout": D.WORLD,
    "set-decoration": D.WORLD, "prop-design": D.WORLD, "animal-design": D.SUBJECTS,
    "battle-crowd-choreography": D.ACTION, "vfx-planning": D.WORLD,
    "sound-design": D.SOUND, "music-direction": D.SOUND, "dialogue-design": D.SOUND,
    "voice-direction": D.SOUND, "reference-strategy": D.REFERENCE, "clip-decomposition": D.EDITORIAL,
})

# Preserve T2's existing minimum sources, rather than inventing new professional obligations.
CORE_SOURCES = ("director", "shot-design", "cinematography")
RECORD_REQUIRED = frozenset({*CORE_SOURCES, "dramatic-performance-direction", "blocking"})
