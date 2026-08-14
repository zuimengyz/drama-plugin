---
name: scene-development
description: Develop or revise a historical-drama Scene from an Episode. Use when defining place, time, characters, entry state, objective, conflict, dialogue, action, turn, or exit state.
---

# Scene Development

Turn one approved part of an Episode into a necessary, playable, state-changing dramatic event. Make a character pursue an immediate objective against real opposition, change tactics under pressure, act through meaningful beats, and reach a turn that changes the story rather than merely discussing it. Do not design Shots.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Scene or revises an existing one, the parent Episode, requested dramatic moment and outcome, and explicit location, time, character, continuity, historical, or user constraints. Identify the concrete change that makes this Scene necessary; “show a relationship” or “discuss the situation” is not yet a sufficient purpose.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the Episode dramatic job and current objective, character and relationship state, known information, historical boundary, previous Scene exit state, next intended direction, and required continuity are supplied. Use `episode.get_episode` for the stable parent and `scene.get_scene` for a known `sceneId`. With a known `episodeId`, use `scene.list_scenes` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `scene.search_scenes` scoped to the Episode when possible and judge candidates.

Use `context.build_context` only when required parent or existing Scene context was not supplied. Use adequate research context first; use `research.search_locations` only when missing location evidence affects the Scene and `research.verify_claim` only for a consequential unresolved claim. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Episode intent, character state, essential continuity, or consequential evidence cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Scene Planning](references/planning.md) and apply it. Create an internal Scene plan that inherits the Episode; state a change-based purpose, entry state, playable immediate objective, opposing force, immediate stakes, evolving tactics and beats, conflict-in-action, dialogue/subtext strategy, playable behavior, meaningful turn, exit state, necessity evidence, Shot-design contract, and unresolved questions. Keep it in Agent Run Context or temporary working state. Do not call `scene.create_scene` or `scene.save_scene` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Scene state in playable action and dialogue. Let resistance force tactic changes; use beats when objective, tactic, information, or power changes; let important information alter behavior; express interior states through behavior, movement, interaction, object use, reaction, choice, silence, distance, or position. The draft must let Shot design cover approved action without inventing the conflict. It must not be characters plus location, talking heads, historical exposition, static conversation, interior summary, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Before any write, read [Scene Review and Revision](references/review.md) and apply the entire domain rubric, Before/After Gate, and Delete Scene Test. Critical checks cover Episode fidelity, dramatic purpose, entry/exit state, objective, opposition, stakes, tactic/beat progression, conflict-in-action, dialogue/subtext function, playable action, turn, meaningful information/relationship/decision/danger/goal/power change, historical integrity, necessity, continuity, and downstream readiness. A Scene that only talks about conflict, cannot be played, or returns to the same state is a critical failure. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow [Scene Review and Revision](references/review.md): Locally revise dialogue, one tactic or beat, action clarity, subtext, or minor continuity. Re-plan the current Scene when its purpose, objective, opposition, conflict-in-action, turn, state change, playability, or necessity fails. If the root cause is the Episode dramatic job, label an upstream Episode issue instead of rewriting the Episode here. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist as a playable state-changing dramatic Scene, all critical checks pass, and no historical or continuity conflict remains. Characters-plus-location/dialogue, pure exposition, missing objective/opposition/turn/state change, unplayable interior summary, or a removable Scene cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Scene `content`. Persist only the reviewed formal result.

Use `scene.create_scene` only for a genuinely new Scene after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `scene.save_scene` immediately afterward unless a concrete revision has actually occurred. Use `scene.save_scene` only to revise an already persisted Scene because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Episode ID, scene order, title, and optional location in the create envelope; use the stable Scene ID, order, title, and optional location for a revision. Put reviewed purpose, characters, time, entry state, objective, opposition, stakes, tactics/beats, conflict, dialogue/subtext intent, playable action, turn, exit state, necessity, and other formal Scene facts in the open `content` object. These are creative content, not new persistence fields. Do not move the parent Episode ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not specify framing, camera position, coverage, create Shots, resolve assets, or automatically invoke another Skill.
