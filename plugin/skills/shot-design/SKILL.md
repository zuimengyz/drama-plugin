---
name: shot-design
description: Design or revise shots for a historical-drama Scene. Use when choosing framing, camera position, composition, blocking, action, expression, camera movement, dialogue coverage, duration, or shot entry and exit state.
---

# Shot Design

Cover the Scene's dramatic turn with the fewest necessary Shots. Give every Shot a dramatic function and production-meaningful framing, camera position, composition, blocking, action, expression, movement, dialogue coverage, duration, and entry/exit state while preserving continuity.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates new Shot coverage or revises existing Shots, the parent Scene and exact coverage scope, the requested visual outcome, and explicit format, duration, continuity, reference, or user constraints. Do not equate one sentence or dialogue line with one Shot automatically.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the approved Scene turn, relevant spatial and performance state, and required before/after continuity are supplied. Use `scene.get_scene` for the stable parent and `shot.get_shot` for a known `shotId`. With a known `sceneId`, use `shot.list_shots` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `shot.search_shots` scoped to the Scene when possible and judge candidates.

Use `asset.get_asset` or `media.get_media` only when a selected stable reference is needed to judge character, location, prop, wardrobe, or visual continuity. Use `context.build_context` only when required parent or existing Shot context was not supplied. Consume approved historical context rather than repeating research per Shot. If a consequential historical issue is unresolved, formulate a focused question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Scene intent, required references, spatial state, or continuity cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Create an internal Shot plan stating the coverage goal, Scene facts and visual states that must be inherited, constraints that cannot be violated, the intended visual and entry-to-exit progression, the dramatic function/framing/composition/blocking/action/camera behavior/duration/continuity required in each draft Shot, and unresolved questions that must be settled first. Keep it in Agent Run Context or temporary working state. Do not call `shot.create_shot` or `shot.save_shot` to store it.

### 4. Execute Draft

Execute the plan as complete candidate formal Shot states that together cover the Scene turn with the fewest necessary Shots. The draft must be detailed enough for Shot review and later production; it must not be mechanical sentence splitting, placeholder camera labels, test content, or scratchpad. Do not persist partial Shot drafts.

### 5. Review

Review the complete coverage before any write. Critical checks are: every retained Shot has a dramatic function, framing, composition, blocking/action, camera behavior, duration, and entry/exit state; coverage is sufficient without redundancy; spatial, performance, prop, wardrobe, action, and temporal continuity are coherent across neighboring Shots; and no material Scene or reference conflict is unresolved. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Locally revise framing, timing, wording, isolated continuity, or completeness defects. Re-plan the current coverage when a Shot lacks dramatic purpose or when coverage, camera strategy, Scene progression, or cross-Shot continuity fails. After any revision or re-plan, review the complete coverage again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft coverage exist, all critical checks pass, and no historical or continuity conflict remains. Plan, draft reasoning, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Shot `content`. Persist only reviewed formal Shot results.

Use `shot.create_shot` only for a genuinely new Shot after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `shot.save_shot` immediately afterward unless a concrete revision has actually occurred. Use `shot.save_shot` only to revise an already persisted Shot because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Scene ID, string-valued shot number, optional title, and optional shot type in the create envelope; use the stable Shot ID, shot number, title, and type for a revision. Put reviewed framing, camera, composition, blocking, action, expression, movement, dialogue coverage, duration, entry/exit state, and other formal Shot facts in `content`. Do not move the parent Scene ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not resolve assets or produce media automatically.
