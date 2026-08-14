---
name: episode-development
description: Develop or revise one historical short-drama Episode from a Script. Use when deciding the episode goal, opening hook, conflict progression, information gain, character change, ending hook, or cross-episode continuity.
---

# Episode Development

Give one Episode a clear dramatic job within its Script. Establish an opening hook, conflict progression, information gain, character change, and ending hook while preserving relevant cross-Episode continuity.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Episode or revises an existing one, the parent Script and episode number, the requested dramatic scope and outcome, and explicit length, continuity, historical, or user constraints. Do not treat mechanical Script slicing as an Episode goal.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the relevant Script state, episode position, and required continuity are supplied. Use `script.get_script` for the stable parent; use `episode.get_episode` for a known `episodeId`; otherwise use `episode.list_episodes` under the known Script, filtering by episode number or title and reading neighboring Episodes when continuity may change.

Use `context.build_context` only when required parent or existing Episode context was not supplied. Use adequate research context first and use `research.verify_claim` only when a consequential Episode decision depends on uncertain history. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If the parent Script, episode position, essential continuity, or consequential evidence cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Create an internal Episode plan stating its dramatic goal, Script facts and character states that must be inherited, constraints that cannot be violated, the intended entry-to-exit change, the opening hook/conflict progression/information gain/character change/ending hook required in the draft, and unresolved questions that must be settled first. Keep it in Agent Run Context or temporary working state. Do not call `episode.create_episode` or `episode.save_episode` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Episode state with one coherent dramatic job and meaningful progression. The draft must be detailed enough for Episode review and later Scene development; it must not be a mechanical slice, a few-line synopsis, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Review the complete draft before any write. Critical checks are: the Episode has one clear dramatic job, an effective opening hook, escalating conflict, information gain, character change, and an earned ending hook; entry and exit states are meaningfully different and continuous with relevant neighboring Episodes; and no material historical or Script continuity conflict is unresolved. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Locally revise a hook, isolated beat, completeness, wording, or minor continuity defect. Re-plan the current Episode when its dramatic job, progression, entry-to-exit change, ending hook, or relationship to the Script fails. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist, all critical checks pass, and no historical or continuity conflict remains. Plan, draft reasoning, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Episode `content`. Persist only the reviewed formal result.

Use `episode.create_episode` only for a genuinely new Episode after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `episode.save_episode` immediately afterward unless a concrete revision has actually occurred. Use `episode.save_episode` only to revise an already persisted Episode because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Script ID, episode number, and title in the create envelope; use the stable Episode ID, episode number, and title for a revision. Put the reviewed Episode job, hooks, progression, information gain, character change, entry/exit states, and other formal facts in `content`. Do not move the parent Script ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not decompose the Episode into Scenes automatically.
