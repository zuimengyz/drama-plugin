---
name: episode-development
description: Develop or revise one historical short-drama Episode from a Script. Use when deciding the episode goal, opening hook, conflict progression, information gain, character change, ending hook, or cross-episode continuity.
---

# Episode Development

Turn one approved part of a Script into a necessary dramatic unit with one clear dramatic job, a meaningful entry-to-exit state change, escalating conflict, an earned turn and ending, and continuity with the whole-series progression. Do not mechanically slice the Script or write detailed Scenes.

## Creative Lifecycle

### 1. Understand Goal

Clarify whether the request creates a new Episode or revises an existing one, the parent Script and episode number, the requested dramatic scope and outcome, and explicit length, continuity, historical, or user constraints. Identify what this Episode must change and why it must exist. Do not treat mechanical Script slicing or a plot-summary assignment as an Episode goal.

### 2. Gather Context

Assess context sufficiency before planning. Continue when the Script main line, relevant secondary line, character and relationship state, historical boundary, approved Episode Architecture, previous exit state, next structural destination, and episode position are supplied. Use `script.get_script` for the stable parent; use `episode.get_episode` for a known `episodeId`; otherwise use `episode.list_episodes` under the known Script, filtering by episode number or title and reading neighboring Episodes when continuity may change.

Use `context.build_context` only when required parent or existing Episode context was not supplied. Use adequate research context first and use `research.verify_claim` only when a consequential Episode decision depends on uncertain history. If broader evidence is required, formulate a focused research question and stop before planning or persistence so the Agent or Host can choose an existing research capability. If the parent Script, episode position, essential continuity, or consequential evidence cannot be obtained or conflicts, state the blocker and do not draft or persist.

### 3. Plan

Before drafting, read [Professional Episode Planning](references/planning.md) and apply it. Create an internal Episode plan that inherits the Script rather than redesigning it; state one sentence-level dramatic job, character objective, entry state, central obstacle, stakes, tactic/counteraction progression, higher cost, meaningful turn, exit state, earned ending, neighboring continuity, necessity evidence, Scene-development contract, and unresolved questions. Keep it in Agent Run Context or temporary working state. Do not call `episode.create_episode` or `episode.save_episode` to store it.

### 4. Execute Draft

Execute the plan as a complete candidate formal Episode state. Progress from objective through obstacle, tactic, counteraction, higher cost, and turn so at least one meaningful goal, knowledge, relationship, loyalty, danger, power, choice, commitment, public position, resource, or status changes by the exit. The draft must let Scene development understand what must happen without writing detailed Scene dialogue or Shots. It must not be a mechanical slice, recap, exposition container, few-line synopsis, placeholder, test content, or scratchpad. Do not persist a partial draft.

### 5. Review

Before any write, read [Episode Review and Revision](references/review.md) and apply the entire domain rubric and Delete Episode Test. Critical checks cover dramatic job, Script fidelity, entry/exit state, character objective, opening hook, conflict progression and escalation, meaningful turn, information gain, character and relationship change, earned ending hook/resolution, neighbor continuity, Episode necessity, short-form rhythm, and downstream readiness. A mechanical split, inert summary, repeated conflict, fake hook, or removable Episode is a critical failure. Mark Review PASS only when every critical check passes; otherwise mark Review FAIL.

### 6. Revise or Re-plan

On Review FAIL, do not persist. Follow [Episode Review and Revision](references/review.md): Locally revise a hook, isolated beat, pacing, wording, or minor continuity defect. Re-plan the current Episode when its dramatic job, Script fidelity, conflict progression, turn, entry-to-exit state change, ending logic, or necessity fails. If the root cause is the Script foundation or Episode Architecture, label an upstream Script issue instead of rewriting the whole series here. After any revision or re-plan, review the complete draft again. A fix never goes directly to persistence without Review Again and PASS.

### 7. Persist

No Review PASS means no create or save. Persist only when required context is sufficient, the plan and complete draft exist as a formal dramatic Episode state, all critical checks pass, and no historical or continuity conflict remains. A plot summary, mechanical split, Episode without a dramatic job, central conflict, turn, meaningful exit-state change, Script fidelity, or necessity cannot pass. Plan, draft reasoning, rejected alternatives, review notes, and revision notes remain Agent Run Context or temporary working state; do not put them in Episode `content`. Persist only the reviewed formal result.

Use `episode.create_episode` only for a genuinely new Episode after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `episode.save_episode` immediately afterward unless a concrete revision has actually occurred. Use `episode.save_episode` only to revise an already persisted Episode because of a specific request, discovered error, upstream change, or necessary addition.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Script ID, episode number, and title in the create envelope; use the stable Episode ID, episode number, and title for a revision. Put the reviewed dramatic job, objective, hooks, conflict progression, turn, information/character/relationship changes, entry/exit states, necessity, and other formal facts in the open `content` object. These are creative content, not new persistence fields. Do not move the parent Script ID or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit save as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create. Use `context.refresh_context` only after a write makes current context stale. Do not write detailed Scenes, create Scene entities, or automatically invoke another Skill.
