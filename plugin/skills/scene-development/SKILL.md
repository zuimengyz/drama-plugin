---
name: scene-development
description: Develop or revise a historical-drama Scene from an Episode. Use when defining place, time, characters, entry state, objective, conflict, dialogue, action, turn, or exit state.
---

# Scene Development

Develop a playable Scene with a concrete dramatic purpose. Define place, time, participants, entry state, objective, conflict, dialogue, action, turn, and exit state so the Scene changes the Episode rather than merely describing it.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Scene or revises an existing one, the parent Episode, requested dramatic moment and outcome, and explicit location, time, character, continuity, historical, or user constraints.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the Episode purpose, relevant character state, and required before/after continuity are supplied. Use `episode.get_episode` for the stable parent and `scene.get_scene` for a known `sceneId`. With a known `episodeId`, use `scene.list_scenes` for structural enumeration and neighboring continuity; when only a natural-language identity is known, use `scene.search_scenes` scoped to the Episode when possible and judge candidates.

Use `context.build_context` only when required parent or existing Scene context was not supplied. Use adequate research context first; use `research.search_locations` only when missing location evidence affects the Scene and `research.verify_claim` only for a consequential unresolved claim. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If Episode intent, character state, essential continuity, or consequential evidence cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Create an internal Scene plan stating its dramatic purpose, Episode and character facts that must be inherited, constraints that cannot be violated, the intended entry-to-exit state change, the place/time/participants/objective/conflict/action/turn/dialogue/exit state required in the draft, and unresolved questions that must be settled first. Keep it in Agent Run Context or temporary working state. Do not call `scene.create_scene` or `scene.save_scene` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Scene state in playable action and dialogue. The draft must be detailed enough for Scene review and later Shot design; it must not be characters plus location, a static conversation summary, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Review the complete draft before any write. Critical checks are: the Scene has a concrete dramatic purpose, objective, conflict, playable action, turn, and explicit entry/exit states; dialogue and action advance the Episode; the exit state differs meaningfully through information, relationship, decision, danger, or goal change; and no material historical or continuity conflict is unresolved. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Locally revise wording, a dialogue beat, action clarity, completeness, or minor continuity defects. Re-plan the current Scene when its purpose, objective, conflict, turn, entry-to-exit change, or Episode function fails. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist, all critical checks pass, and no historical or continuity conflict remains. Plan, draft reasoning, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Scene `content`. Persist only the reviewed formal result.

Use `scene.create_scene` only for a genuinely new Scene after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `scene.save_scene` immediately afterward unless a concrete revision has actually occurred. Use `scene.save_scene` only to revise an already persisted Scene because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Episode ID, scene order, title, and optional location in the create envelope; use the stable Scene ID, order, title, and optional location for a revision. Put reviewed characters, time, entry state, objective, conflict, dialogue, action, turn, exit state, and other formal Scene facts in `content`. Do not move the parent Episode ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not generate Shots or resolve assets automatically.
