"""Local picture assembly from the existing reviewed plan; no generation or business writes."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
from drama_plugin.production_design import picture_edit_handoff


def _run(args: list[str]) -> bytes:
    return subprocess.run(args, check=True, capture_output=True).stdout


def _probe(path: Path) -> dict[str, Any]:
    return json.loads(_run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))  # type: ignore[no-any-return]


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def render_picture_edit(plan: PictureEditPlan, paths: dict[str, Path], directory: Path,
                        *, current_canon_fingerprint: str, fps: int = 24) -> dict[str, Any]:
    """Hard cuts with native synchronized audio; J/L audio edits remain in sound finishing.

    Explicitly re-encodes a new candidate. Rejects unsupported stream layouts/geometry
    instead of silently dropping tracks, cropping, stretching or inventing silence.
    Call only for an authorized local assembly after actual source performance review.
    """
    plan = PictureEditPlan.model_validate(dump_contract(plan))
    if fps not in {24, 25, 30}:
        raise ValueError('Choose an explicit supported output frame rate')
    if set(paths) != {s.media_id for s in plan.sources}:
        raise ValueError('Exact source path mapping required')
    hashes = {key: _hash(path) for key, path in paths.items()}
    handoff = picture_edit_handoff(plan, current_sources=hashes, canon_fingerprint=current_canon_fingerprint)
    if not handoff['assemblyReady']:
        raise ValueError('Picture assembly requires reviewed source audio/dialogue and plan')
    info = {key: _probe(path) for key, path in paths.items()}
    dimensions = set()
    for source in plan.sources:
        probe = info[source.media_id]
        videos = [s for s in probe['streams'] if s['codec_type'] == 'video']
        audios = [s for s in probe['streams'] if s['codec_type'] == 'audio']
        if len(videos) != 1 or len(audios) != 1 or len(probe['streams']) != 2:
            raise ValueError('This renderer requires one video and one audio stream; no silent track dropping')
        v = videos[0]
        if v.get('sample_aspect_ratio', '1:1') not in {'1:1', 'N/A'} or v.get('side_data_list'):
            raise ValueError('Rotated or non-square-pixel source requires explicit normalization')
        dimensions.add((v['width'], v['height']))
        measured = min(float(v.get('duration', probe['format']['duration'])),
                       float(audios[0].get('duration', probe['format']['duration'])))
        if abs(float(probe['format']['duration']) - source.duration) > .1:
            raise ValueError('Plan duration differs from measured source')
        if any(e.source_out > measured + .001 for e in plan.picture_edit if e.source_media == source.media_id):
            raise ValueError('Trim exceeds source picture/audio duration')
    if len(dimensions) != 1:
        raise ValueError('Mixed source geometry requires a separately reviewed normalization plan')
    recipe = {'plan': dump_contract(plan), 'fps': fps, 'renderer': 'picture-edit-hardcuts-v1',
              'audioPolicy': 'SYNCHRONIZED_NATIVE_TRIMS', 'outputCodec': 'h264/aac',
              'ffmpeg': _run(['ffmpeg', '-version']).decode().splitlines()[0]}
    fingerprint = sha256_canonical(recipe)
    directory = directory.resolve()
    output = directory / ('picture-' + fingerprint + '.mp4')
    journal = directory / ('picture-' + fingerprint + '.json')
    if output in {p.resolve() for p in paths.values()}:
        raise ValueError('Output cannot replace source')
    if journal.exists():
        record = json.loads(journal.read_text())
        if record.get('recipeFingerprint') != fingerprint or not output.exists() or _hash(output) != record['outputHash']:
            raise ValueError('Retained result changed; recover bytes before rendering again')
        return record  # type: ignore[no-any-return]
    if output.exists():
        raise ValueError('Unjournaled output exists; recover instead of overwriting')
    directory.mkdir(parents=True, exist_ok=True)
    ids = list(paths)
    args = ['ffmpeg', '-v', 'error', '-nostdin', '-n']
    for key in ids:
        args.extend(['-i', str(paths[key].resolve())])
    filters = []
    count = len(plan.picture_edit)
    for i, e in enumerate(plan.picture_edit):
        j = ids.index(e.source_media)
        filters.append(f'[{j}:v:0]trim=start={e.source_in}:end={e.source_out},setpts=PTS-STARTPTS,fps={fps},setsar=1[v{i}]')
        filters.append(f'[{j}:a:0]atrim=start={e.source_in}:end={e.source_out},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[a{i}]')
    filters.append(''.join(f'[v{i}][a{i}]' for i in range(count)) + f'concat=n={count}:v=1:a=1[v][a]')
    args.extend(['-filter_complex', ';'.join(filters), '-map', '[v]', '-map', '[a]', '-c:v', 'libx264',
                 '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(output)])
    _run(args)
    _run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'])
    expected = sum(e.source_out - e.source_in for e in plan.picture_edit)
    actual = float(_probe(output)['format']['duration'])
    if abs(actual - expected) > count / fps + .05:
        raise ValueError('Rendered timeline differs from planned trims')
    if any(_hash(paths[key]) != value for key, value in hashes.items()):
        raise ValueError('Source changed during assembly')
    record = {'recipeFingerprint': fingerprint, 'recipe': recipe, 'output': str(output),
              'outputHash': _hash(output), 'duration': actual, 'expectedDuration': expected,
              'sourceHashes': hashes, 'sourceMutation': False, 'reencoded': True,
              'status': 'LOCAL_CANDIDATE_REVIEW_AND_PERSISTENCE_PENDING',
              'audioReview': 'UNKNOWN', 'fullPlaybackReview': 'UNKNOWN', 'userAdoption': 'UNCHANGED'}
    journal.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    return record
