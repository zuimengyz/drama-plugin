---
name: script-adaptation
description: Adapt a historical-drama Work into a screen Script. Use when designing the audiovisual dramatic structure, main and secondary lines, character arcs, pacing, escalation, climax, or short-form series shape.
---

# Script Adaptation

Convert an approved Work into a screen-adaptable formal Script state that can govern later Episode development. Inherit its Historical Scope, Spine, actor attribution, Narrative Authority, protagonist alignment, architecture mappings, and evidence boundary while designing playable progression and coverage; do not redesign the Work or prematurely write Scene/Shot detail.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Script or revises an existing one, the target Work, requested adaptation scope and outcome, and explicit format, episode count or duration, audience, tone, or continuity constraints. If the request actually changes the approved protagonist, premise, historical boundary, major ending, or other Work foundation, identify the upstream issue instead of silently repairing it in Script.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the relevant Work and adaptation constraints are supplied. Use `work.get_work` for a known `workId`; use `script.get_script` for a known `scriptId`; otherwise use `script.list_scripts` under the known Work and judge the structured candidates. Use `context.build_context` only when required Work or existing Script context was not supplied.

Use the Work's approved evidence boundary and supplied research context first. Use `research.verify_claim` only for a consequential historical claim newly introduced or materially reinterpreted by the adaptation; do not repeat research for facts already approved in Work. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If the governing Work, essential constraints, or consequential evidence cannot be obtained or conflict, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Script Planning](references/planning.md) and apply it. Create an internal adaptation contract that records the Work Historical Scope, ordered Spine, actor authority and attribution, protagonist alignment, architecture-to-spine mappings, premise, supported stakes, thematic question, historical boundary, ending, format, audience, and tone. Plan a causal main line that covers every required spine beat, only necessary secondary lines, information reveal, flexible episode architecture, short-form pacing, climax/payoff, screenability, and dialogue strategy. Optional interpretive arcs remain non-causal. Resolve open structural questions before drafting. Keep the plan in Agent Run Context or temporary working state. Do not call `script.create_script` or `script.save_script` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Script state. Translate approved history into observable action, behavior, dialogue, visual information, discovery, choice, reaction, and consequence. Make each structural segment and proposed Episode unit declare required spine beats and change story state; do not assign a collective or primary actor's causal act to the protagonist. Episode counts remain adjustable when coverage Review finds a missing or overloaded transition. The result must let Episode development understand the whole-series drive, progression, episode jobs, turns, climax, ending, historical constraints, and required beat coverage without reinventing them. It must not be a plot summary, event list, mechanical episode split, placeholder, test content, scratchpad, detailed Scene script, or camera plan. Do not persist a partial draft.

### 5. Review

Before any write, read [Script Review and Revision](references/review.md) and apply the entire domain rubric to the complete draft. Critical checks cover Work fidelity, Historical Spine coverage, fact attribution, protagonist/scope alignment, dramatization non-causality, main and secondary lines, causality and escalation, information reveal, coverage-derived episode architecture, pacing, screenability, dialogue, climax/payoff, ending fidelity, and downstream readiness. A plot summary, event list, mechanical episode split, unfilmable interior prose, or material Work drift is a critical failure. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow the defect routing in [Script Review and Revision](references/review.md): Locally revise dialogue, isolated beats, limited exposition, a small ordering problem, or minor continuity; Re-plan structurally when the main line, motivation, arc, conflict escalation, episode architecture, climax/payoff, or Work fidelity fails. If the defect originates in Work, mark it as an upstream Work issue rather than silently changing the foundation. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan/adaptation contract and complete draft exist as a screen-adaptable formal Script state, all critical checks in the Script rubric pass, and no Work, historical, or continuity conflict remains. A plot summary, event list, few-line episode outline, passive main line, missing arc or escalation, absent climax, unworkable episode architecture, unfilmable prose, or material Work drift cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Script `content`. Persist only the reviewed formal result.

Use `script.create_script` only for a genuinely new adaptation after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `script.save_script` immediately afterward unless a concrete revision has actually occurred. Use `script.save_script` only to revise an already persisted Script because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Work ID and Script title in the create envelope; use the stable Script ID and title for a revision. Put the reviewed adaptation contract, required historical beat coverage, main/secondary lines, optional non-causal interpretive progression, escalation, information reveal, flexible episode architecture, pacing, climax, ending, screenability, and other formal adaptation facts in the open `content` object. These are creative content, not a request for new persistence fields. Do not move the parent Work ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Script may plan Episode architecture, but do not create Episode entities, write detailed Scene dialogue/action, design cameras, or call another Skill automatically.
