# Professional Shot Planning

Use this method during the Shot `Plan` stage. Plan the complete coverage group before individual Shots. Express the approved Scene; do not repair its conflict, generate media, or encode provider-specific workflows.

## 1. Inherit the Scene contract

Record the Scene's required historical beats, Narrative Input State, Required Transition, Narrative Output State, purpose/action/turn, place/time, spatial layout, blocking, historical boundary, references, and constraints.

If the Scene lacks playable conflict, action, or state change, label an upstream Scene issue. Camera technique cannot create missing drama.

## 2. Choose the coverage strategy

State what the camera must primarily express: a power shift, isolation, discovery, escalating action, relationship distance, concealed information, or another approved Scene change.

Before listing Shots, decide:

- which spatial relations must be established;
- which performance/action moments must be seen;
- which information or reactions should be revealed, delayed, or withheld;
- which actions require continuity coverage;
- which observations are sufficient to express the Scene turn.

Prefer the smallest coherent set. Do not split every sentence or dialogue line.

### When this group opens the work

An opening redesign is first a Film/Screenplay decision. Apply the Director's
[film-opening authorship](../../director/SKILL.md#film-opening-authorship) before
coverage; do not treat the currently rendered shot as a required opening. Carry
the selected entry event, spectator relationship and next encounter into this group.
If only a local shot has been improved, report that scope instead of claiming a
redesigned film opening. Reject a default safe sequence justified only by existing
assets or easy generation; choose coverage for the selected dramatic experience.

Apply after the complete original screenplay and selection, not as a condition for
writing V1. Inherit the opening perception and purpose from the selected scene;
ask what entering here lets the audience experience, and what an earlier or later
entry would gain or lose. Return a needed narrative change to Host/Screenplay and
Director rather than inventing a prologue in coverage or compilation.

Coordinate the first effective image and sound: what does each make perceptible,
whose attention do we share, and what remains unlocated or unexplained? They may
coincide or arrive separately. With Sound, distinguish a withheld layer from an
absent listening world; narration, music, silence and direct action are choices,
not prescribed opening devices.

Read the opening group through its handoff into the first scene's event. Track how
discovery, a person's attention or response changes what the audience expects.
Keep setup when it prepares or changes that encounter, rather than merely delaying
it. With Performance and Editorial, hold while listening, tension or a sound/image
relation develops; omit an interval when its process adds nothing necessary,
preserving the causal and perceptual link. Neither novelty in every shot nor a
fixed duration or shot count is required.

Express the relation in existing purpose, requiredTransition, entry/exit and
editingRelation, with concrete Camera, Sound, Performance and Editorial originals.
Keep only current executable facts in the video request; titles and measured
picture/sound edits go to Finishing. A technical continuation inherits the ongoing
state, not another introduction. No separate opening plan or copied theory is
needed downstream.

### Rhythm preference and usable duration

Apply the current project's explicit rhythm preference to attention. A supplied
6:4 preference favors effective story progression while preserving character,
relation and resonance; do not impose that preference on unrelated projects. This is not a
ratio of seconds and does not slow emotional action or accelerate speech. Use
selection, overlap, ellipsis and motivated cuts to change pace. Keep a hold when
its observed picture/sound relation earns the time.

Name the intended editorial use separately from generation length. When a clip
must be longer than the chosen cut, continue the same plausible task as handles;
do not lengthen the useful action or impose an idle ending. In a revision, scope
prior stroke counts, camera locks and end holds to their original shot before
choosing whether to retain them. Recompile the current originals and inspect a
continuous temporary AV sequence; a stable motion curve alone cannot verify rhythm.

### Reconcile the complete scene before precision

Use [scene collaboration](../../director/references/scene-collaboration.md).
Editorial participates on provisional coverage, before formal Shot records exist.
Read the current ordered scene together, including the receiver of a changed
exit. Preserve one selected revision of the scene solution across departments;
do not join a new camera solution to an old action/cut solution. A common scene
packet supplies context, while only this shot's selected execution facts enter
its Prompt. Unresolved disagreement returns to the Host, not to text concatenation.

## 3. Give every Shot a narrative purpose

Assign one or more concrete functions: establish space/power, reveal information, capture a decision or reaction, emphasize threat, create information disparity, preserve action continuity, or express relationship change. Delete or merge a Shot with no new visual, narrative, emotional, performance, or continuity function.

## 4. Bind subject, action, and blocking

Specify who/what the audience observes and bind what visibly happens to approved Action and Blocking. Use approach, retreat, central occupation, blocked exit, avoided eyeline, or movement around another figure only when motivated; avoid excessive choreography.

## 5. Bind approved camera choices

Choose the information progression with Camera: space-to-detail may reveal a cause,
detail-to-space may reframe its meaning; holding a two-shot can preserve a relation.
Compare what wide/medium/close coverage reveals and withholds. No obligatory
establishing view or wide-medium-close cycle follows from these options.

Check Camera height/angle against context, blocking, editing, performance, spatial clarity, and subjective experience; reject simplistic “low equals powerful” formulas.

Bind only approved camera movement. Missing or conflicting motivation returns to Cinematography; do not invent a movement to fill coverage.

Verify the Camera composition preserves subject priority, screen space, depth, relationship, negative space and environment information. Request revision from Cinematography if coverage loses required meaning.

## 6. Design dialogue coverage and rhythm

Do not alternate speaker close-ups automatically. Decide whose power, reaction, concealment, or relationship is most important; sometimes observe the listener while another speaks, preserve a two-shot, or withhold a reaction.

Read exact text only from the parent Scene's canonical `spokenContent`. Bind a retained Shot through canonical `spokenContentBindings` with `spokenContentId` plus `ON_SCREEN_SPEAKER`, `REACTION`, `OFF_SCREEN`, or `VOICE_OVER`; never copy the body or add audio timing. The same item may span speaker and reaction coverage while remaining one source item.

Consume Editorial’s cut/hold intent so planned Shot duration serves Scene, performance, information and action rhythm. Persist positive integer `plannedDurationMs`; prose rhythm may supplement but cannot replace it. For a standalone Shot, distinct bound item estimates must fit its planned duration. For continuous multi-Shot coverage, deduplicate shared item IDs and compare their estimates with the total group duration, then reserve playable room for action, reaction, and silence. Short form does not require every Shot to be short; hold on performance, reaction, silence, or tension only when narratively useful. Apply the [Dialogue Layer content convention](../../../docs/dialogue-layer-content-convention.md).

## 7. Preserve spatial continuity

Compare adjacent views against one layout: axis, real eyeline target, facing,
screen direction and travel vector. A motivated axis crossing needs an audience
reorientation, not a mirrored set. Multi-angle references preserve the same pose
and occupancy unless an intervening action changes them; unseen geometry remains
an assumption. Request a plan or alternate view only when it resolves uncertainty.

## 8. Preserve action and performance continuity

For each receiver compare predecessor exit with entry: position, facing, eyeline,
motion, supporting hand/object state, camera endpoint and unfinished speech/task.
A match-on-action cut carries the action phase. A graphic match may connect
different times or places without preserving the same physical state. Bind the
approved Editorial relation: for an ellipsis, distinguish the supported offscreen
change from what remains unknown rather than inventing the missing action.
Preserve emotion, attention and energy unless the Scene supplies a cause.

Within a take, reconcile Action's ordered/parallel events, Performance's receiving
opportunities, Voice's phrase entries and Editorial's holds/end condition. Use
estimated local windows only where useful, with one shared reading of overlap.
The technical clip boundary is neither a film cut nor an instruction to restart.
Do not split a gesture into shots or invent repeated work to fill duration. Keep
execution details in the current department leaves; Shot binds their intention
and entry/exit, not a copied timeline or new timing fields.

## 9. Preserve visual and temporal references

When stable references exist and matter, verify character identity, costume, prop state, environment, and important visual anchors. Read stable Asset or Media references only for continuity; do not create or resolve them.

Track time of day, lighting direction, weather, elapsed time, and ongoing action. Do not introduce an unexplained temporal or lighting jump inside a continuous Scene.

## 10. Define narrative and visual states

For every Shot, state `Narrative Input State`, `Required Transition`, and `Narrative Output State`, plus concise visual entry/exit state. Not every Shot needs a major story change, but adjacent output/input states must match and the group must represent every indispensable Scene transition. Do not jump from order to distant consequence when mobilization, travel, arrival, or confrontation is narratively required.

## 11. Apply generation feasibility and complexity gates

Ensure character count, actions, spatial relations, camera movement, prop interaction, stable references, environment, and entry/exit states can be described and executed coherently. A Shot overloaded with multiple complex actions, rapid spatial changes, elaborate movement, many characters, and prop interactions should be split, simplified, or covered differently.

Remain provider-agnostic. Supply enough formal information for downstream production to judge a still image, start/end frame pair, or continuous video without choosing a provider or model parameter here.

## 12. Complete the coverage draft contract

The plan must support a minimal complete coverage group in which every Shot states narrative purpose, subject/action and current Blocking/Camera refs, dialogue/reaction role, rhythm/duration, entry/exit state, continuity obligations, stable references where relevant, and feasibility.

If production must invent the subject/action, spatial logic, transitions, or Scene-turn coverage, the Shot plan is incomplete.
