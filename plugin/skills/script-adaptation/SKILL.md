---
name: script-adaptation
description: Adapt a historical-drama Work into a screen Script. Use when designing the audiovisual dramatic structure, main and secondary lines, character arcs, pacing, escalation, climax, or short-form series shape.
---

# Script Adaptation

Preserve the Work's dramatic truth while translating it into screen action. Define the main line, necessary secondary lines, character arcs, pacing, escalation, climax, and short-form structure. Prefer observable action over explanatory prose and keep continuity with the current Work.

Read only the Work and existing Script state needed for the decision. Use `work.get_work` when a stable `workId` is known. Use `script.get_script` for a known `scriptId`; otherwise use `script.list_scripts` under the known Work and select by structured fields. Use `script.create_script` only when a new adaptation is required, after producing the complete initial formal state needed by this Skill. A successful create is the normal first write and returns the stable ID; do not call `script.save_script` immediately afterward unless a concrete revision has actually occurred. Use `script.save_script` only to revise an already persisted Script because of a specific user request, discovered error, upstream change, or necessary addition to its formal state. Use `research.verify_claim` only when the adaptation depends on an unresolved historical claim.

Organize persistence as **Stable Envelope + Domain Content**. Keep the parent Work ID and Script title in the create envelope; use the stable Script ID and title when saving a revision. Put the confirmed audiovisual structure, lines, arcs, pacing, escalation, climax, and other formal adaptation facts in the `content` JSON object. Do not move the parent Work ID during save or hide, duplicate, or rename envelope fields inside `content`. Treat the Tool catalog as the sole machine-schema source. Submit `script.save_script` as a full replacement formal state, never as a patch, scratchpad, stringified JSON, or routine follow-up to create.

Use `context.build_context` only when required Work or Script context was not supplied, and use `context.refresh_context` only after a state change makes it stale. Do not create Episodes or call another Skill; return the Script result so the Agent can decide what follows.
