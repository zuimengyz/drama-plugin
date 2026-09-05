# Layered review and bounded targeted revision

Read the whole draft once as a viewer before examining control notes. Then test the
Bible against the actual text. A self-report of PASS is not evidence.

## Review routing

|Layer|Evidence to examine|Smallest revision owner|
|---|---|---|
|HISTORY|actor attribution, conflicting sources, core result, certainty|affected historical claim/causal descendants|
|CAUSALITY|choice/cost and why next scene must follow; delete-scene test|current scene link; story only if spine breaks|
|TIMELINE|event order, travel and message intervals, alive/office state|affected transition and dependent scenes|
|SPACE|location, route, force/city state, simultaneous presence|affected blocking/transition|
|CHARACTER|behavior under current pressure vs invariants|character interpretation or inconsistent scene|
|CAPABILITY|what the person can do and fails to do; cost of strength|affected tactic/scene, not global stats|
|RELATIONSHIP|formal vs actual power, access, trust/debt changes|affected interaction and ledger|
|KNOWLEDGE|what this speaker received before this choice; audience difference|receipt/decision and dependent lines|
|PACING|dramatic delta, repeated meeting/exposition/battle, climax/aftermath|scene allocation or episode architecture|
|PAYOFF|setup available before use, promised closure/expiry|setup or payoff scene|
|DIALOGUE|name-blind voice swap, generic slogans, modern diction, exposition|affected spoken items|
|SUBTEXT|speech as tactic; shared facts stated for viewer only|affected line/beat|
|EMOTION|accumulation, contrast, recovery, expressive restraint|affected beat/neighbor rhythm|
|WAR|macro→meso→micro→consequence; army behavior and limits|affected battle/retreat sequence|
|VISUAL|can the action be seen; emotion explained instead of enacted|affected action/object/line|
|PERFORMANCE|target, playable action, tension/control and speech relation|upstream guidance for affected lines|

Each finding records `id`, `problem`, severity (CRITICAL/MAJOR/MINOR), layer from this
table, exact evidence (scene/line/claim), `recommendedRevisionScope` and a concrete
acceptance check. Do not diagnose simply “optimize dialogue”. Separate an unsupported
fact from a deliberate but weak creative interpretation.

## Revision execution

1. Declare the finding IDs and affected scene scopes before editing. Include only
   dependencies actually invalidated by the fix; explain any scope expansion.
2. Preserve the current draft and scene-body hashes. Change the owner: a line, scene,
   character constraint or episode link. Do not regenerate unaffected scene bodies.
3. Update the relevant Bible/ledger facts and re-read the changed scene and neighbors.
4. Recheck historical/causal integrity and the complete rhythm curve; record before,
   after, outcome and residual issue. A resolved record needs textual evidence.

At most two revision rounds after Initial Draft. A round may batch independent
findings, but is not permission to rewrite everything. Do not manufacture a weak
draft to demonstrate the mechanism. If a requested incubation test starts strong,
identify one real reader-facing improvement and preserve the comparison.

## Freeze

Freeze only the exact reviewed revision, with no unresolved CRITICAL/MAJOR issue and
an explicit disposition for minor limitations. All sixteen base layers, applicable meta reviews and twenty craft
dimensions need PASS/PARTIAL/N/A plus a concrete locator or scope reason. Record both
author review and human artistic review; human PENDING is not system FAIL but is not
human PASS. If the limit is reached with major issues, return PARTIAL/FAIL and leave
the draft UNFROZEN. No test or artifact checker can certify literary quality.

## Five meta reviews for complete/new incubation

|Layer|Evidence and failure|Revision owner|
|---|---|---|
|GENERALIZATION|Replace names, period and subject: does the rule still work? A fixture or mandatory tragic style in core fails.|skill rule or current capability selection|
|SUBJECTIVE_LENS|Whose experience, why close now, what narrative function? Check objective return and unchanged historical facts. “To move the viewer” alone is weak.|moment, POV permission or lens purpose|
|OPENING_CLOSING|Do first/last perceptions derive from thesis, aperture, POV and episode job? Detect copied hooks, compulsory tears, summary lines or full shot plans.|episode/scene anchor and dependent body|
|LONG_HORIZON|Check body/status/place/relationship/knowledge/promises across episode boundaries, payoff expiry and multi-scale rhythm; neither all climax nor all setup.|changed state and identified downstream consumers|
|STYLE_BIAS|Would a different material justify a different texture? Inspect whether the last work's restraint, grandeur, sorrow or speed has been copied without cause.|derived style and affected scenes|

Use the same finding/severity/evidence/scope format and the same two-round ceiling.
Dependency analysis precedes editing: distinguish scenes needing recheck from scenes
needing changed words. Read prose as well as records; declarations cannot prove absence
of omniscience or style bias. Human artistic acceptance remains separate.
