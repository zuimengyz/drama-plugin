"""Local storyboard attachments -> existing DRAFT PictureEditPlan; no production route.

Host authors boards and timing. This adapter never infers coverage, selects assets,
creates generation tasks or changes Canon/adoption. Explicit silence is a temporary
track, not a performance or a completed Sound Bible.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import json

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
from drama_plugin.contracts.sequence import SequencePackage
from drama_plugin.hosts.picture_edit import _hash, _probe, _run, render_picture_edit
from drama_plugin.sequence import sequence_handoff


def storyboard_attachment_plan(package: SequencePackage,
                               boards: dict[str, list[dict[str, Any]]], *,
                               current_fingerprints: dict[str, str]) -> dict[str, Any]:
    """Source-bound local recipe, NOT a model request or automatic first frame."""
    package = SequencePackage.model_validate(dump_contract(package))
    handoff = sequence_handoff(package, current_fingerprints)
    if set(boards) != {s.key for s in package.shots}:
        raise ValueError('Provide exactly the selected storyboard shot attachments')
    rows = []
    for shot, timing in zip(package.shots, package.editorial.coverage):
        panels: list[dict[str, Any]] = []
        for panel in boards[shot.key]:
            path = Path(panel['path']).resolve(strict=True)
            duration = float(panel['duration'])
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Panel duration must be finite and positive')
            if path.suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
                raise ValueError('Use local still storyboard attachments')
            panels.append({'path': str(path), 'hash': _hash(path), 'duration': duration})
        if not panels or abs(sum(p['duration'] for p in panels) - timing.duration) > 1e-6:
            raise ValueError('Panel timing must realize the selected editorial estimate')
        rows.append({'shot': shot.key, 'scene': shot.scene_id,
                     'sourceShot': shot.source_shot_id, 'panels': panels,
                     'duration': timing.duration, 'durationReason': timing.duration_reason})
    value = {'sequenceFingerprint': handoff['fingerprint'], 'shots': rows,
             'purpose': 'DIRECTOR_ANIMATIC_DRAFT', 'audio': 'SILENT_PLACEHOLDER',
             'productionAuthorized': False, 'automaticFirstFrame': False,
             'generationRequests': [], 'adoption': 'UNCHANGED'}
    return {**value, 'fingerprint': sha256_canonical(value)}


def _source(row: dict[str, Any], directory: Path, fps: int) -> Path:
    recipe = {'row': row, 'fps': fps, 'renderer': 'storyboard-stills-v1',
              'audio': 'SILENT_PLACEHOLDER',
              'ffmpeg': _run(['ffmpeg', '-version']).decode().splitlines()[0]}
    stem = sha256_canonical(recipe)
    output, journal = directory / (stem + '.mp4'), directory / (stem + '.json')
    if journal.exists():
        record = json.loads(journal.read_text())
        if not output.exists() or _hash(output) != record['outputHash']:
            raise ValueError('Changed retained animatic source')
        return output
    if output.exists():
        raise ValueError('Unjournaled animatic source; inspect before resuming')
    # ffconcat quotes are not shell quotes; reject line breaks and escape apostrophes.
    lines = ['ffconcat version 1.0']
    for panel in row['panels']:
        path = panel['path']
        if '\n' in path or '\r' in path:
            raise ValueError('Unsupported newline in storyboard path')
        lines += ["file '" + path.replace("'", "'\\''") + "'", f"duration {panel['duration']}"]
    lines.append(lines[-2])  # give the last still its declared duration
    listing = directory / (stem + '.ffconcat')
    listing.write_text('\n'.join(lines) + '\n')
    _run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-safe', '0', '-i', str(listing),
          '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', str(row['duration']),
          '-map', '0:v:0', '-map', '1:a:0', '-vf', f'fps={fps},setsar=1',
          '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
          '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(output)])
    if any(_hash(Path(p['path'])) != p['hash'] for p in row['panels']):
        raise ValueError('Storyboard attachment changed during rendering')
    journal.write_text(json.dumps({'recipe': recipe, 'outputHash': _hash(output)}, indent=2))
    return output


def render_storyboard_animatic(package: SequencePackage,
                              boards: dict[str, list[dict[str, Any]]], directory: Path, *,
                              current_fingerprints: dict[str, str], fps: int = 24) -> dict[str, Any]:
    """Render one selected sequence through the native picture renderer, DRAFT only.

    For a film, call per scene then assemble those actual outputs with PictureEditPlan.
    Missing audio is explicitly silent in the review record. Label the delivery as
    picture-only; do not require subtitles burned into cinematic storyboard art.
    Film timing is a rehearsal estimate, unrelated to generation limits.
    """
    if fps not in {24, 25, 30}:
        raise ValueError('Unsupported preview fps')
    recipe = storyboard_attachment_plan(package, boards, current_fingerprints=current_fingerprints)
    directory = directory.resolve() / recipe['fingerprint']
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'attachment-recipe.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2))
    paths, sources, edits = {}, [], []
    for row in recipe['shots']:
        output = _source(row, directory, fps)
        paths[row['shot']] = output
        measured = float(_probe(output)['format']['duration'])
        sources.append({'mediaId': row['shot'], 'contentHash': _hash(output), 'duration': measured,
                        'performanceReview': 'STILL_STORYBOARD_ONLY; no motion or audible performance evidence'})
        edits.append({'sourceMedia': row['shot'], 'sourceIn': 0, 'sourceOut': row['duration'],
                      'cutReason': row['durationReason'], 'audioCarry': 'SILENT_PLACEHOLDER; see Sound cue originals',
                      'paceFunction': 'Host-selected rehearsal estimate, not a model generation window'})
    plan = PictureEditPlan.model_validate({'revision': package.revision,
        'sourceCanonFingerprint': package.editorial.source_fingerprint,
        'sources': sources, 'pictureEdit': edits, 'status': 'DRAFT', 'audioReview': 'UNKNOWN',
        'protectedDialogueReview': 'Text timing only; voice and music NOT recorded or heard'})
    (directory / 'PictureEditPlan.json').write_text(json.dumps(dump_contract(plan), ensure_ascii=False, indent=2))
    (directory / 'sources.json').write_text(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
    record = render_picture_edit(plan, paths, directory / 'assembly',
                                current_canon_fingerprint=package.editorial.source_fingerprint,
                                fps=fps, preview_only=True)
    return {'attachmentRecipe': recipe, 'pictureEditPlan': dump_contract(plan),
            'sources': {k: str(v) for k, v in paths.items()}, 'render': record,
            'productionAuthorized': False, 'sourceMutation': False}
