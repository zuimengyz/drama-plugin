# Shot Review and Revision

Apply this rubric to the complete coverage group before persisting any Shot. Keep evaluation binary and simple: every listed row is critical because a failure can break Scene meaning, continuity, or production; one unresolved failure means Review FAIL for the group.

## Domain rubric

| Check | PASS evidence | FAIL signal |
|---|---|---|
| Scene fidelity | Coverage expresses the approved conflict/action/turn without redesigning it. | Camera choices mask or alter the Scene. |
| Historical beat coverage | Coverage represents every historical/story beat assigned to the Scene. | A required beat disappears between planned Shots. |
| Narrative input/output state | Every Shot output supports the next Shot input and Scene boundaries match. | Story state changes between Shots without representation. |
| Required transition | Indispensable action, movement, decision, or consequence is shown or validly compressed. | A major transition is skipped. |
| Coverage strategy | One coherent visual approach identifies necessary observations and reveals. | Shots are listed before a strategy or split by sentence. |
| Narrative purpose | Every retained Shot adds visual, narrative, emotional, performance, or continuity value. | A Shot has no distinct reason to exist. |
| Subject/action/blocking | Visible subject, executable action, and motivated spatial behavior are explicit. | Only a camera label or abstract meaning is supplied. |
| Framing/angle/movement/composition | Camera language serves information, performance, space, emotion, or action. | Size changes and movement are ornamental or formulaic. |
| Dialogue/reaction coverage | Coverage follows power, reaction, concealment, and relationship rather than speakers mechanically. | Every line receives its speaker's close-up; reactions are neglected. |
| Rhythm | Duration/cutting serves Scene, performance, information, and action. | All Shots are arbitrarily short or held without purpose. |
| Spoken binding | Every binding resolves one parent-Scene item and states `ON_SCREEN_SPEAKER`, `REACTION`, `OFF_SCREEN`, or `VOICE_OVER`; shared coverage keeps one source item. | A binding is dangling/ambiguous, duplicates an item as new dialogue, or confuses reaction coverage with a second audio item. |
| Spoken source integrity | Shot content contains binding identity only and preserves the reviewed Scene text, provenance, performance intent, and `mustKeep` decision. | Shot copies, rewrites, deletes, or adds spoken text, or stores audio/subtitle timing. |
| Numeric duration feasibility | Every Shot has positive integer `plannedDurationMs`; distinct spoken estimates fit the Shot or deduplicated contiguous coverage group with playable room. | Duration is prose/non-positive, spoken load exceeds coverage, or production must solve the conflict later. |
| Scene state continuity | Narrative, spatial, temporal, force, knowledge, and danger state remains legible across the group. | The Scene arrives at an unexplained state. |
| Spatial continuity | Axis, screen direction, eyeline, relative positions, movement, and geography remain legible. | Unintended crossings or jumps confuse space. |
| Shot action continuity | Entry/exit action, direction, phase, hands, objects, and positions match. | Props disappear or action jumps without cause. |
| Performance continuity | Emotion, energy, attention, orientation, and intention progress causally. | Performance state changes between Shots without a Scene beat. |
| Asset/costume/prop continuity | Stable identity, wardrobe, objects, and environment remain consistent. | Visual references drift without story cause. |
| Temporal continuity | Time, light, weather, elapsed action, and ongoing motion are coherent. | Continuous action contains unexplained temporal change. |
| Causal narrative continuity | Shot transitions preserve cause, response, and consequence. | A later state has no represented or inherited cause. |
| Full story arc | The complete planned Shot tree retains beginning, development, crisis, climax, and ending coverage. | Local coverage passes while the larger story remains incomplete. |
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

Report these gates separately: `CHARACTER_VISUAL_CONTINUITY`, `COSTUME_PERIOD_CONTINUITY`, `PROP_STATE_CONTINUITY`, `SHOT_ACTION_CONTINUITY`, `SCENE_STATE_CONTINUITY`, `CAUSAL_NARRATIVE_CONTINUITY`, `HISTORICAL_BEAT_COVERAGE`, `FULL_STORY_ARC`, and `DURATION_FEASIBILITY`. Any failed gate means group Review FAIL. If an adjacent narrative state or required transition fails, return `FAIL_NARRATIVE_TRANSITION`; visual consistency does not override it.

For `DURATION_FEASIBILITY`, deduplicate one item shared across a contiguous coverage group. Fail when distinct bound spoken estimates do not fit the Shot/group or when arithmetic fit leaves no playable action, reaction, or silence. Resolve this before physical production; no Provider may rewrite the Scene source.

Use local revision for one framing, angle, movement, duration, composition, wording, or minor continuity defect. Re-plan the Shot group when strategy, economy, axis/spatial logic, Scene-turn coverage, feasibility, or production readiness fails. Label missing Scene action/conflict/state change as an upstream Scene issue.

After every revision or re-plan, apply the full group rubric again. Allow `shot.create_shot` or `shot.save_shot` only when the entire group passes; then persist each reviewed formal Shot state. Keep alternatives, reasoning, findings, and revision notes temporary.
