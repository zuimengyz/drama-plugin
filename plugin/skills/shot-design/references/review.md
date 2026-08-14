# Shot Review and Revision

Apply this rubric to the complete coverage group before persisting any Shot. Keep evaluation binary and simple: every listed row is critical because a failure can break Scene meaning, continuity, or production; one unresolved failure means Review FAIL for the group.

## Domain rubric

| Check | PASS evidence | FAIL signal |
|---|---|---|
| Scene fidelity | Coverage expresses the approved conflict/action/turn without redesigning it. | Camera choices mask or alter the Scene. |
| Coverage strategy | One coherent visual approach identifies necessary observations and reveals. | Shots are listed before a strategy or split by sentence. |
| Narrative purpose | Every retained Shot adds visual, narrative, emotional, performance, or continuity value. | A Shot has no distinct reason to exist. |
| Subject/action/blocking | Visible subject, executable action, and motivated spatial behavior are explicit. | Only a camera label or abstract meaning is supplied. |
| Framing/angle/movement/composition | Camera language serves information, performance, space, emotion, or action. | Size changes and movement are ornamental or formulaic. |
| Dialogue/reaction coverage | Coverage follows power, reaction, concealment, and relationship rather than speakers mechanically. | Every line receives its speaker's close-up; reactions are neglected. |
| Rhythm | Duration/cutting serves Scene, performance, information, and action. | All Shots are arbitrarily short or held without purpose. |
| Spatial continuity | Axis, screen direction, eyeline, relative positions, movement, and geography remain legible. | Unintended crossings or jumps confuse space. |
| Action continuity | Entry/exit action, direction, phase, hands, objects, and positions match. | Props disappear or action jumps without cause. |
| Performance continuity | Emotion, energy, attention, orientation, and intention progress causally. | Performance state changes between Shots without a Scene beat. |
| Asset/costume/prop continuity | Stable identity, wardrobe, objects, and environment remain consistent. | Visual references drift without story cause. |
| Temporal continuity | Time, light, weather, elapsed action, and ongoing motion are coherent. | Continuous action contains unexplained temporal change. |
| Generation feasibility | Character count, action, space, movement, references, and transitions are executable. | One Shot contains incompatible or excessive simultaneous demands. |
| Coverage economy | The group is minimal yet sufficient and covers the Scene turn. | Coverage explodes, repeats, or omits a necessary performance/action. |
| Downstream production readiness | Formal descriptions support provider-agnostic still/frame/video decisions. | Production must invent subject, spatial logic, continuity, or transitions. |

## Reject common anti-patterns

- **One-Line-One-Shot:** map every sentence or dialogue line to a new Shot.
- **Coverage Explosion / No Narrative Purpose:** create redundant views without distinct function.
- **Random Shot Size / Camera Ornament:** vary size or movement without dramatic reason.
- **Continuity Break:** lose axis, eyeline, direction, action phase, position, or time.
- **Reaction Neglect:** show only speakers and miss more important listeners or relationship states.
- **Asset Drift:** change identity, costume, prop, or environment without cause.
- **Unproducible Shot:** combine excessive characters, actions, movement, space changes, and interactions.
- **Premature Provider Detail:** encode workflow nodes, model settings, or provider parameters in Shot design.

## Revision and persist gate

Use local revision for one framing, angle, movement, duration, composition, wording, or minor continuity defect. Re-plan the Shot group when strategy, economy, axis/spatial logic, Scene-turn coverage, feasibility, or production readiness fails. Label missing Scene action/conflict/state change as an upstream Scene issue.

After every revision or re-plan, apply the full group rubric again. Allow `shot.create_shot` or `shot.save_shot` only when the entire group passes; then persist each reviewed formal Shot state. Keep alternatives, reasoning, findings, and revision notes temporary.
