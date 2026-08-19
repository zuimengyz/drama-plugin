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

## 3. Give every Shot a narrative purpose

Assign one or more concrete functions: establish space/power, reveal information, capture a decision or reaction, emphasize threat, create information disparity, preserve action continuity, or express relationship change. Delete or merge a Shot with no new visual, narrative, emotional, performance, or continuity function.

## 4. Define subject, action, and blocking

Specify who/what the audience observes, what visibly happens, and how spatial behavior expresses goals and relationships. Use approach, retreat, central occupation, blocked exit, avoided eyeline, or movement around another figure only when motivated; avoid excessive choreography.

## 5. Motivate framing and camera

Choose wide/medium/close/detail or another appropriate size by required information, performance, spatial relation, emotion, and action. Do not mechanically cycle sizes.

Choose camera height/angle by context, blocking, editing, performance, spatial clarity, and subjective experience; reject simplistic “low equals powerful” formulas.

Move the camera only to follow action, reveal information, change relationship, increase pressure, or shift attention. Prefer stillness when it completes the purpose.

Compose for subject priority, screen space, depth, relationship, negative space, visual obstacle, and environment information. Let composition serve the Scene rather than decorate it.

## 6. Design dialogue coverage and rhythm

Do not alternate speaker close-ups automatically. Decide whose power, reaction, concealment, or relationship is most important; sometimes observe the listener while another speaks, preserve a two-shot, or withhold a reaction.

Read exact text only from the parent Scene's canonical `spokenContent`. Bind a retained Shot through canonical `spokenContentBindings` with `spokenContentId` plus `ON_SCREEN_SPEAKER`, `REACTION`, `OFF_SCREEN`, or `VOICE_OVER`; never copy the body or add audio timing. The same item may span speaker and reaction coverage while remaining one source item.

Let Shot duration and cutting serve Scene, performance, information, and action rhythm. Persist positive integer `plannedDurationMs`; prose rhythm may supplement but cannot replace it. For a standalone Shot, distinct bound item estimates must fit its planned duration. For continuous multi-Shot coverage, deduplicate shared item IDs and compare their estimates with the total group duration, then reserve playable room for action, reaction, and silence. Short form does not require every Shot to be short; hold on performance, reaction, silence, or tension only when narratively useful. Apply the [Dialogue Layer content convention](../../../docs/dialogue-layer-content-convention.md).

## 7. Preserve spatial continuity

Track the 180-degree axis, screen direction, eyeline, relative position, movement direction, and environment geography. Crossing the axis is allowed only with an intentional narrative/visual reason and a design that prevents unintended confusion.

## 8. Preserve action and performance continuity

For continuous action, track entry action, movement direction, hand/object state, character position, action phase, and exit action. Across Shots, preserve emotion, energy, attention, body orientation, and current intention unless the Scene supplies a cause for change.

## 9. Preserve visual and temporal references

When stable references exist and matter, verify character identity, costume, prop state, environment, and important visual anchors. Read stable Asset or Media references only for continuity; do not create or resolve them.

Track time of day, lighting direction, weather, elapsed time, and ongoing action. Do not introduce an unexplained temporal or lighting jump inside a continuous Scene.

## 10. Define narrative and visual states

For every Shot, state `Narrative Input State`, `Required Transition`, and `Narrative Output State`, plus concise visual entry/exit state. Not every Shot needs a major story change, but adjacent output/input states must match and the group must represent every indispensable Scene transition. Do not jump from order to distant consequence when mobilization, travel, arrival, or confrontation is narratively required.

## 11. Apply generation feasibility and complexity gates

Ensure character count, actions, spatial relations, camera movement, prop interaction, stable references, environment, and entry/exit states can be described and executed coherently. A Shot overloaded with multiple complex actions, rapid spatial changes, elaborate movement, many characters, and prop interactions should be split, simplified, or covered differently.

Remain provider-agnostic. Supply enough formal information for downstream production to judge a still image, start/end frame pair, or continuous video without choosing a provider or model parameter here.

## 12. Complete the coverage draft contract

The plan must support a minimal complete coverage group in which every Shot states narrative purpose, subject/action/blocking, motivated framing/angle/movement/composition, dialogue/reaction role, rhythm/duration, entry/exit state, continuity obligations, stable references where relevant, and feasibility.

If production must invent the subject/action, spatial logic, transitions, or Scene-turn coverage, the Shot plan is incomplete.
