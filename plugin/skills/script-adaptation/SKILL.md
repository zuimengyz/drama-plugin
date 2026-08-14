---
name: script-adaptation
description: Adapt a historical-drama Work into a screen Script. Use when designing the audiovisual dramatic structure, main and secondary lines, character arcs, pacing, escalation, climax, or short-form series shape.
---

# Script Adaptation

Preserve the Work's dramatic truth while translating it into observable screen action. Define the main line, necessary secondary lines, character arcs, pacing, escalation, climax, and short-form structure without replacing the Work's historical or creative boundaries.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Script or revises an existing one, the target Work, requested adaptation scope and outcome, and explicit format, length, audience, tone, or continuity constraints.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the relevant Work and adaptation constraints are supplied. Use `work.get_work` for a known `workId`; use `script.get_script` for a known `scriptId`; otherwise use `script.list_scripts` under the known Work and judge the structured candidates. Use `context.build_context` only when required Work or existing Script context was not supplied.

Use adequate research context first. When a consequential adaptation decision depends on an unresolved historical claim, use `research.verify_claim`. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. Do not repeat research for settled context. If the governing Work, essential constraints, or consequential evidence cannot be obtained or conflict, state the blocker and do not draft or persist.

### 3. Plan

Create an internal Script plan stating the adaptation goal, Work facts and character truths that must be inherited, constraints that cannot be violated, the intended audiovisual structure and progression, the main/secondary lines, arcs, pacing, escalation, climax, and short-form shape required in the draft, and unresolved questions that must be settled first. Keep it in Agent Run Context or temporary working state. Do not call `script.create_script` or `script.save_script` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Script state. Prefer observable action over explanatory prose and preserve continuity with the Work. The draft must be detailed enough for Script review and later Episode development; it must not be a plot-summary fragment, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Review the complete draft before any write. Critical checks are: main and necessary secondary lines support the Work; character arcs, pacing, escalation, climax, and short-form structure are coherent; the result is screenable rather than merely explanatory; Work truth and consequential historical constraints remain intact; and no material continuity conflict is unresolved. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Locally revise wording, isolated pacing, completeness, or minor continuity defects. Re-plan the current Script when the main line, character arc, overall structure, escalation, climax, or fidelity to the Work fails. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist, all critical checks pass, and no historical or continuity conflict remains. Plan, draft reasoning, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Script `content`. Persist only the reviewed formal result.

Use `script.create_script` only for a genuinely new adaptation after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `script.save_script` immediately afterward unless a concrete revision has actually occurred. Use `script.save_script` only to revise an already persisted Script because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Work ID and Script title in the create envelope; use the stable Script ID and title for a revision. Put the reviewed audiovisual structure, lines, arcs, pacing, escalation, climax, and other formal adaptation facts in `content`. Do not move the parent Work ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not create Episodes or call another Skill automatically.
