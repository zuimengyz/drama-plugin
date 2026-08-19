# Professional Scene Planning

Use this method during the Scene `Plan` stage. Plan a necessary, playable dramatic event inside the approved Episode; do not redesign the Episode or specify camera coverage.

## 1. Inherit the Episode contract

Record the Episode dramatic job, assigned `requiredSpineBeatIds`, actor attribution, historical boundary, previous Scene Narrative Output State, next intended Narrative Input State, and the transition this Scene must represent.

If the Episode offers no coherent job or state destination, label an upstream Episode issue instead of inventing a different Episode inside the Scene.

## 2. Define Narrative Input State, Required Transition, and Narrative Output State

State why the Scene must exist using a supported action and result. Name its input, required transition, and intended output across historical/story state, knowledge, relationship, decision, danger, goal, power, commitment, location, or available choice. “Show the relationship” or “discuss the danger” is not a sufficient purpose.

Require the input to follow the previous output. If an indispensable mobilization, travel, arrival, confrontation, decision, or consequence lies between them, represent it in this or another Scene; do not hide it in an unexplained jump.

## 3. Give a character a playable objective

Choose a center character and define an immediate, specific result they can pursue now. “Obtain the seal,” “make the minister publicly commit,” or “prevent the messenger from leaving” is more playable than “protect the realm.”

Define immediate stakes: lost trust, exposed secret, missed opportunity, forced position, political displacement, or inability to keep hiding. Stakes need not be life-or-death, but failure must matter now.

## 4. Build active opposition

Use another person's competing objective, institution, deadline, ritual/status rule, misinformation, secret, inner contradiction, physical condition, or risk that materially blocks the objective. Opposition must act in the present Scene; a distant war or general political danger is only context until it resists current action.

## 5. Plan tactics and beats

Plan behavior that adapts when resistance succeeds. A character may appeal, test, withhold, bargain, mislead, provoke, threaten, confess, retreat, or reframe, but do not treat these as a fixed menu.

Build beats around meaningful changes, not lines of dialogue:

```text
objective/tactic/information/power shifts
→ resistance changes
→ behavior changes
→ new consequence
```

Do not force a fixed beat count. Require a tactic change when the prior tactic clearly fails.

## 6. Design conflict-in-action and subtext

Make decision, action, resistance, and consequence occur now. Talking about a war, danger, or political conflict does not itself create Scene conflict.

Give each major speaker a current objective. Let dialogue perform a tactic and interact with action; avoid background both speakers know. Use refusal, interruption, evasion, silence, and differentiated voice when appropriate. Allow spoken meaning to differ from dramatic intention, especially under ritual, status, and political risk, without making dialogue obscure.

First decide whether the Scene needs spoken content at all. Pure environment, action, silence, reaction, battle, transition, or visually sufficient information may keep canonical `spokenContent` empty. If the Scene depends on a proposal, refusal, order, promise, revelation, or narration, a functional summary is insufficient: write reviewed exact text using the [Dialogue Layer content convention](../../../docs/dialogue-layer-content-convention.md). Resolve character `speakerKey` from the Work's existing actor/character structure; use a stable `narrator:` key for narration without creating a visual identity. Estimate every item as positive integer milliseconds before Shot planning.

Plan provenance as `DIRECT_QUOTE`, `ADAPTED`, `DRAMATIZED`, or `FUNCTIONAL`. A direct quote requires source reference, exact locator, matching excerpt, and matching spoken text. Preserve existing item IDs through wording or detail revision; only real addition, deletion, split, or merge changes affected identity.

## 7. Make action playable

Externalize important interior states through behavior, movement, interaction, object use, physical reaction, choice, silence, distance, and position. Avoid relying on “realizes,” “feels,” or abstract descriptions of the situation.

Define place/time only to the degree they create constraint, opportunity, atmosphere, or action. Do not design shot size, angle, camera movement, or coverage.

## 8. Earn the turn

Make the turn change knowledge, relationship, decision, danger, goal, power, commitment, or available choice so the Scene cannot simply return to its entry state. The turn may come from discovery, failed tactic, unexpected action, refusal, concession, reversal, or irreversible choice.

## 9. Prove necessity

Apply a planning-level Delete Scene Test. Identify what the Episode would lose in its job, character/relationship state, information, decision, danger, power, or goal progression. If the loss is negligible, delete, merge, or re-plan.

## 10. Complete the Scene draft contract

The plan must support a draft containing purpose, place/time, participants, entry state, objective, opposition, stakes, tactic/beat progression, conflict-in-action, dialogue/subtext function, playable action, turn, exit state, historical/neighbor continuity, and necessity evidence.

If Shot design must invent the Scene conflict, action, turn, or final state, the Scene plan is incomplete.
