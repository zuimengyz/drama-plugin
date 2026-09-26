# Literary Cinema R3D — Gate Evidence

2026-09-26 · OFFLINE RUNTIME TESTS · synthetic approvals are test attestations only. No current-work interpretation has been approved.

| Gate | Concrete evidence | Result |
|---|---|---|
| STAR candidate | Portable current-work JSON preserves H-S1/H-S2 HIGH, H-S3/H-S4 OPEN, H-S5 unknown mechanism, H-S6 UNSUPPORTED, H-S7 REJECTED; runtime validates actual LiteraryPackage anchors and pinned evidence reviews | PASS |
| Object identity | STAR-REALITY-01 uses A005; STAR-DREAM-01 uses A018/A019. Other sun, other earth and communal stars are not occurrences of that object | PASS |
| Generic symbolism | `STAR = generic hope`, empty supporting evidence, LOW: formal approval fails; no department handoff. Rejected items remain in appendix | PASS |
| Counter-evidence | Empty counter-search must be explicit; populated counter-evidence requires a per-evidence assessment. Strong contradictory counter-anchor forbids HIGH | PASS |
| Confidence | Strong scoped direct/recurrence/echo support required for HIGH; evidence review binds the exact claim/facet; no signed-in-user authority inferred from SELF_AUDIT | PASS |
| Multi-valent | Two nonconflicting items can both be approved using separate exact receipts without merging | PASS |
| Contested | OPEN/CONTESTED may propagate only with an externally attested PRESERVE_AMBIGUITY receipt. Deterministic approval fails | PASS |
| Conflicting selections | Board, Director dispatch and consumer-record selection reject deterministic adoption of declared incompatible items | PASS |
| Unapproved propagation | Authoring a Board, retaining an item, setting USER inside receipt JSON, or supplying plain SourcePin/aliased source references does not grant approval | PASS |
| Approved propagation | Synthetic externally trusted receipt passes exact work/branch/scope/item/evidence checks; ProfessionalDepartmentHost retains explicit CreativeRecord use | PASS |
| Director integration | Actual immutable DirectorArtifactStore REQUEST→DISPATCH rejects missing interpretation approval; trusted exact receipt permits design dispatch | PASS |
| Production Book | Existing complete_production_book rejects an unapproved interpretation intent before readiness; no current Book is adopted | PASS |
| Department HOW | Thirteen required owner handoffs carry questions/obligations, scope, limitations and existing state/fact refs. Unknown design fields rejected; reviewed HOW_LEAK rejected | PASS |
| Character / world | Existing C_MAN:sealed phase reference is distinct from objective E_VISIT/E_GIRL SourceUnits; nonexistent stage or I_EXIT-as-world-fact fails | PASS |
| Music | YIELD / DO_NOT_SCORE available; motif does not mandate a musical cue | PASS |
| Selective stale | Actual professional graph: I1→Camera→Lighting/Shot/Prompt-compiler invalidates after current I1 changes; unrelated Costume branch remains valid | PASS |
| Evidence stale | Changed current source-package fingerprint invalidates unchanged claim and approval; local evidence changes invalidate exact item hash | PASS |
| Approval stale | Current approval fingerprint replacement, REVOKE/REJECT and changed scope all require revalidation, even if prose is unchanged | PASS |
| Immutable versions | CreativeSourceHost requires current predecessor plus version increment; old hash-addressed original remains replayable, observations and source unchanged | PASS |
| Cross-department drift | Owner-authored DRIFT review bound to Sound decision produces INTERPRETATION_DRIFT_CONCERN without rewriting it | PASS |
| Independent source | Referenced independent source resolves and routes SOURCE_PRIORITY_REVIEW_REQUIRED, rather than being automatically rejected or overriding Canon | PASS |
| Prompt isolation | Real approved professional projection strips interpretationUses/interpretation approval refs; owner-authored observable fact enters actual Seedance2 and GPT Image IR serializers; claim, IDs, review/evidence/confidence metadata absent from final text | PASS |
| Direct prose shortcut | Copying the exact interpretation meaning into consumed professional values is rejected. The runtime does not claim to detect arbitrary paraphrases | PASS |
| Legacy | Empty opt-in field omitted from serialization; legacy professional artifact replay and existing prompt snapshots unchanged | PASS |
| Current R3 | Same files rechecked: Scene/mapper 3/3, exact-turn 15/15. S03 current Director receipt remains previously known stale; no repin or creative rewrite | PASS (preservation) |

## Executed tests

- [New runtime tests](../../../plugin/tests/test_r3d_interpretation.py), [integration tests](../../../plugin/tests/test_r3d_integration.py), [new-test output](pytest-r3d.txt).
- [Focused output](pytest-focused.txt): creative source, professional, Director, R3B/R3B-R, Seedance/VisualPromptIR/image serializer.
- [Full pytest](pytest-full.txt), [changed-file mypy](mypy-changed.txt), [full mypy](mypy-after.txt), [mypy baseline](mypy-before.txt).
- [Real current R3 gate replay](r3c-recheck.json), [before/after integrity](source-integrity.json).

These tests establish contract and dependency behavior. They do not certify literary truth, artistic quality, audience recognition or provider rendering. Semantic drift and HOW boundaries use source-pinned professional review; no NLP inference engine was added.
