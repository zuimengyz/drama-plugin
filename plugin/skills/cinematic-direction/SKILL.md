---
name: cinematic-direction
description: Translate approved Shot narrative into source-pinned visual direction, observable acting and a timed director execution spec before video model selection. Use for look, camera, performance and within-shot beats; not story rewriting, media generation or voice selection.
---

# Cinematic Direction & Performance

影视导演、摄影质感与人物表演。 One Skill, four connected capabilities:
**Look Development, Cinematography, Performance Direction, Temporal Beat Planning**.
Their common output is `CinematicShotSpec`, not four independently versioned plans.

Abstract Intent → Observable Behaviour → Temporal Execution. “电影感、史诗感、悲伤、
紧张、愤怒、英勇、高级感、大片感、震撼、真实 / cinematic, epic, dramatic, masterpiece”
may explain intention; they cannot constitute the main execution information.
The Host authors concrete behavior in context. Do not implement a universal
emotion-to-gesture dictionary or force every character through the same ticks.

## Creative Lifecycle

### 1. Understand Goal

Respect the existing Shot's narrative job, historical facts, result, position and
dialogue. This node realizes the approved action; it cannot add events, change
relationships/positions, rewrite an ending, invent speech or import period-wrong
props. Preserve adopted media and their native-audio policy. Text direction is not
authorization to generate, upload, synthesize speech or alter an existing movie.

### 2. Gather Context

Use supplied current context, otherwise `shot.get_shot`, `scene.get_scene`,
`episode.get_episode`, `script.get_script`, `work.get_work`; use
`context.build_context` only for a missing context projection. Pin these source
identities, canonical bound SpokenContent, duration, rhythm, prior/next state and
any applicable Cinematic Intent, Dramatic Bible and DPD. Existing DPD owns dramatic
objective/tactic/relationship; this projection supplies physical acting and camera.
Do not reinterpret DPD as another character/Voice identity or duplicate its system.

Read [the director contract](../../docs/cinematic-direction-contract.md) for the
actual IR, inheritance, source fingerprint, offline entry and selection handoff.
Reference duties may be planned without images: a desired role is not an Asset,
an upload, a first frame, or an assertion that the source already exists.

### 3. Plan

Keep working decisions in the existing Agent Run Context. Inherit Work VisualBible
through explicit Episode → Scene → Shot overrides and inspect inherited/override/
effective views. Arrays replace; omitted keys inherit; no vague null reset. Establish
palette, motivated source lighting/fill, allowable face shadow, highlight/black
behavior, saturation/contrast, skin/cloth/metal/environment, atmosphere and camera
philosophy. Justify local differences rather than copying a bible into each prompt.

Choose framing, placement/height, subject orientation, lens family/intent, focus
target/transition and opening/ending composition. LOCKED is valid; RESTRAINED,
MOTIVATED or DYNAMIC movement needs a trigger, amplitude and reason: why now?
Use practical descriptions instead of unsupported focal lengths/centimeters.

For each relevant person ask what they want from whom, what belief they try to
create or conceal, and what changes. Convert that arc into selected gaze, eyelid,
jaw, breath, shoulder/weight, hand/prop, speech or reaction behavior. Do not fill
every anatomical field. A Behavior Anchor states what was already underway before
the trigger, with identity/history/continuity basis. Omit it when the main action
is already underway or the Shot does not need it; do not add a new plot event or
a complete dressing/drinking routine merely to animate the first frame.

### 4. Execute Draft

Build Opening → meaningful Performance Beats → Ending. Use as many beats as
action, information, speech and response need, never a fixed count or per-second
quota. Simple action may be one beat. Allow purposeful holds/pauses/continuous
action and motivated overlaps explicitly. Share boundary states to expose prop
and position jumps. Fit the formal duration and preserve canonical dialogue's
planning allowance; no silent acceleration or fake millisecond precision.

Dialogue direction can say when, toward whom, with what vocal intention, emphasis,
pause, gaze and after-line reaction. Preserve text/ID/speaker exactly. It does not
produce audio, choose a Voice or revise a selected native track.

Add only meaningful secondary motion: sleeve lag from a raised arm, loose hair
settling after a turn, a curtain moved by established wind, or dust at hoof contact.
For effects show interaction: cause → affected body/material/ground/air/light →
visible response, including occlusion/depth. Avoid unexplained wind, constant
floating cloth or indiscriminate particles. No effect is required merely because
the schema supports it.

Define the **Shot Stability Contract** as allowed versus forbidden degrees of
freedom. It is **not a Negative Prompt**. Standing may be allowed while position
teleportation is forbidden; camera advance may be allowed while an unmotivated
orbit is not. Choose applicable identity/costume/architecture/cut/text/focus bounds;
do not globally forbid every change.

Reference Requirements distinguish character, costume, location, look,
composition, camera motion, performance, VFX and continuity. Each has a subject,
purpose and REQUIRED/PREFERRED importance. Never assign all roles to one portrait
or equate a character reference with an opening frame. Do not choose upload count,
model, template or mode here. Existing preparation cap of three references and
video single-image or same-target start/end contract remain unchanged downstream.

Express Execution Requirements as demands for duration, micro-expression, temporal
adherence, multi-beat/prop interaction, camera/secondary-motion complexity and
identity/costume/environment continuity. These are Host-authored needs, not model
scores, claimed capabilities, quality proof, price estimates or provider controls.

### 5. Review

Reuse the current complete-draft review. Check ordinary viewing usefulness, not
an exhaustive perfection checklist. For a finding record observed wording/state,
why it affects execution, and the smallest revise. Review:

- empty emotional labels; unchanged expression without purpose; a person waiting
  for the plot instead of already inhabiting the situation;
- camera movement without cause or identical movement applied to unrelated beats;
- unexplained look drift, unsupported light source, missing opening/ending,
  reversed/overflowing time, prop or position discontinuity;
- relevant secondary motion omitted, or effects without material/space interaction;
- missing meaningful stability boundaries or references without specific duties;
- any historical/Script/DPD contradiction, added words or deleted action.

Code supplies structural checks and a few explanatory warnings, not an artistic
score. The Host reviews semantics that text matching cannot prove. A deliberate
still expression, locked camera, absent anchor or absent effects can be right.
Unconfirmed concerns do not become major errors; ordinary notes do not require
user approval. Offline PASS concerns executable text, never generated visual quality.

### 6. Revise or Re-plan

Use the existing plan → draft → review → revise/re-plan loop. Repair only the
unsupported gesture, beat timing, camera cause, reference duty or visual override.
If the problem is upstream canon, identify that constraint instead of rewriting
history. Re-review the complete result. No new planner, revision state machine,
art score, manual approval layer or per-target retry lock is introduced.

### 7. Persist

Freeze the reviewed spec and source/visual inheritance fingerprints as
`CINEMATIC_DIRECTION_FROZEN`, then return its Execution and Reference Requirements
to video-model-selection. Selection still owns capability/quality/cost evidence,
mode, input preparation and template choice. A changed director spec requires the
existing re-plan/requalification and request sealing, not a bypass of fingerprints.

The formal result may live in existing `Shot.content.creativeArtifacts` via
`shot.save_shot`, or a stable source-pinned Creative IR artifact for a text-only
run. Preserve unrelated content on full replacement; do not create new tables,
Media, or a second revision authority. This stage's Dry Run uses artifacts only.
The packaged `scripts/direct_shot.py` validates, reviews, freezes and emits a
provider-neutral execution brief plus the real selection handoff without network
or production calls. Whole-scene or modality changes remain the caller's decision.

## Canonical coverage and generation-time sound

A line shared across speaker/reaction/off-screen Shots uses the existing Scene
spoken item, formal coverageIntent and a reviewed contiguous coverage artifact.
Each Shot carries only its interval and canonical text range; never repeat the
whole sentence or add text/timing to Shot bindings. Freeze and recheck the group
against current formal Shots. Timing estimates remain planning data.

Include SourceSoundIntent for new production: native audio policy, canonical IDs,
meaningful diegetic/ambient sound, silence, generated music policy and continuity.
No Voice, mix, repair recipe or generation belongs here. DPD → CinematicShotSpec
is the single new-schema execution authority; legacy visual briefs are lineage.
Reference roles pass downstream for actual fulfillment; absence is not fulfillment.
