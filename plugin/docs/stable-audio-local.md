# Stable Audio 3 provider family / P1

Director owns WHY; music-direction owns HOW SCORE SERVES INTENT; provider owns execution;
host owns orchestration. Existing FilmScorePlan → MusicCue → ComposerBrief →
MusicGenerationRequirements remains the semantic input. No new Skill, Tool, Agent,
DB table, Java endpoint, MCP method, or top-level business contract.

`providers.music.stable_audio.StableAudio3Provider` is an opt-in synchronous Python
adapter, following the existing local host renderer / speech mapping pattern. It is
called by a host after `LocalCapabilityBridge` finishes DESIGN_ONLY music review.
That bridge deliberately stays DESIGN_ONLY. It never gains generation permission.
`integration/stable_audio_local_poc.py` provides the local artifact orchestration.

Configuration is external, following DRAMA_PLUGIN provider naming:
`DRAMA_PLUGIN_STABLE_AUDIO_LOCAL_ROOT` (optimized/mlx root),
`DRAMA_PLUGIN_STABLE_AUDIO_LOCAL_PYTHON` (existing Python executable),
`DRAMA_PLUGIN_STABLE_AUDIO_LOCAL_MODEL` (`medium` or `sm-music`). No implicit install,
model download, environment bootstrap or cloud fallback. `inspect_installation`
hashes code and local weights; directory existence is not model readiness.
The isolated worker substitutes an offline-only resolver before importing the CLI,
denies Python socket/process activity, strips credential environment variables,
checks prompt token lengths and records native load/runtime/memory observations.
Native traffic is not packet-captured; don't describe Python instrumentation as an OS firewall.

Only an explicitly source-bound LOCAL_ENGINEERING_POC is authorized by this adapter.
Human instrumental certainty is UNKNOWN until listening. The bounded technical probe
executes the instrumental target and checks load, WAV, duration and offline behavior;
that is eligibility for a nonproduction listening experiment, not a no-vocals PASS.
Production requirements remain blocked whenever a required capability is unsupported
or UNKNOWN. A separate instrument generation (A) never means synchronized stems (B).

Host-provided field translations are artifacts pinned to the exact reviewed Brief.
Only cue-level text reaches the model. No production book, future scene or screenplay
is sent. Parameters and seed live in mapping traces only. Two durable candidate slots
use exclusive-create reservations. Failure, crash or ambiguous output never resubmits.
All results stay task artifacts, NOT_APPROVED / NOT_ADOPTED / NOT_PRODUCTION_ELIGIBLE.
`get_result` checks the output hash before returning a synchronous retained result.

`StableAudio3CloudRoute` is a disabled configuration / five-gate boundary, with
qualification NOT_STARTED and generationAuthorized false. It contains no key, URL,
HTTP request or guessed payload. All five future gates (configured, qualified, rights
reviewed, cost known, generation authorized) are necessary but this P1 placeholder
never executes even when its booleans are set. Local evidence cannot qualify Cloud.
A later independently authorized adapter can consume the same neutral requirements;
quality and prompt mapping parity are not promised.
