# Professional Historical Work Planning

Use this method during the Work `Plan` stage. Keep comparisons and rejected options in temporary working state; persist only the selected formal story foundation after Review PASS.

## 1. Frame the creative brief and evidence boundary

Record type, audience, tone, period, scale, short-form intent, and explicit requirements. Sort consequential material into documented/supported, disputed/uncertain, and dramatic invention space. Preserve supported actor identity, sequence, outcome, and material causality; retain uncertainty where evidence is uncertain.

The Work designs a historical story foundation. It does not write detailed Episodes, Scenes, dialogue, or Shots.

## 2. Define Historical Scope first

Write a simple `historicalScope` statement answering which bounded war, campaign, battle, decision process, political event, group experience, or personal experience the Work actually tells. Do not use a fixed taxonomy. Scope must be narrow enough to cover coherently and broad enough to match the user's request.

Scope governs which facts belong in the story, whose actions carry the main causality, and which structure is required. Never select a protagonist and then expand or distort scope to justify that selection.

## 3. Build the Historical Spine

Build an ordered `historicalSpine[]` of the indispensable beats inside the scope. Every beat contains at least:

```text
beatId · actor · event · causalEffect · evidenceClass
```

Add a light source/evidence reference when available. Preserve chronological and causal order. Keep actor attribution at source-supported actor granularity: evidence about a collective, institution, office, or unnamed group does not support narrowing the action to a named person.

The spine is neither a complete chronology nor a list of photogenic moments. It is the minimum chain whose removal would make the event's major historical causality incomplete.

## 4. Derive Historical Actor Hierarchy and Narrative Authority

For each material actor, record lightweight scope-relative authority such as `PRIMARY`, `SECONDARY`, or `BACKGROUND`, plus a short justification tied to spine beats. Narrative Authority means how much of the selected event's core causality the actor actually initiates, controls, executes, or bears; it is not rank alone. Give each individual who may speak one unique, stable, Work-scoped `speakerKey` on this existing actor entry. Reuse it across Scenes; do not create Scene-local identity or make it depend on a visual Asset. Narration uses the reserved Work-scoped `narrator:` convention and is not a historical actor.

The same person may have different authority under a different scope. Never upgrade authority merely because an actor is younger, more visual, easier to identify with, or easier to give action.

## 5. Select protagonist and viewpoint from authority

Derive the protagonist only after Scope, Spine, and Narrative Authority.

- For a main battlefield, main decision, or main political process, choose a protagonist from actors with `PRIMARY` Narrative Authority.
- A `SECONDARY` or peripheral actor may be protagonist only when the narrative scope is explicitly narrowed to that actor's experience.
- Narrowing viewpoint does not transfer decisions or causal actions from higher-authority actors.

The governing rule is: **Viewpoint can move downward. Historical causality cannot be reassigned downward.** Compare viable protagonist/viewpoint options only within these constraints.

## 6. Design bounded dramatic material

Define a premise, external pursuit where evidence supports one, capable opposition, and political, military, social, historical, or moral stakes. Personal stakes require evidence or must be labeled compatible invention that does not explain the historical result.

`internalNeed`, a heroic agency arc, and private relationship arcs are not mandatory. If useful, treat internal tendency as interpretive/performance guidance only; it cannot create historical events or demand psychological growth. When private relationship evidence is thin, record `historicalRelationship`, allowed interaction, and evidence boundary instead of inventing trust, betrayal, or change.

Theme is downstream of history:

```text
Historical Spine → thematic question
```

Never use:

```text
theme → invented major decision → historical outcome
```

## 7. Compress the spine into Story Architecture

Use a flexible architecture such as starting state, disruption, escalation, reversal, crisis, climax, ending, and final state. Each major node must list the `spineBeatIds` it compresses or presents. Architecture may merge beats, compress time or people, change presentation order without changing causality, use montage, select a POV, and add compatible action/dialogue.

It may not invent a decisive event, turn the historical climax into a fictional hero's unsupported choice, or use an arc to explain why history occurred.

For every important `DRAMATIZED_BUT_COMPATIBLE` event, apply the planning-level Dramatization Deletion Test:

```text
delete dramatization → main Historical Spine causality still holds
```

If the chain fails, remove or re-plan the invention.

## 8. Estimate structure from coverage

Use this order:

```text
Historical Spine
→ Required Story Beats
→ Beat Compression
→ Scene Requirements
→ Scene Action / Information Density
→ Shot Estimate
```

Coverage First, Compression Second. Do not choose episode, Scene, or Shot counts before establishing spine coverage. `structureEstimate` may record episodes, scenes, shots, and reasoning, but it is adjustable downstream and never a fixed quota. A small-scale preference cannot delete an indispensable beat.

## 9. Complete the Work draft contract

The selected plan must support a draft that independently communicates:

- creative brief and evidence boundary;
- `historicalScope`, ordered `historicalSpine`, actor hierarchy, and Narrative Authority;
- protagonist selection and scope alignment;
- premise, supported pursuit/opposition/stakes, theme, and bounded optional interpretation;
- story architecture with spine mappings, climax, ending, and final state;
- coverage-derived `structureEstimate` and its reasoning.

If Script adaptation would need to invent historical causality, actor attribution, scope, protagonist qualification, indispensable beats, or the main architecture, the Work plan is incomplete.
