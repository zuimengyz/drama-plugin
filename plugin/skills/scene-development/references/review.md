# Scene Review and Revision

Apply this rubric to the complete Scene draft before persistence. Keep evaluation binary and simple: every listed row is critical because each is required for a playable state-changing event; one unresolved failure means Review FAIL.

## Domain rubric

| Check | PASS evidence | FAIL signal |
|---|---|---|
| Episode fidelity | Purpose and exit state serve the approved Episode job/direction. | Scene silently redesigns or detours from the Episode. |
| Scene purpose | A specific action/result explains why this Scene exists. | Purpose only displays character, setting, theme, or background. |
| Entry state | Relevant knowledge, relationship, goal, danger, and power are usable. | The starting dramatic conditions are ambiguous. |
| Character objective | A center character pursues an immediate playable result. | Nobody wants anything specific now. |
| Opposing force | Present resistance can materially block the objective. | No obstacle acts, or “history” is only discussed. |
| Stakes | Failure has a concrete immediate consequence. | Success and failure are dramatically equivalent. |
| Tactics and beats | Resistance causes strategy, information, or power to change. | Positions repeat and tactics never adapt. |
| Conflict-in-action | Decision, action, resistance, and consequence happen now. | Talking heads discuss conflict happening elsewhere. |
| Dialogue/subtext | Speech serves objectives/tactics, interacts with action, and avoids shared-fact exposition. | Dialogue teaches history or directly states every intention. |
| Playable action | Interior meaning is externalized through performable behavior. | Abstract psychology or narration carries the Scene. |
| Turn | A consequential event changes what characters can do next. | No reversal, discovery, decision, or lost option occurs. |
| Meaningful state change | Knowledge, relationship, decision, danger, goal, power, commitment, or choice changes. | Before equals after in every material dimension. |
| Historical integrity | Action respects approved fact, uncertainty, and invention boundaries. | Convenience creates unsupported historical drift. |
| Scene necessity | Deletion materially damages Episode job, state, information, decision, or danger. | The Episode works almost unchanged without the Scene. |
| Continuity | Entry follows prior state and exit supports the next direction. | Character, knowledge, object, time, or motivation jumps without cause. |
| Downstream readiness | Shot design can cover approved action without inventing conflict or camera instructions already embedded. | Scene is unplayable, incomplete, or prematurely dictates Shots. |

## Apply the hard gates

**Before/After Gate:** if entry and exit are materially the same and no information, relationship, decision, danger, goal, power, commitment, or choice changes, Review FAIL.

**Delete Scene Test:** if removal causes negligible loss to the Episode job or state progression, delete, merge, or re-plan; Review FAIL.

## Reject common anti-patterns

- **Talking Heads / Exposition Scene:** characters stand and explain history or off-screen conflict.
- **No Objective / No Opposition:** nobody pursues a result or meets active resistance.
- **Repeated Position / No Tactic Change:** speakers repeat views after resistance.
- **No Turn / Static Relationship:** the dramatic state never changes.
- **Interior Summary:** unplayable psychology replaces behavior.
- **Decorative Scene:** deletion changes nothing material.
- **Premature Shot Design:** framing, camera, and coverage replace Scene action.

## Revision and persist gate

Use local revision for dialogue, one tactic/beat, action clarity, subtext, or minor continuity. Re-plan when purpose, objective, opposition, stakes, conflict-in-action, turn, state change, playability, necessity, or downstream readiness fails. Label a root Episode-design defect as an upstream Episode issue.

After every revision or re-plan, apply the full rubric and both gates again. Allow `scene.create_scene` or `scene.save_scene` only after every check passes. Keep alternatives, reasoning, findings, and revision notes temporary; persist only the approved playable state-changing dramatic Scene.
