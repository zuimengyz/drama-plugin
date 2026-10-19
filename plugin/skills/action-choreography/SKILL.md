---
name: action-choreography
description: Specify causal body and object mechanics before a complex shot is produced. Use for Action Bible authoring and review; no media generation.
---

# Action Choreography

## Role and authority

Specify causal body and object mechanics before a complex shot is produced.

Own: Contact, grip, load, support, balance and ordered physical action phases.

Read [professional department architecture](../../docs/professional-departments.md) for the registry, Bible envelope, source/approval rules and Host handoff. Author only this department’s records; references never transfer ownership. Mark each record MIGRATED_FROM_R1 or NEW_PROFESSIONAL_ELABORATION when migrating a locked baseline.

## Inputs and dependencies

Approved action outcome; Blocking; Performance intent; Prop and Animal interaction constraints.

## Professional decisions

Start from the character's current task, its target and resistance, the approved
result, and what the audience needs to read. Choose an action scale and rhythm
that fit ability, urgency, load and relationship. Literary restraint does not set
a universal speed or amplitude; skilled work may be brisk and economical.

Resolve the relations that make this action possible:

- **Support and force:** where weight rests, what initiates or resists movement,
  and how momentum is absorbed or carried into the next action. A light precise
  task may be hand-led; a load may recruit legs and trunk. Choose the sequence
  from the task rather than prescribing feet → hips → shoulders for everyone.
- **Contact and freedom:** identify the relevant surfaces and when each relation
  begins, changes or ends. A grip can fix the hand in tool space while the tool
  slides on the work; a sole can pivot about its loaded region. Name the motion
  that remains possible, not merely “keep contact.”
- **Transfer and release:** for a controlled handover or set-down, locate the
  receiving support and an accessible approach before unloading. For a throw,
  drop or jump, release creates flight; specify its consequence and subsequent
  catch/landing only when part of the approved action. Inspect intermediate
  access and reach when geometry makes them uncertain.
- **Coordination:** describe the principal trajectory and how other limbs or
  participants support, accommodate or oppose it. Distinguish simultaneous effort
  from a useful delay; coordinated contact may need synchronized motion. A fixed
  grip does not freeze shoulders, elbows, trunk or all relative transforms.
- **Rhythm and result:** locate meaningful changes in effort, speed, attention or
  material state. Repetition, a held task or continued motion may each be right.
  Choose a recovery or pause because of the action, not to complete a standard
  preparation/contact/impact/recovery template or fill an allotted duration.

Use a relevant observed reference when the unresolved question is technique,
weight transfer or timing. Record the observed relation and the limits of its
transfer to this character, prop and shot. A still establishes shape or a pose,
not a motion trajectory; a plausible proxy trajectory does not establish acting.
Keep uncertain dimensions, loads and material responses explicit as hypotheses.

Describe the selected causal action in readable prose: what the person does,
what it changes and how that enables the next state. Keep short restrictions only
where they resolve a consequential ambiguity in this shot. One failed render is
evidence about that execution, not a rule for every actor or future shot.

For method selection and source limitations, see
[movement research and external execution](references/movement-methods.md).

## Outputs

Produce a versioned `Action Bible` with current source pins, department dependencies, scope, ownership, status and continuity references. Keep known decisions separate from unresolved requirements.

In the native handoff, an `actionPhases` row is an execution unit, not an actor or
mechanical substep. Its `action` carries the causal sequence, concurrent partner
expression and uninterrupted speech against one `entryState` and `observable`
end condition. Take expression from the participants' Beat originals; selecting
one primary Beat does not serialize their tasks. A reused Beat carries only
expression valid across its selected units; stage-local changes belong here.
Keep contact changes inside the current action, including intentional release.
A mechanical substep alone does not require a new psychological Beat or execution unit.

Use event-relative timing or estimated local windows where they clarify execution;
never turn each window into another row. Separate a required repeated stroke from
an idle loop by its material result or dramatic purpose. Do not invent work to
fill a clip. Current contact, support and visibility conditions belong in these
action leaves; `physicalStateConstraints` holds lasting invariants, not a second
recital of the sequence. A technical split inherits the actual release state,
without restarting preparation; a film cut needs Shot/Editorial's authored boundary.

## Forbidden authority

Do not change upstream historical evidence, approved story/relationships/dialogue or another department’s records. Do not encode provider/model/workflow controls in creative content, manufacture user approval, or call media generation.

## Quality gates

The visible result follows from the authored effort, support, contact or deliberate release. Check transitions and recovery against the character’s actual condition; separate an execution fault from an unresolved observation.

## Failure and escalation

Resolve missing placement or scale when it materially changes feasibility; otherwise state the working assumption. Proposed event changes go to Screenplay/Director. Diagnose whether a failed realization needs better reference, control or expression before adding more prompt restrictions.

## Source reads

Use supplied current originals first. For missing scoped context, read `work.get_work`, `scene.get_scene`, `script.get_script`, `episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`. These reads do not authorize source writes or production.

## Route-owned expression

Within the Director-selected route envelope, select the preparation, acceleration, contact, follow-through or environmental response this action actually needs. Continuous work and quiet attention need not acquire an impact structure. Preserve physical causality and canonical outcomes. A character action signature does not propagate to other actors. Read [expression route contract](../../docs/expression-route-contract.md) when using character or action expression profiles.

## Character Package ownership

Combine screenplay facts, Director intent and the packaged actionSignature. Do not decide the character movement identity anew or add event outcomes.

Use the unified read-only `CharacterRepository.resolve_character_package` contract in [Character External Driver](../../docs/character-external-driver.md). Pin characterPackageRef, characterPackageVersion and checksum. Never create or overwrite Character Core in this Skill. Missing or stale packages return to the driver; model memory and old chat are not assets. DESIGN_REVIEW access does not authorize casting or production.

## Character Embodiment ownership

Combine script action + Director intent + embodiment baseline + actionSignature. Do not invent movement identity or new action results.

Read [Embodiment contract](../../docs/character-embodiment.md). Use the unified read-only `characters.embodiment.embodiment_handoff` with exact ref/version/checksum and route. Never create or overwrite embodiment in downstream execution. Comparisons are reasoning-only; they do not enter the generation prompt.

## Still live-action professional knowledge

For opt-in STILL/LIVE_ACTION, project only the approved current body_mechanics or contact_constraints slice into existing action/contact facts. Ordered future phases and movement timing remain internal to this still consumer. Identity references cannot create an action. Support/load/contact comes from Action and Blocking; material response and conditional contact shadow remain Lighting/QA responsibilities.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.


## Actor-playable screenplay handoff (Screenplay R2)

Read [screenplay playability and exact dialogue](../../docs/screenplay-playability.md). Resolve causal mechanics for the approved playable action, preserving actor/target/negation/contact. Missing action meaning returns to its owner rather than being created for model convenience.
