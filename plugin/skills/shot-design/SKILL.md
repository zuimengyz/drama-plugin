---
name: shot-design
description: Design or revise shots for a historical-drama Scene. Use when choosing framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, or shot entry and exit state.
---

# Shot Design

Express an approved Scene through minimal necessary, narratively motivated, continuous, provider-agnostic coverage. Plan the group before individual Shots; every Shot must declare Narrative Input State, Required Transition, and Narrative Output State in addition to visual entry/exit state. Do not redesign the Scene or produce media.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates new Shot coverage or revises existing Shots, the parent Scene and exact coverage scope, the requested visual outcome, and explicit format, duration, continuity, stable-reference, or production constraints. Identify what the camera must express about the Scene turn. Do not equate one sentence or dialogue line with one Shot automatically.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the approved Scene's assigned historical beats, Narrative Input/Output State, Required Transition, purpose/action/turn, spatial layout, blocking, time/environment, neighboring Shot states, and production constraints are supplied. Use `scene.get_scene` for the stable parent and `shot.get_shot` for a known `shotId`. With a known `sceneId`, use `shot.list_shots` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `shot.search_shots` scoped to the Scene when possible and judge candidates.

Use `asset.get_asset` or `media.get_media` only when a selected stable reference is needed to judge character, location, prop, wardrobe, or visual continuity. Use `context.build_context` only when required parent or existing Shot context was not supplied. Consume approved historical context rather than repeating research per Shot. If a consequential historical issue is unresolved, formulate a focused question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Scene intent, required references, spatial state, or continuity cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Shot Planning](references/planning.md) and apply it. Create an internal coverage plan that inherits rather than repairs the Scene; define required historical/story observations, coverage strategy, Shot economy, and for each retained Shot its narrative purpose, `narrativeInputState`, `requiredTransition`, `narrativeOutputState`, subject/action/blocking, camera language, rhythm, visual entry/exit state, continuity, references, and feasibility. Keep it in Agent Run Context or temporary working state. Do not call `shot.create_shot` or `shot.save_shot` to store it.

### 4. Execute Draft

Execute the strategy as complete candidate formal Shot states that together cover the Scene turn with the fewest necessary Shots. Make camera choices serve information, performance, spatial relation, emotion, action, or continuity; preserve screen direction, axis/eyeline, positions, action phase, performance energy, assets, props, costume, time, lighting, and ongoing motion. Simplify, split, or redesign an overloaded Shot until its action, space, movement, references, and entry/exit states are executable downstream. The draft must not be one-line-one-shot splitting, redundant coverage, camera labels without subject/action, test content, or scratchpad. Do not persist partial Shot drafts.

### 5. Review

Before any write, read [Shot Review and Revision](references/review.md) and apply the entire coverage rubric. Critical checks are reported as `CHARACTER_VISUAL_CONTINUITY`, `COSTUME_PERIOD_CONTINUITY`, `PROP_STATE_CONTINUITY`, `SHOT_ACTION_CONTINUITY`, `SCENE_STATE_CONTINUITY`, `CAUSAL_NARRATIVE_CONTINUITY`, `HISTORICAL_BEAT_COVERAGE`, and `FULL_STORY_ARC` separately. If `Previous Narrative Output State → Current Narrative Input State` fails or an indispensable action/state is skipped, return `FAIL_NARRATIVE_TRANSITION` even when visual checks pass. Unmotivated or redundant coverage, unresolved narrative continuity, unproducible complexity, or failure to cover the Scene turn is critical. Mark Review PASS only when every gate passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow [Shot Review and Revision](references/review.md): Locally revise one framing, angle, movement, duration, composition, or minor continuity defect. Re-plan the current Shot group when coverage strategy, economy, spatial/axis logic, Scene-turn coverage, or generation feasibility fails. If the Scene lacks playable conflict/action/state change, label an upstream Scene issue instead of hiding it with camera technique. After any revision or re-plan, review the complete coverage again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft coverage exist, all critical checks pass, and the design is minimal necessary, narratively motivated, continuous, and production-ready without unresolved Scene/reference conflict. One-line-one-shot splitting, repeated coverage, missing narrative purpose or subject/action, spatial/action discontinuity, asset drift, or unproducible complexity cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Shot `content`. Persist only reviewed formal Shot results.

Use `shot.create_shot` only for a genuinely new Shot after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `shot.save_shot` immediately afterward unless a concrete revision has actually occurred. Use `shot.save_shot` only to revise an already persisted Shot because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Scene ID, string-valued shot number, optional title, and optional shot type in the create envelope; use the stable Shot ID, shot number, title, and type for a revision. Put reviewed narrative purpose, Narrative Input State, Required Transition, Narrative Output State, subject/action/blocking, camera language, continuity dimensions, references, feasibility, visual entry/exit state, and other formal Shot facts in the open `content` object. These are creative content, not new persistence fields. Do not move the parent Scene ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Read a stable Asset/Media only when continuity requires it; do not create or resolve assets, produce media, add provider workflow/model parameters, redesign the Scene, or automatically invoke another Skill.
