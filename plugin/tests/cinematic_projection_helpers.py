"""Real Requirements for retained, offline cinematic projection diagnostics.

No media or language approval is invented. Contract defaults supply the empty
production-dialogue authorization tuple; live submission remains separately gated.
"""
from typing import Literal

from drama_plugin.visual.cinematic import verify_frozen
from drama_plugin.visual.video_selection import Requirements


def projection_requirements(frozen, *, sound: str,
                            mode: Literal['SINGLE_IMAGE', 'TEXT_TO_VIDEO'] = 'SINGLE_IMAGE',
                            authority_context=None) -> Requirements:
    spec = verify_frozen(frozen)
    return Requirements(
        work_id=spec.work_id, scene_id=spec.scene_id, shot_id=spec.shot_id,
        target_id=spec.shot_id, shot_type='OFFLINE_PROJECTION_DIAGNOSTIC',
        source_fingerprint=spec.source_fingerprint, mode=mode,
        controls=('TEXT',) if mode == 'TEXT_TO_VIDEO' else ('FIRST_FRAME',),
        duration_seconds=spec.duration_seconds, aspect_ratio='16:9', sound=sound,
        frozen_creative={'cinematic_direction': frozen}, authority_context=authority_context,
        inputs=(), reference_duties=(),
        required=('Preserve frozen creative obligations',), forbidden=('No invented creative facts',),
    )
