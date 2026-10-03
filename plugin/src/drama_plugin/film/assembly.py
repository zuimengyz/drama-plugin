"""Physical consumers of approved edit order and measured speech timing."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.creative_engine.sources import NativeCreativeSources
from drama_plugin.creative_engine.contracts import Kind, SceneBody
from drama_plugin.execution.contracts import AudioExecution, ReviewedAVCandidate
from drama_plugin.execution.media import LocalMediaStore, atomic_write, probe
from drama_plugin.execution.store import ExecutionStore
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.film.contracts import FilmShotBinding, SubtitleCue, DeliveryProfile, FilmCanon
from drama_plugin.runtime.contracts import ArtifactReference


def _stamp(ms: int) -> str:
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def validate_cues(cues: tuple[SubtitleCue, ...], shots: tuple[FilmShotBinding, ...], execution: ExecutionStore, versions: CreativeVersionStore, canon: FilmCanon, canon_ref: ArtifactReference) -> str:
    offsets: dict[str, int] = {}
    elapsed = 0
    for ordered_shot in shots:
        offsets[ordered_shot.shot_id] = elapsed
        elapsed += ordered_shot.duration_ms
    rendered: list[str] = []
    for number, cue in enumerate(cues, 1):
        shot = next((s for s in shots if s.shot_id == cue.shot_id), None)
        if shot is None:
            raise ValueError('Cross-scope subtitle')
        candidate = execution.get(shot.candidate_ref, ReviewedAVCandidate)
        if candidate.audio_execution_ref != cue.timing_ref:
            raise ValueError('Subtitle timing is not approved speech execution')
        audio = execution.get(cue.timing_ref, AudioExecution)
        if not any(t.start_ms == cue.start_ms and t.end_ms == cue.end_ms and
                   ArtifactReference(owner=t.source_ref.owner.value, artifact_ref=t.source_ref.artifact_ref,
                                     version=t.source_ref.version) == cue.text_ref for t in audio.timings):
            raise CapabilityAbsent('RELIABLE_SUBTITLE_TIMING_ABSENT')
        # Text is resolved from the precise approved AudioPlan, never from an estimate.
        body, _, _ = execution.ledger.get_artifact('audio-plan', audio.audio_plan_ref)
        from drama_plugin.generation.contracts import AudioExecutionPlan
        plan = AudioExecutionPlan.model_validate(body)
        event = next((e for e in plan.speech_events if e.source_ref.artifact_ref == cue.text_ref.artifact_ref
            and e.source_ref.version == cue.text_ref.version), None)
        if event is None:
            raise ValueError('Subtitle text differs from Canon')
        scene = next(versions.resolve(r) for r in versions.selected_refs(shot.shot_ref) if versions.resolve(r).kind == Kind.SCENE)
        assert isinstance(scene.body, SceneBody)
        ids = {t.spoken_content_id for t in audio.timings if t.start_ms == cue.start_ms and t.end_ms == cue.end_ms}
        line = next((line for line in scene.body.dialogue if line.id in ids),None)
        if line is None:
            raise ValueError('Subtitle exact Canon source absent')
        from drama_plugin.contracts.base import sha256_canonical
        if cue.localization_ref:
            original = next((s for s in canon.scenes if s.scene_id==shot.scene_id),None)
            if cue.localization_ref != canon_ref or original is None or not any(
                q.dialogue_id==line.id and q.source_text_hash==sha256_canonical(line.text) and q.language==cue.language and q.text==cue.text for q in original.subtitle_localizations):
                raise ValueError('Subtitle localization is not approved for this precise Canon text')
        elif line.text != cue.text or cue.language != event.language:
            raise ValueError('Subtitle exact Canon text mismatch')
        if cue.end_ms > shot.duration_ms:
            raise ValueError('Subtitle outside measured AV')
        offset = offsets[cue.shot_id]
        rendered.append(f'{number}\n{_stamp(offset+cue.start_ms)} --> {_stamp(offset+cue.end_ms)}\n{cue.text}\n')
    return '\n'.join(rendered)


def assemble(shots: tuple[FilmShotBinding, ...], store: LocalMediaStore, subtitle_text: str | None) -> tuple[bytes, ArtifactReference | None]:
    with tempfile.TemporaryDirectory(prefix='target-film-') as temp:
        root = Path(temp)
        paths = [store.path(shot.media) for shot in shots]
        # Paths are not interpolated into a shell. The concat demuxer has its own quoting.
        (root/'edit.txt').write_text('\n'.join("file '"+str(path).replace("'", "'\\''")+"'" for path in paths))
        joined = root/'joined.mp4'
        subprocess.run(['ffmpeg','-nostdin','-v','error','-f','concat','-safe','0','-i',str(root/'edit.txt'),
                        '-map','0:v:0','-map','0:a:0?','-c','copy','-fflags','+bitexact','-y',str(joined)],
                       check=True, capture_output=True, timeout=120)
        subtitle_ref = None
        if subtitle_text is not None:
            raw = subtitle_text.encode('utf-8')
            digest = hashlib.sha256(raw).hexdigest()
            subtitle_ref = ArtifactReference(owner='film-subtitle', artifact_ref='subtitle:sha256:'+digest, version=1)
            # The text derivative stays outside the execution Ledger.
            atomic_write(store.directory / (digest+'.srt'), raw)
            srt = root/'captions.srt'
            srt.write_bytes(raw)
            output = root/'subtitled.mp4'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(joined),'-i',str(srt),'-map','0','-map','1',
                            '-c','copy','-c:s','mov_text','-metadata:s:s:0','language=und','-y',str(output)],
                           check=True, capture_output=True, timeout=120)
            joined = output
        return joined.read_bytes(), subtitle_ref


def final_qa(path: Path, profile: DeliveryProfile, duration_ms: int, content_hash: str) -> tuple[tuple[str,...], tuple[str,...]]:
    checks: list[str] = []
    failures: list[str] = []
    observation = probe(path, decode=True)
    checks.extend(('container_readable','video_decode','audio_decode','duration','resolution_profile','hash_consistency'))
    if not observation.video_codec or (observation.width, observation.height) != (profile.width,profile.height):
        failures.append('VIDEO_PROFILE_MISMATCH')
    if profile.audio_required and not observation.audio_codec:
        failures.append('REQUIRED_AUDIO_ABSENT')
    if abs(observation.duration_ms-duration_ms) > profile.duration_tolerance_ms:
        failures.append('DURATION_MISMATCH')
    if hashlib.sha256(path.read_bytes()).hexdigest() != content_hash:
        failures.append('HASH_MISMATCH')
    raw = subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],check=True,capture_output=True,timeout=30)
    streams = json.loads(raw.stdout)['streams']
    av = [s for s in streams if s['codec_type'] in ('video','audio')]
    if len(av) == 2:
        starts = [float(s.get('start_time',0))*1000 for s in av]
        ends = [(float(s.get('start_time',0))+float(s.get('duration',observation.duration_ms/1000)))*1000 for s in av]
        if max(starts)-min(starts) > profile.duration_tolerance_ms or max(ends)-min(ends) > profile.duration_tolerance_ms:
            failures.append('AV_SYNC_MISMATCH')
        checks.append('av_sync')
    if profile.subtitle_required:
        checks.append('subtitle_presence')
        if not any(s['codec_type']=='subtitle' for s in streams):
            failures.append('REQUIRED_SUBTITLE_ABSENT')
    return tuple(checks),tuple(failures)
