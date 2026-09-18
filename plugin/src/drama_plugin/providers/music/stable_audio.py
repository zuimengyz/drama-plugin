"""Stable Audio 3 family. Local artifact-only execution; cloud is a closed boundary.

No business schema, endpoint, Tool, creative decisions, implicit retries or adoption.
The host supplies reviewed source-bound inputs and an explicit engineering-PoC state.
"""
from __future__ import annotations

import array
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.film_score import FilmScorePlan, MusicGenerationRequirements
from drama_plugin.music_direction import composer_brief, qualify_music_requirements

FAMILY = 'stable_audio_3'
STATUSES = {'PASS', 'FAIL', 'UNKNOWN', 'NOT_SUPPORTED', 'NOT_APPLICABLE_WITH_REASON'}
PREFIX = 'DRAMA_PLUGIN_STABLE_AUDIO_LOCAL_'
REQUIRED_FIELDS = ('dramaticFunction', 'cueArc', 'timbrePalette', 'rhythmicFunction',
                   'dialogueWindows', 'entryTrigger', 'exitTrigger', 'doNot')
VERSE = re.compile(r'HISTORICAL_VERSE_PERFORMANCE|DECLAMED_VERSE')


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


@dataclass(frozen=True)
class LocalConfig:
    root: Path
    python: Path
    model: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LocalConfig:
        e = os.environ if env is None else env
        if not all(e.get(PREFIX + k) for k in ('ROOT', 'PYTHON', 'MODEL')):
            raise ValueError('EXPLICIT_LOCAL_CONFIGURATION_REQUIRED')
        return cls(Path(e[PREFIX + 'ROOT']).expanduser().absolute(),
                   Path(e[PREFIX + 'PYTHON']).expanduser().absolute(), e[PREFIX + 'MODEL'])


def inspect_installation(config: LocalConfig) -> dict[str, Any]:
    if config.model not in {'medium', 'sm-music'}:
        raise ValueError('UNSUPPORTED_MODEL')
    root = config.root
    if not (root / 'scripts/sa3_mlx.py').is_file() or not config.python.is_file():
        raise ValueError('LOCAL_INSTALLATION_MISSING')
    codec = 'l' if config.model == 'medium' else 's'
    files = ['t5gemma_f16.npz', f'dit_{config.model}_f16.npz', f'same_{codec}_decoder_f32.npz']
    missing = [n for n in files if not (root / 'models/mlx' / n).is_file() or (root / 'models/mlx' / n).stat().st_size == 0]
    if missing:
        raise ValueError('LOCAL_MODEL_INCOMPLETE: ' + ', '.join(missing))
    encoder = root / 'models/mlx' / f'same_{codec}_encoder_f32.npz'
    paths = [root / 'models/mlx' / n for n in files]
    if encoder.is_file():
        paths.append(encoder)
    weights = [{'file':str(p), 'resolved':str(p.resolve()), 'size':p.stat().st_size, 'sha256':digest(p)} for p in paths]
    # Bind every implementation file, not only a potentially clean git revision.
    code = {str(p.relative_to(root)):digest(p) for folder in ('scripts', 'models/defs')
            for p in sorted((root / folder).rglob('*.py'))}
    git = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    identity = {'providerFamily':FAMILY, 'route':'LOCAL', 'model':config.model,
                'implementation':'MLX', 'weights':weights, 'code':code,
                'repoCommit':git.stdout.strip() if git.returncode == 0 else None}
    return {**identity, 'binding':sha256_canonical(identity), 'localRoot':str(root),
            'python':str(config.python), 'platform':platform.platform(), 'architecture':platform.machine(),
            'weightsPresent':True, 'modelLoaded':False, 'encoderPresent':encoder.is_file(),
            'sampleRateCodeEvidence':44100, 'deviceBackend':'Metal',
            'weightsSourceEvidence':'Local symlinks and SHA-256; scripts/weights.py manifest; no remote verification',
            'cloudQualification':'NOT_STARTED', 'externalProviderCalls':0}


def validate_inputs(plan: FilmScorePlan, requirements: MusicGenerationRequirements,
                    brief: Mapping[str, Any], current: Mapping[str, str], reviewed_brief: str) -> None:
    plan = FilmScorePlan.model_validate(dump_contract(plan))
    requirements = MusicGenerationRequirements.model_validate(dump_contract(requirements))
    if plan.review_status != 'DESIGN_REVIEWED' or reviewed_brief != sha256_canonical(brief):
        raise ValueError('UNREVIEWED_COMPOSER_BRIEF')
    if requirements.cue_ref in plan.excluded_performance_refs or VERSE.search(json.dumps(brief, ensure_ascii=False)):
        raise ValueError('HISTORICAL_VERSE_NOT_APPLICABLE_TO_MUSIC_PROVIDER')
    cue = next((c for c in plan.music_cues if c.cue_id == requirements.cue_ref), None)
    if cue is None:
        raise ValueError('NO_SCORE_OR_UNKNOWN_CUE')
    if cue.source_strategy != 'ORIGINAL_AI':
        raise ValueError('NON_ORIGINAL_AI_REJECTED')
    pins = (*plan.source_pins, plan.film_intent_ref, *cue.binding_refs,
            *requirements.reference_refs, *(d.performance_intent_ref for d in plan.scene_music_decisions if d.scene_id in cue.scene_ids))
    if any(current.get(p.key) != p.fingerprint for p in pins):
        raise ValueError('STALE_SOURCE')
    if dump_contract(requirements) != brief.get('generationRequirements') or dict(brief) != composer_brief(plan, cue.cue_id, current=current):
        raise ValueError('COMPOSER_BRIEF_REQUIREMENTS_MISMATCH')
    if requirements.instrumental_policy != 'INSTRUMENTAL' or requirements.vocal_policy != 'PROHIBITED':
        raise ValueError('P1_INSTRUMENTAL_ONLY')


def map_brief(brief: Mapping[str, Any], translation: Mapping[str, Any]) -> dict[str, Any]:
    """A pinned field-by-field language translation is a host artifact, not new intent.

    The model tokenizer is checked at execution; never silently truncate a long brief.
    """
    if translation.get('composerBriefFingerprint') != sha256_canonical(brief):
        raise ValueError('STALE_PROMPT_TRANSLATION')
    protected = translation.get('protectedPerformanceTexts')
    if not isinstance(protected, list) or any(not isinstance(x, str) or not x.strip() for x in protected):
        raise ValueError('EXPLICIT_PROTECTED_PERFORMANCE_TEXT_POLICY_REQUIRED')
    fields = translation.get('fields', {})
    if set(fields) != set(REQUIRED_FIELDS) or not all(isinstance(v, str) and v.strip() for v in fields.values()):
        raise ValueError('COMPLETE_FIELD_TRANSLATION_REQUIRED')
    prompt = 'Instrumental film score. ' + ' '.join(fields[k] for k in REQUIRED_FIELDS if k != 'doNot')
    negative = 'singing, chant, choir, vocal texture, spoken words. ' + fields['doNot']
    if VERSE.search(prompt + negative) or any(x in prompt + negative for x in protected):
        raise ValueError('HISTORICAL_VERSE_NOT_APPLICABLE_TO_MUSIC_PROVIDER')
    return {'renderedPrompt':prompt, 'negativeInstructions':negative,
            'translationFingerprint':sha256_canonical(translation), 'fieldMapping':dict(fields),
            'protectedPerformanceTextsFingerprint':sha256_canonical(protected)}


def inspect_wav(path: Path, requested: float) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('OUTPUT_MISSING')
    with wave.open(str(path), 'rb') as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if w.getcomptype() != 'NONE' or width != 2 or not frames or rate <= 0:
            raise ValueError('LOSSLESS_PCM16_REQUIRED')
        raw = w.readframes(frames)
        if len(raw) != frames * channels * width:
            raise ValueError('TRUNCATED_WAV')
    samples = array.array('h', raw)
    import sys
    if sys.byteorder != 'little':
        samples.byteswap()
    duration = frames / rate
    peak = max(abs(x) for x in samples) / 32768
    return {'file':str(path), 'sha256':digest(path), 'mime':'audio/wav', 'container':'RIFF/WAVE',
            'codec':'pcm_s16le', 'subtype':'PCM_16', 'bitDepth':16, 'sampleRate':rate,
            'channels':channels, 'frames':frames, 'requestedDuration':requested, 'duration':duration,
            'delta':duration-requested, 'durationPass':abs(duration-requested) <= .1,
            'decodeSuccess':True, 'lossless':True, 'peak':peak,
            'clippedSampleFraction':sum(abs(x) >= 32767 for x in samples)/len(samples),
            'nearSilentSampleFraction':sum(abs(x) < 33 for x in samples)/len(samples),
            'nonSilent':peak > .001, 'instrumentalObservation':'REQUIRES_HUMAN_LISTENING',
            'forcedVocalRisk':'HUMAN_LISTEN_FOR_VOCALS'}


def qualify(plan: FilmScorePlan, requirements: MusicGenerationRequirements,
            installation: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    if evidence.get('binding') != installation['binding'] or evidence.get('route') != 'LOCAL':
        raise ValueError('QUALIFICATION_MODEL_VERSION_ROUTE_MISMATCH')
    statuses = evidence.get('statuses', {})
    if any(v not in STATUSES for v in statuses.values()):
        raise ValueError('INVALID_CAPABILITY_STATUS')
    cue = next(c for c in plan.music_cues if c.cue_id == requirements.cue_ref)
    outcome = qualify_music_requirements(cue, statuses)
    # A separately generated instrument track never satisfies B synchronized stems.
    if requirements.stem_requirement == 'REQUIRED' and evidence.get('stemsKind') != 'B_SYNCHRONIZED_COMPONENTS':
        outcome['missingOrFailed'] = sorted(set(outcome['missingOrFailed']) | {'stems'})
    blockers = outcome['missingOrFailed']
    if statuses.get('performance_observability') != 'PASS':
        blockers = sorted(set(blockers) | {'performance_observability'})
    return {'providerFamily':FAMILY, 'route':'LOCAL', 'model':installation['model'],
            'binding':installation['binding'], 'requirementsFingerprint':sha256_canonical(requirements),
            'statuses':dict(statuses), 'productionQualification':'BLOCKED' if blockers else 'PASS',
            'blockers':blockers, 'cloudQualification':'NOT_STARTED', 'productionAuthorized':False}


@dataclass(frozen=True)
class StableAudio3CloudRoute:
    """No URL, API payload, key access, HTTP client or inherited local qualification."""
    configured: bool = False
    qualified: bool = False
    rights_reviewed: bool = False
    cost_known: bool = False
    generation_authorized: bool = False

    def inspect_capabilities(self) -> dict[str, Any]:
        return {'providerFamily':FAMILY, 'route':'CLOUD', 'qualification':'NOT_STARTED',
                'generationAuthorized':False, 'adapterImplemented':False,
                'requiredGates':['CONFIGURED','QUALIFIED','RIGHTS_REVIEWED','COST_KNOWN','GENERATION_AUTHORIZED']}

    def generate(self, requirements: MusicGenerationRequirements) -> None:
        raise ValueError('CLOUD_ROUTE_DISABLED_NO_FALLBACK')


class StableAudio3Provider:
    def __init__(self, config: LocalConfig, artifact_root: Path):
        self.config = config
        self.directory = artifact_root.resolve()
        self.directory.mkdir(parents=True, exist_ok=True)

    def inspect_capabilities(self) -> dict[str, Any]:
        return inspect_installation(self.config)

    def qualify(self, plan: FilmScorePlan, requirements: MusicGenerationRequirements,
                evidence: Mapping[str, Any]) -> dict[str, Any]:
        return qualify(plan, requirements, self.inspect_capabilities(), evidence)

    def generate(self, plan: FilmScorePlan, requirements: MusicGenerationRequirements,
                 brief: Mapping[str, Any], *, current: Mapping[str, str], reviewed_brief: str,
                 translation: Mapping[str, Any], qualification: Mapping[str, Any],
                 poc_evidence: Mapping[str, Any], state: str, candidate: str,
                 duration: float, seed: int, route: str = 'LOCAL') -> dict[str, Any]:
        if route != 'LOCAL':
            raise ValueError('WRONG_ROUTE_NO_FALLBACK')
        validate_inputs(plan, requirements, brief, current, reviewed_brief)
        if state != 'LOCAL_ENGINEERING_POC':
            raise ValueError('EXPLICIT_LOCAL_POC_STATE_REQUIRED')
        install = self.inspect_capabilities()
        if (qualification.get('binding') != install['binding'] or qualification.get('route') != 'LOCAL'
                or qualification.get('requirementsFingerprint') != sha256_canonical(requirements)):
            raise ValueError('STALE_QUALIFICATION')
        if poc_evidence.get('binding') != install['binding'] or not all(poc_evidence.get(k) is True for k in (
                'modelLoaded', 'wavValid', 'durationValid', 'offline', 'instrumentalTargetExecuted')):
            raise ValueError('LOCAL_POC_BASELINE_REQUIRED')
        # Human certainty about vocals is NOT inferred from an instrumental prompt.
        if candidate not in {'A', 'B'}:
            raise ValueError('MAX_TWO_PRIMARY_CANDIDATES')
        if not math.isfinite(duration) or not requirements.duration_range[0] <= duration <= requirements.duration_range[1]:
            raise ValueError('DURATION_OUTSIDE_REQUIREMENTS')
        mapping = map_brief(brief, translation)
        trace_path = self.directory / f'provider-mapping-{candidate}.json'
        output = self.directory / 'audio' / f'candidate-{candidate}.wav'
        (self.directory / 'audio').mkdir(exist_ok=True)
        trace = {**mapping, 'providerFamily':FAMILY, 'route':'LOCAL', 'model':self.config.model,
                 'installationBinding':install['binding'], 'composerBriefFingerprint':sha256_canonical(brief),
                 'requirementsFingerprint':sha256_canonical(requirements), 'sourcePins':dict(current),
                 'qualificationAtGeneration':dict(qualification), 'requestedDuration':duration, 'seed':seed,
                 'adapterParameters':{'steps':8, 'cfg':3.0, 'seed':seed, 'duration':duration, 'device':'Metal'},
                 'outputFile':str(output), 'formalWrites':0, 'adopted':False,
                 'status':'STARTED', 'executionStart':datetime.now(timezone.utc).isoformat()}
        # O_EXCL is the durable reservation; even an uncertain/crashed result consumes this slot.
        try:
            with trace_path.open('x') as stream:
                json.dump(trace, stream, ensure_ascii=False, indent=2)
        except FileExistsError as exc:
            raise ValueError('EXISTING_OR_AMBIGUOUS_RESULT_NO_RESUBMIT') from exc
        if output.exists():
            trace['status'] = 'AMBIGUOUS_RESULT'
            write_json(trace_path, trace)
            raise ValueError('UNJOURNALED_OUTPUT_NO_RESUBMIT')
        started = time.monotonic()
        try:
            execution = run_local(self.config, self.directory, f'candidate-{candidate}', mapping,
                                  duration=duration, seed=seed, output=output)
            metadata = inspect_wav(output, duration)
            if not metadata['durationPass'] or not metadata['nonSilent']:
                raise ValueError('OUTPUT_TECHNICAL_FAILURE')
            trace.update(status='GENERATED_LOCAL_CANDIDATE', approval='NOT_APPROVED', adoption='NOT_ADOPTED',
                         eligibility='NOT_PRODUCTION_ELIGIBLE', sha256=metadata['sha256'], execution=execution)
            write_json(self.directory / f'candidate-{candidate}-metadata.json', metadata)
        except BaseException:
            trace['status'] = 'AMBIGUOUS_RESULT' if output.exists() else 'FAILED_NO_AUTO_RETRY'
            raise
        finally:
            trace['executionEnd'] = datetime.now(timezone.utc).isoformat()
            trace['wallSeconds'] = time.monotonic() - started
            write_json(trace_path, trace)
        return trace

    def get_result(self, candidate: str) -> dict[str, Any]:
        if candidate not in {'A', 'B'}:
            raise ValueError('UNKNOWN_CANDIDATE')
        record: dict[str, Any] = json.loads((self.directory / f'provider-mapping-{candidate}.json').read_text())
        if record['status'] != 'GENERATED_LOCAL_CANDIDATE' or digest(Path(record['outputFile'])) != record['sha256']:
            raise ValueError('RESULT_UNKNOWN_OR_CHANGED')
        return record


def run_local(config: LocalConfig, directory: Path, run_id: str, mapping: Mapping[str, Any], *,
              duration: float, seed: int, output: Path, init_audio: Path | None = None,
              edit_window: tuple[float, float] | None = None, noise: float = 1.0) -> dict[str, Any]:
    """Internal bounded qualification/inference worker, not a Tool or public business contract."""
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id) or not 0 < duration <= 35:
        raise ValueError('INVALID_PROBE')
    if not output.resolve().is_relative_to(directory.resolve()) or output.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW_TASK_ARTIFACT')
    if init_audio is not None and not init_audio.resolve().is_relative_to(directory.resolve()):
        raise ValueError('REFERENCE_MUST_BE_TASK_GENERATED')
    validation = directory / 'validation'
    validation.mkdir(exist_ok=True)
    job = {'root':str(config.root), 'model':config.model, 'prompt':mapping['renderedPrompt'],
           'negative':mapping['negativeInstructions'], 'duration':duration, 'seed':seed,
           'output':str(output.resolve()), 'metrics':str((validation / (run_id + '-metrics.json')).resolve()),
           'initAudio':str(init_audio.resolve()) if init_audio else None, 'editWindow':edit_window, 'noise':noise}
    request = validation / (run_id + '-request.json')
    with request.open('x') as stream:
        json.dump(job, stream, ensure_ascii=False, indent=2)
    # No inherited credentials, project environment, network configuration or wrapper bootstrap.
    env = {k:os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'LANG') if k in os.environ}
    env.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
               DO_NOT_TRACK='1', PYTHONDONTWRITEBYTECODE='1')
    with (validation / (run_id + '.log')).open('w') as log:
        result = subprocess.run([str(config.python), '-B', str(Path(__file__).with_name('stable_audio_worker.py')),
                                 str(request.resolve())], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode:
        raise ValueError('LOCAL_EXECUTION_FAILED_NO_FALLBACK: ' + str(result.returncode))
    metrics: dict[str, Any] = json.loads(Path(job['metrics']).read_text())
    if metrics['networkAttempts'] != 0 or metrics['downloads'] != 0:
        raise ValueError('OFFLINE_BOUNDARY_VIOLATION')
    return metrics
