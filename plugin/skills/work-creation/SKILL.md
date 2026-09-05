---
name: work-creation
description: Create or revise a historical-drama Work from research context. Use when defining literary premise, theme, viewpoint, relationships, central conflict, dramatic timeline, or the overall structure of the source work.
---

# Work Creation

Turn research context into a historically governed story foundation that can guide later screen adaptation, not a historical-event summary or a premature Script. Establish scope and historical causality before selecting a protagonist or dramatic structure. The required order is:

```text
Research → Historical Scope → Historical Spine → Historical Actor Hierarchy
→ Narrative Authority → Protagonist → Story Architecture → Structure Estimate
```

Later steps may compress and present earlier facts but may not rewrite them. Viewpoint can move downward; historical causality cannot be reassigned downward.

For complete screenplay incubation, this literary foundation is the historical/story stage of [Cinematic Screenplay Incubation](../cinematic-screenplay-incubation/SKILL.md). Reuse its compact Dramatic Bible when supplied; preserve this standalone entrypoint and its formal write gates. A local dialogue problem never requires regenerating the whole Work.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Work or revises an existing one, the requested scope and outcome, and the type, audience, scale, short-form intent, tone, period, and explicit user constraints. Make conservative working assumptions for non-critical omissions and record them in the internal plan; contradictory critical constraints block progress. Do not treat a title, event name, chronology, or famous person as sufficient creative intent.

### 2. Gather Context

Assess context sufficiency before planning. Continue when creative intent, format constraints, and adequate research context are supplied. When a stable `workId` is known, use `work.get_work`; when only a title or natural-language identity is known, use `work.search_works` and judge candidates; use `work.list_works` only to enumerate the available structural scope. Use `context.build_context` only when an existing Work context is required and was not supplied.

For a consequential evidence-dependent choice, use adequate supplied evidence first and use `research.verify_claim` only for an unresolved claim. Preserve source-supported actor granularity: a collective, institution, office, or unnamed group must not become a named actor without evidence. If broader evidence is missing, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. Do not repeat research for facts already supported. If essential creative intent, evidence, or constraints remain missing or contradictory after available Tool use, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Work Planning](references/planning.md) and apply it. Create an internal Work plan in the required historical-first order. Define `historicalScope`; build an ordered `historicalSpine[]` whose beats contain at least `beatId`, `actor`, `event`, `causalEffect`, and `evidenceClass`; derive a lightweight `historicalActorHierarchy` and each actor's scope-relative Narrative Authority. Give every individual actor who may speak one unique, stable, Work-scoped `speakerKey` in that existing hierarchy; never create a parallel Scene-local speaker registry or require a visual Asset. Only then select the protagonist, story architecture, and coverage-derived `structureEstimate`. State inherited facts, forbidden changes, invention space, required downstream content, and unresolved questions. Keep the plan in Agent Run Context or temporary working state. Do not call `work.create_work` or `work.save_work` to store it.

### 4. Execute Draft

Execute the selected plan as a complete candidate formal Work state. Preserve historical actors, sequence, outcomes, and material causality. A protagonist with `SECONDARY` Narrative Authority is allowed only when the scope is correspondingly narrowed; never transfer a `PRIMARY` actor's decision or causal role to make the protagonist active. Political, military, social, and historical stakes may be concrete; unsupported personal stakes are forbidden. `internalNeed` and private relationship arcs are optional interpretive or performance material only and may not create events, require psychological growth, or carry the historical causal chain. Theme must emerge from the Historical Spine rather than cause new decisions. The result must independently tell Script adaptation what the story is, why it moves, how it culminates, what each architecture node maps to, and what must not drift. It must not be a few-line event summary, chronology dump, character list, placeholder, test content, scratchpad, Scene dialogue, or Shot detail. Do not persist a partial draft.

### 5. Review

Before any write, read [Work Review and Revision](references/review.md) and apply the entire domain rubric and all hard gates to the complete draft. Critical checks include `HISTORICAL_SPINE_COMPLETE`, `FACT_ATTRIBUTION_VALID`, `PROTAGONIST_SCOPE_ALIGNMENT`, `UNSUPPORTED_CAUSAL_PROMOTION_ABSENT`, `DRAMATIZATION_NON_CAUSAL`, `STORY_ARCHITECTURE_SPINE_ALIGNED`, `STRUCTURE_COVERS_SPINE`, and Work-scoped speaker identity uniqueness and stability. Apply the Dramatization Deletion Test to every important `DRAMATIZED_BUT_COMPATIBLE` event: if deleting it breaks the main historical causal chain, fail with `FAIL_UNSUPPORTED_CAUSAL_EVENT`. A historical summary, inert chronology, unsupported historical drift, unsupported causal promotion, or incomplete story foundation is a critical failure. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow the defect routing in [Work Review and Revision](references/review.md): Locally revise wording, isolated clarity, or minor consistency defects; Re-plan when scope, spine, attribution, Narrative Authority, protagonist alignment, architecture mapping, dramatization causality, or coverage fails. Never repair a scope mismatch by granting unsupported agency. Rewrite the draft when structural failures are pervasive. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist as a formal story foundation, all critical checks and hard gates pass, and no historical or continuity conflict remains. A mere event summary, theme label, character list, unsupported actor attribution, protagonist/scope mismatch, missing historical beat, architecture without spine mapping, or story without climax and ending cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Work `content`. Persist only the reviewed formal result.

Use `work.create_work` only for a genuinely new Work after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `work.save_work` immediately afterward unless a concrete revision has actually occurred. Use `work.save_work` only to revise an already persisted Work because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep title and optional description in the Stable Envelope; place reviewed `historicalScope`, `historicalSpine`, `historicalActorHierarchy` including stable `speakerKey` values for speaking individuals, `narrativeAuthority`, protagonist, premise/logline, evidence boundary, stakes, optional interpretive material, story architecture with spine mappings, ending, and `structureEstimate` in the open `content` object. The estimate records episodes, scenes, shots, and reasoning derived in the order `Historical Spine → Required Story Beats → Beat Compression → Scene Requirements → Scene Action / Information Density → Shot Estimate`; it is adjustable downstream, never a production quota. These are creative content, not a request for new persistence fields. Do not hide, duplicate, or rename envelope fields inside `content`, and never submit stringified JSON, scratchpad reasoning, or raw Tool results. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not write Episode, Scene, dialogue, camera, or Shot design, and do not create a Script merely because the Work is complete.
