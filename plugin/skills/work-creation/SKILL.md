---
name: work-creation
description: Create or revise a historical-drama Work from research context. Use when defining literary premise, theme, viewpoint, relationships, central conflict, dramatic timeline, or the overall structure of the source work.
---

# Work Creation

Turn research context into a character-driven story foundation that can govern later screen adaptation, not a historical-event summary or a premature Script. Establish the premise, protagonist, conflict, stakes, theme, arcs, historical boundary, and major story architecture.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Work or revises an existing one, the requested scope and outcome, and the type, audience, scale, short-form intent, tone, period, and explicit user constraints. Make conservative working assumptions for non-critical omissions and record them in the internal plan; contradictory critical constraints block progress. Do not treat a title, event name, chronology, or famous person as sufficient creative intent.

### 2. Gather Context

Assess context sufficiency before planning. Continue when creative intent, format constraints, and adequate research context are supplied. When a stable `workId` is known, use `work.get_work`; when only a title or natural-language identity is known, use `work.search_works` and judge candidates; use `work.list_works` only to enumerate the available structural scope. Use `context.build_context` only when an existing Work context is required and was not supplied.

For a consequential evidence-dependent choice, use adequate supplied evidence first and use `research.verify_claim` only for an unresolved claim. If broader evidence is missing, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. Do not repeat research for facts already supported. If essential creative intent, evidence, or constraints remain missing or contradictory after available Tool use, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Work Planning](references/planning.md) and apply it. Create an internal Work plan that converts the historical subject into a dramatic proposition: define the creative brief and evidence boundary; briefly compare viable choices for protagonist, viewpoint, entry point, central conflict, and climax; then select a premise, protagonist goal and need, capable opposition, escalating stakes, thematic question, character and relationship arcs, causal story architecture, ending, and short-form shape. State inherited facts, forbidden changes, invention space, required downstream content, and unresolved questions. Keep the plan in Agent Run Context or temporary working state. Do not call `work.create_work` or `work.save_work` to store it.

### 4. Execute Draft

Execute the selected plan as a complete candidate formal Work state. Preserve the causal chain from pressure through choice to consequence; make the protagonist active, the opposition intelligible, the stakes concrete, and the arcs and historical/invention boundary usable downstream. The result must independently tell Script adaptation what the story is, why it moves, how it culminates, and what must not drift. It must not be a few-line event summary, chronology dump, character list, placeholder, test content, scratchpad, Scene dialogue, or Shot detail. Do not persist a partial draft.

### 5. Review

Before any write, read [Work Review and Revision](references/review.md) and apply the entire domain rubric to the complete draft. Critical checks cover story identity, protagonist agency and motivation, opposition, stakes, dramatic causality, character and relationship arcs, theme, viewpoint, central conflict, timeline, structure, historical integrity, short-form suitability, and downstream readiness. A historical summary, inert chronology, unsupported historical drift, or incomplete story foundation is a critical failure. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow the defect routing in [Work Review and Revision](references/review.md): Locally revise wording, isolated clarity, or minor consistency defects; Re-plan the current Work when story identity, protagonist agency, premise, opposition, stakes, causal architecture, climax, arc, historical boundary, or creative purpose fails. Rewrite the draft when structural failures are pervasive. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist as a formal story foundation, all critical checks in the Work rubric pass, and no historical or continuity conflict remains. A mere event summary, theme label, character list, timeline, one-line premise, passive protagonist, conflict without actionable opposition, missing stakes, or story without climax and ending cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Work `content`. Persist only the reviewed formal result.

Use `work.create_work` only for a genuinely new Work after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `work.save_work` immediately afterward unless a concrete revision has actually occurred. Use `work.save_work` only to revise an already persisted Work because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep title and optional description in the Stable Envelope; place the reviewed premise/logline, creative brief, protagonist and major arcs, opposition, stakes, theme, relationships, evidence boundary, story architecture, ending, and other formal creative facts in the open `content` object. These are creative content, not a request for new persistence fields. Do not hide, duplicate, or rename envelope fields inside `content`, and never submit stringified JSON, scratchpad reasoning, or raw Tool results. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not write Episode, Scene, dialogue, camera, or Shot design, and do not create a Script merely because the Work is complete.
