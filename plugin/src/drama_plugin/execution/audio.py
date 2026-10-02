"""Consume approved AudioExecutionPlan and recipe without rewriting speech.

Approved stable clips or explicit native preservation are the E1 consumers.
Missing TTS/recordings remains capability absence. Placement uses measured clip
durations and checks the authored temporal graph; it never serializes layers.
"""
from __future__ import annotations

from array import array
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Protocol

from drama_plugin.execution.contracts import AudioTiming, FinishingRecipe, MediaIdentity
from drama_plugin.execution.media import LocalMediaStore, probe
from drama_plugin.execution.transport import CapabilityAbsent
from drama_plugin.generation.contracts import AudioExecutionPlan, TemporalRelation


class AudioConsumer(Protocol):
    def render(self, plan: AudioExecutionPlan, recipe: FinishingRecipe, video: MediaIdentity,
               store: LocalMediaStore, output: Path) -> tuple[AudioTiming, ...]: ...


class ApprovedAudioConsumer:
    """Local physical execution of an approved recipe; no speech provider calls."""

    def render(self, plan: AudioExecutionPlan, recipe: FinishingRecipe, video: MediaIdentity,
               store: LocalMediaStore, output: Path) -> tuple[AudioTiming, ...]:
        if not shutil.which("ffmpeg"):
            raise CapabilityAbsent("AUDIO_RENDER_ABSENT")
        if plan.artifact_reference() != recipe.audio_plan_ref:
            raise ValueError("Audio recipe/plan mismatch")
        selected = {p.event_id: p for p in recipe.placements}
        events = {e.event_id: e for e in plan.speech_events}
        if set(selected) - set(events):
            raise ValueError("Recipe adds unauthored speech")
        if recipe.native_policy != "PRESERVE" and set(selected) != set(events):
            raise CapabilityAbsent("TARGET_SPEECH_RECORDINGS_OR_TTS_ABSENT")
        if recipe.native_policy != "PRESERVE" and "TTS" in plan.source_roles and not selected and events:
            raise CapabilityAbsent("TARGET_TTS_ABSENT")
        beds = (*plan.ambience_refs, *plan.foley_refs, *plan.music_refs)
        if recipe.native_policy != "PRESERVE" and tuple(recipe.bed_refs) != beds:
            raise CapabilityAbsent("TARGET_AUTHORED_AUDIO_BEDS_ABSENT")
        if plan.native_audio_policy == "DISABLED" and recipe.native_policy != "REPLACE":
            raise ValueError("Recipe reintroduces disabled native audio")
        if recipe.native_policy != "REPLACE" and not probe(store.path(video)).audio_codec:
            raise CapabilityAbsent("NATIVE_AUDIO_ABSENT")
        timings: list[AudioTiming] = []
        for event_id, placement in selected.items():
            event = events[event_id]
            if placement.source_ref != event.source_ref:
                raise ValueError("Audio clip binds a different exact speech source")
            observation = probe(store.path(placement.media))
            if placement.media.kind != "AUDIO" or not observation.audio_codec or observation.video_codec:
                raise ValueError("Speech placement is not stable audio")
            end = placement.start_ms + observation.duration_ms
            if end > plan.duration_ms or (event.window_ms is not None and not
                    event.window_ms[0] <= placement.start_ms < end <= event.window_ms[1]):
                raise ValueError("Complete recorded speech does not fit approved window; E2 revision required")
            timings.append(AudioTiming(event_id=event_id, source_ref=event.source_ref,
                start_ms=placement.start_ms, end_ms=end, layer=event.layer.value,
                spoken_content_id=event.spoken_content_id))
        measured = {t.event_id: t for t in timings}
        for relation in plan.relations:
            if relation.ends_target_speech:
                # Never infer a word boundary or trim an approved recording.
                raise CapabilityAbsent("APPROVED_WORD_BOUNDARY_INTERRUPTION_CONSUMER_ABSENT")
            if relation.event_id not in measured or relation.target_event_id not in measured:
                # Preserved native speech remains unobserved, never invented timing.
                continue
            a, b = measured[relation.event_id], measured[relation.target_event_id]
            if relation.relation == TemporalRelation.BEFORE:
                valid = a.end_ms <= b.start_ms
            elif relation.relation == TemporalRelation.AFTER:
                valid = b.end_ms <= a.start_ms
            elif relation.relation == TemporalRelation.INTERRUPT:
                valid = b.start_ms < a.start_ms < b.end_ms
            else:
                valid = max(a.start_ms, b.start_ms) < min(a.end_ms, b.end_ms)
            if not valid:
                raise ValueError("Recorded speech contradicts approved temporal relation; E2 revision required")
            if relation.relation == TemporalRelation.FADE_BEHIND:
                fade = selected[a.event_id].fade_out_window_ms
                if fade is None:
                    raise CapabilityAbsent("APPROVED_FADE_RECIPE_ABSENT")
                if not (a.start_ms <= fade[0] < fade[1] <= a.end_ms and
                        max(fade[0], b.start_ms) < min(fade[1], b.end_ms)):
                    raise ValueError("Approved fade contradicts measured speech relation")
        inputs: list[str] = []
        filters: list[str] = []
        labels: list[str] = []
        if recipe.native_policy != "REPLACE":
            inputs += ["-i", str(store.path(video))]
            filters.append(f"[0:a:0]aresample=48000,volume={recipe.native_gain_db}dB[a0]")
            labels.append("[a0]")
        placements = (*recipe.placements, *recipe.bed_placements)
        for index, placement in enumerate(placements, start=len(labels)):
            if index >= len(recipe.placements) + (recipe.native_policy != "REPLACE"):
                bed_index = index - len(recipe.placements) - (recipe.native_policy != "REPLACE")
                if placement.source_ref != recipe.bed_refs[bed_index]:
                    raise ValueError("Audio bed source mismatch")
            if placement.start_ms + probe(store.path(placement.media)).duration_ms > plan.duration_ms:
                raise ValueError("Audio source would be truncated")
            inputs += ["-i", str(store.path(placement.media))]
            effect = f"[{index}:a:0]aresample=48000,volume={placement.gain_db}dB,adelay={placement.start_ms}:all=1"
            if placement.fade_out_window_ms is not None:
                start, end = placement.fade_out_window_ms
                effect += f",afade=t=out:st={start / 1000}:d={(end - start) / 1000}"
            filters.append(effect + f"[a{index}]")
            labels.append(f"[a{index}]")
        if labels:
            filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,"
                           f"apad=whole_dur={plan.duration_ms / 1000},atrim=duration={plan.duration_ms / 1000}[out]")
        else:
            # Explicit approved replacement with no speech/bed means silence.
            inputs = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            filters.append(f"[0:a]atrim=duration={plan.duration_ms / 1000}[out]")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-filter_complex_threads", "1", *inputs,
            "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2",
            "-t", str(plan.duration_ms / 1000), "-c:a", "pcm_f32le", "-f", "wav", str(output)],
            check=True, capture_output=True, timeout=60)
        # Reject clipping without silently normalizing or altering approved gain.
        decoded = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(output),
            "-f", "f32le", "-"], check=True, capture_output=True, timeout=30).stdout
        samples = array("f")
        samples.frombytes(decoded)
        if any(abs(value) > 1.0 for value in samples):
            raise ValueError("Approved audio gain clips; E2 mix revision required")
        return tuple(timings)


def render_audio(consumer: AudioConsumer, plan: AudioExecutionPlan, recipe: FinishingRecipe,
                 video: MediaIdentity, store: LocalMediaStore) -> tuple[MediaIdentity, tuple[AudioTiming, ...]]:
    with tempfile.TemporaryDirectory(prefix="target-audio-") as directory:
        output = Path(directory) / "mix.wav"
        timings = consumer.render(plan, recipe, video, store, output)
        media = store.retain(output.read_bytes(), kind="AUDIO", mime="audio/wav")
    return media, timings


def finish_av(video: MediaIdentity, audio: MediaIdentity, store: LocalMediaStore) -> MediaIdentity:
    if not shutil.which("ffmpeg"):
        raise CapabilityAbsent("AV_MUX_ABSENT")
    # One existing pure primitive; no old host, retention or Work workflow.
    from drama_plugin.audio.host_media import mux_video_and_audio
    with tempfile.TemporaryDirectory(prefix="target-av-") as directory:
        output = Path(directory) / "candidate.mp4"
        mux_video_and_audio(store.path(video), store.path(audio), output)
        return store.retain(output.read_bytes(), kind="VIDEO", mime="video/mp4")
