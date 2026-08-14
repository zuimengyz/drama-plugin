---
name: work-creation
description: Create or revise a historical-drama Work from research context. Use when defining literary premise, theme, viewpoint, relationships, central conflict, dramatic timeline, or the overall structure of the source work.
---

# Work Creation

Turn research context into a coherent literary Work, not a historical-event summary. Establish theme, viewpoint, relationships, central conflict, dramatic timeline, and overall structure while keeping consequential fact, uncertainty, and invention distinguishable.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Work or revises an existing one, the requested scope and outcome, the creative intent, and explicit audience, format, tone, historical, or user constraints. Do not treat a title or event name as sufficient creative intent.

### 2. Gather Context

Assess context sufficiency before planning. Continue when creative intent and adequate research context are supplied. When a stable `workId` is known, use `work.get_work`; when only a title or natural-language identity is known, use `work.search_works` and judge candidates; use `work.list_works` only to enumerate the available structural scope. Use `context.build_context` only when an existing Work context is required and was not supplied.

For a consequential evidence-dependent choice, use adequate supplied evidence first and use `research.verify_claim` only for an unresolved claim. If broader evidence is missing, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. Do not repeat research for facts already supported. If essential creative intent, evidence, or constraints remain missing or contradictory after available Tool use, state the blocker and do not draft or persist.

### 3. Plan

Create an internal Work plan that states the Work's goal, inherited historical facts, constraints that must not be violated, intended dramatic structure or state change, the premise/theme/viewpoint/relationships/conflict/timeline/structure required in the draft, and unresolved questions that must be settled first. Keep the plan in Agent Run Context or temporary working state. Do not call `work.create_work` or `work.save_work` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Work state. The draft must be detailed enough for Work review and later Script adaptation; it must not be a few-line event summary, placeholder fields, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Review the complete draft before any write. Critical checks are: theme, viewpoint, relationships, central conflict, timeline, and structure form one coherent literary Work; the result is more than a historical summary; consequential historical constraints, uncertainty, and dramatic invention are explicit; and no user or continuity constraint is unresolved. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Locally revise wording, completeness, or minor consistency defects. Re-plan the current Work when premise, central conflict, overall structure, historical boundary, or creative purpose fails. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist, all critical checks pass, and no historical or continuity conflict remains. Plan, draft reasoning, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Work `content`. Persist only the reviewed formal result.

Use `work.create_work` only for a genuinely new Work after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `work.save_work` immediately afterward unless a concrete revision has actually occurred. Use `work.save_work` only to revise an already persisted Work because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep title and optional description in the Stable Envelope; place the reviewed premise, theme, viewpoint, relationships, conflict, timeline, structure, and other formal creative facts in the `content` object. Do not hide, duplicate, or rename envelope fields inside `content`, and never submit stringified JSON, scratchpad reasoning, or raw Tool results. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not create a Script merely because the Work is complete.
