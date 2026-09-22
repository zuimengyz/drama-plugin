# Narration Line and full Director screenplay

Narration Line owns the continuous spoken narration strategy; Authorial Voice keeps
closure-node intervention eligibility and its actual-use scarcity ledger. Dialogue
owns diegetic words. Literature-to-Cinema owns upstream cinematic permission,
including ExplicitnessException. Director consumes these originals and coordinates
professional handoffs. Audio/voice identity/casting own downstream delivery and
execution; no provider controls enter narration contracts.

`contracts/narration.py` defines NarrationBible, NarrationCue, scene silence,
NarrationPerformanceIntent, UpstreamChangeRequest and FullDirectorScreenplay.
`narration.py` is the pure validator/compiler. The skill CLI is a real offline
consumer; skill.yaml is discovered by the existing SkillRegistry. This release
supports the LiteraryPackage adapter, not unimplemented historical narration.

NarrationContext replays the existing P0 compiler and exact screenplay beat spans.
Narration review hashes bind the entire context and plan; Director hashes bind the
narration plan, screenplay and Character Dramaturgy. There is no adoption API.
Every result is candidate-only and P2=false. Structural acceptance does not certify
literary quality, translation accuracy or whether silence is artistically superior.

SOURCE_NARRATOR_FUNCTION is an exact source excerpt; ADAPTED_SOURCE_NARRATOR is a
newly worded expression with direct NARRATOR units. CHARACTER_THOUGHT_SOURCE uses
INTERNAL_STATE units and only character narration types. New narration invention
always returns HUMAN_CONFLICT, even if its self-review claims FUNCTION_ONLY.
Original and adapted narration remain distinct from SOURCE_FACT downstream.

A cue must bind an adaptation decision/destination, source units, their anchors and
existing SourceMap rows. If upstream cinema lacks a source-scoped VO grant, the cue
requires an explicit pending upstream request and returns UPSTREAM_CHANGE_REQUIRED.
The Director consumer rejects unresolved narration; it never patches upstream.
NONE has no cues and every scene has a first-class SILENCE reason.

FullDirectorScreenplay enumerates scene intent and handoffs, not lenses, timings,
assets or storyboard. It references exact CharacterArc stages instead of redefining
them; its prose is specialist-authored and requires human semantic review. The
validator verifies bindings and fields, not the truth of prose judgments.
