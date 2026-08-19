# Historical Work Review and Revision

Apply this rubric to the complete Work draft before persistence. Evaluation is binary: one unresolved critical failure means Review FAIL.

## Domain rubric

| Check | PASS evidence | FAIL signal |
|---|---|---|
| Story identity | A bounded historical dramatic proposition organizes the Work. | A chronology dump or disconnected event/character list stands in for a story. |
| Historical Scope | Scope is explicit and governs included causality, actors, and coverage. | Scope is absent, drifts to fit a protagonist, or differs from the claimed event. |
| Historical Spine | Ordered indispensable beats preserve the scope's main sequence and causality. | A required beat is absent or only photogenic fragments remain. |
| Fact attribution | Every consequential act remains at evidence-supported actor granularity. | A collective or institutional claim is narrowed to an unsupported named actor. |
| Actor hierarchy | Material actors have simple, scope-relative authority justified by spine participation. | Authority follows fame, rank, or dramatic convenience rather than causality. |
| Speaker identity | Every speaking individual has one unique stable Work-scoped `speakerKey`; narration remains separate and visual Asset identity is optional. | Keys collide or change across Scenes, a Scene-local registry duplicates actors, or dialogue is blocked by a missing visual Asset. |
| Protagonist/scope alignment | The protagonist has PRIMARY authority for broad event scope, or scope is narrowed for a secondary actor. | A supporting actor is promoted while broad scope and historical causality remain claimed. |
| Causal promotion | No actor receives unsupported judgment, decision, persuasion, or decisive action. | Protagonist agency depends on reassigned causality. |
| Opposition and stakes | Opposition is intelligible; stakes are historical/political/military/social or evidence-supported personal stakes. | Unsupported personal stakes or a flat villain are invented to force drama. |
| Interpretive material | Optional internal/relationship material stays non-causal and within evidence boundaries. | An invented need, trust, betrayal, or growth explains a historical outcome. |
| Theme | The thematic question emerges from existing spine beats and consequences. | Theme requires a new major historical decision or event. |
| Dramatic causality | Dramatic pressure and consequences present the supported historical chain. | Fiction replaces the cause of an actual outcome. |
| Dramatization deletion | Removing every important compatible invention leaves the main Historical Spine intact. | Deleting an invention breaks the explanation of history. |
| Story Architecture | Every major architecture node maps to one or more spine beats. | Climax, reversal, crisis, or ending has no spine basis or reallocates causality. |
| Structure coverage | Estimate follows beat coverage and includes all indispensable spine beats. | A preset episode/Scene/Shot quota deletes required history. |
| Historical integrity | Fact, uncertainty, and invention remain distinguishable. | Evidence class changes, outcome drifts, or uncertainty becomes fact. |
| Downstream readiness | Script can inherit scope, spine, authority, protagonist, mappings, ending, and structure reasoning. | Downstream must redesign the historical foundation. |

## Hard gates

All gates must pass:

- `HISTORICAL_SPINE_COMPLETE`
- `FACT_ATTRIBUTION_VALID`
- `PROTAGONIST_SCOPE_ALIGNMENT`
- `UNSUPPORTED_CAUSAL_PROMOTION_ABSENT`
- `DRAMATIZATION_NON_CAUSAL`
- `STORY_ARCHITECTURE_SPINE_ALIGNED`
- `STRUCTURE_COVERS_SPINE`

If the Dramatization Deletion Test fails, return `FAIL_UNSUPPORTED_CAUSAL_EVENT`. If actor granularity narrows without evidence, return `UNSUPPORTED_CAUSAL_PROMOTION` and Review FAIL.

## Reject common anti-patterns

- **Historical Summary / Chronology Dump:** dates replace dramatic presentation and state change.
- **Interesting Supporting Hero:** a visually convenient actor receives another actor's historical decisions.
- **Scope Inflation:** a personal experience claims to explain the whole event.
- **Unsupported Personal Arc:** invented need, betrayal, or growth creates historical causality.
- **Theme-First History:** a message causes invention of a decisive act.
- **Quota-First Compression:** episode, Scene, or Shot count is chosen before required beat coverage.
- **Visual Fragment Selection:** photogenic fragments omit the beginning, decisive process, climax, or ending.
- **Historical Drift:** key fact, outcome, actor, presence, sequence, or causality changes for convenience.

## Classify, revise, and persist

Use local revision only for wording, labeling, isolated mapping, or minor consistency defects. Re-plan the Work when scope, spine completeness, actor authority, protagonist alignment, attribution, architecture mapping, dramatization causality, climax, or coverage fails. Never repair a failure by increasing unsupported protagonist agency. Rewrite the full draft when connected structural failures are pervasive.

After every revision or re-plan, apply the entire rubric, all seven hard gates, and the Dramatization Deletion Test again. Allow `work.create_work` or `work.save_work` only after every check passes. Keep alternatives, reasoning, findings, and revision notes temporary; persist only the approved formal historical story foundation.
