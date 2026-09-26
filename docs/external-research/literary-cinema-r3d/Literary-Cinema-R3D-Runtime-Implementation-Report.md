# Literary Cinema R3D — Runtime Implementation Report

2026-09-26 · Runtime implementation and controlled candidate materialization complete. **READY_FOR_FILM_INTERPRETATION_BOARD_REVIEW = YES.** Current work remains unapproved and NOT_ADOPTED. Stop at Board review; no R3C-R or production.

## Baseline

Git root: `/Users/zy/historical-plugin/drama-plugin`; HEAD `df625f9d01cc62c3f1ffed2774e88166ab37bae5`. The starting working tree already contained R3B-R changes to screenplay_playability.py / scene_dramaturgy.py, its tests, and R3D-A reports. Their pre-turn bytes, rather than HEAD versions, were frozen. [Baseline manifest](baseline-integrity.json) contains 1,106 existing files.

Inputs: all ten R3D-A formal reports and evidence/anchor ledger; actual creative_source contracts/validators/Host, Cinematic Intent/Director workspace/store, professional registry/CreativeRecord, CharacterArc and embodiment contracts, Scene/DPD boundaries, specialized visual assets, film score/editorial, preproduction and existing prompt/IR boundaries. No skill authoring or generation workflow was invoked.

### Carrier decision from current source

Existing Cinematic Intent items already own `id`, `meaning`, `why`, `scopeLevel`, `scopeRef`, priority and presentation constraints. They are therefore the carrier: add an opt-in typed `interpretation` facet and retain the item with the existing immutable DirectorArtifactStore and SourcePin. Meaning is not copied into a second thesis/Canon. Existing LiteraryPackage (including Preservation/Adaptation/CharacterArc) and Dramatic Bible are source/thesis pins. Film Board only reads those retained items.

## Changed Runtime Files

| File under plugin/src/drama_plugin | Change |
|---|---|
| contracts/interpretation.py (new) | Evidence/observation/scope/occurrence/implication facet; typed specialization of existing approval receipt; explicit consumption receipt |
| interpretation.py (new) | Source-bound evidence/approval validation, handoff, consistency result, deterministic Board, actual dependency traversal and conflicting-selection checks |
| contracts/professional.py | Optional CreativeRecord.interpretation_uses; empty field omitted to preserve old hashes |
| professional.py | Revalidate declared consumption and dependencies, enforce source aliases/selection boundary, propagate trusted approvals through package validation; strip interpretation provenance at upstream professional projection |
| hosts/creative_source.py | Retain candidate/new versions and externally approved receipts in existing store; read-only Board; predecessor/current checks |
| hosts/director_artifacts.py | Existing DISPATCH requires externally attested exact interpretation approval and compatible selected readings |
| hosts/professional.py | Resolve originals and carry approved refs through submit/package/task/dashboard |
| preproduction.py | Existing full Book gate rechecks consumed interpretation chain and rejects unapproved interpretation intent |

No Provider, service, MCP, storage implementation, Seedance/image Prompt Generator, R3B-R gate, R2/R3 screenplay or existing creative candidate changed. No new top-level Skill.

## Interpretation Layer Model

- **Source fact:** only pointers to SOURCE_FACT SourceUnits in the current LiteraryPackage. The facet cannot author fact text or promote an interpretation unit to a fact.
- **Source observation:** scoped/versioned anchor-linked observation inside the hashed item. SourceAnchor offsets/text/hash remain owned by LiteraryPackage; no editable parallel source copy.
- **Hypothesis / working interpretation:** explicit layer, scope, supporting/counter-evidence, confidence, limitations and status on the existing intent's meaning.
- **Approved for this adaptation:** derived only by validating an exact separate approval receipt against externally trusted Host approved_refs. Rendering or storing an item does not change it into an approved item.

Source Canon and Preservation remain above interpretations. Formal approval revalidates the existing LiteraryPackage and pinned evidence/canon-preservation review. This is professional evidence coordination, not a programmatic proof of literary truth.

## Evidence / Counter-Evidence

Every observation/evidence/occurrence anchor must belong to the pinned package and explicitly reviewed scope. Counter-evidence must have one assessment per counter item. Empty counter-evidence is accepted only with explicit NO_COUNTER_EVIDENCE_FOUND_IN_REVIEWED_SCOPE. Limitations cannot be empty. Unsupported/rejected hypotheses remain retained, cannot carry implications and cannot be approved or handed off.

Confidence has no numeric score. HIGH needs strong scoped DIRECT_TEXT/RECURRENCE/STRUCTURAL_ECHO support; strong contradictory counter-evidence cannot be ignored. Confidence review hashes the claim and evidence facet; evidence-fingerprint and full item hash bind the user receipt. SELF_AUDIT is explicitly separate from user authority. The system validates the review's source/version/boundary, not the semantic correctness of a reviewer's interpretation.

## Confidence / Ambiguity

OPEN, MULTI_VALENT, CONTESTED, UNSUPPORTED and REJECTED are explicit states. Multiple compatible readings can coexist. OPEN/CONTESTED cannot become deterministic constraints: explicit PRESERVE_AMBIGUITY approval is required. Declared conflicts cannot be combined as deterministic approvals by the Board, Director or professional consumer. No giant symbolism taxonomy or NLP classifier was introduced.

## Approval

InterpretationApproval specializes the existing PROFESSIONAL_CREATIVE_APPROVAL shape with item fingerprint, evidence fingerprint, work/branch/scope, actor type, decision, approval mode and version. `actorType=USER` in untrusted JSON is insufficient: the exact receipt pin must be in Host-supplied approved_refs. Rejection/revocation, changed scope, changed evidence or claim, and obsolete current pins fail validation. One exact receipt can be shared by many legitimate departmental uses; it is not per-shot creative approval.

CreativeSourceHost retains approved receipts only after that external attestation. No current-work user receipt was created. Synthetic test receipts are clearly fixture-only.

## Interpretive Spine Carrier / Film Interpretation Board

`project_board` validates real facet/source data and optional exact receipts; it never edits items or creates approval. `render_board` only formats projected rows. Current main view selects eight existing rows, with all 15 items in the evidence appendix. Its `sourceFingerprint` binds the complete item set. Retained originals and a byte-identical portable fixture make it replayable.

[Current Board](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/interpretation/film-interpretation-board-r3d-candidate.md) · [Evidence appendix](/Users/zy/historical-plugin/artifacts/flagship-literary-film-01/creative/interpretation/interpretation-candidate.json) · [Candidate report](Literary-Cinema-R3D-One-Ridiculous-Man-Interpretation-Candidate-Report.md).

## Character State Handoff / World Relation Handoff

Implications can reference existing `character_id:arc_stage` in LiteraryPackage CharacterArc; invalid state refs fail. This remains phase-level Character Dramaturgy ownership, separate from current DPD objectives/tactics. No costume, face, pose or performance is generated from psychological labels.

World fact refs must resolve SOURCE_FACT units independently of the Character state link. Current candidate distinguishes C_MAN:sealed from E_VISIT/E_GIRL. The Director's audience relation is a question/obligation, never a joint worldPsychology field. Existing source facts and objective world conditions cannot be replaced by an interpretation of the protagonist.

## Motif Runtime

Occurrences have distinct IDs, source anchors, local function, scope, linked interpretations and evolution. RETAIN/EXPAND/RECONTEXTUALIZE/CONTRAST/OPEN remain possible without one permanent symbol. The current STAR fixture keeps reality and dream-identification separate, and does not merge other sun/earth/stars. H-S1/H-S2 are bounded HIGH; H-S3/H-S4 stay OPEN; generic hope is UNSUPPORTED and literal navigation home REJECTED. None are user-approved. See [Gate Evidence](Literary-Cinema-R3D-Gate-Evidence.md).

## Cross-Department Implication

`department_handoff` requires exact current approved intent/receipt and implication ID. Output includes owner, question or obligation, scope, limitations, negative boundaries, ambiguity policy, optional Character state/world-fact refs and music YIELD/DO_NOT_SCORE. It does not provide lens, shot size, light recipe, wardrobe, cut duration or a raw meaning field. Contract rejects HOW fields; professional evidence review must attest QUESTIONS_ONLY; HOW_LEAK blocks.

Supported owners: Story/Scene, Character Dramaturgy, Director, Performance, Costume, Specialized Asset, Production Design, Cinematography, Lighting, Color, Sound, Music, Editorial and Shot. Prompt is not a consumer. The specialized asset/legacy costume authoring rules remain unchanged: receiving a question does not authorize a parallel concrete asset writer. Typed assets still use their existing original owner inputs and production gates. This round implements approved question handoff and CreativeRecord consumption; it does not automatically generate new typed assets, DPDs or score plans.

A CreativeRecord explicitly retains interpretation+approval pins, implication ID, scope, reviewer/disposition and the fingerprint of its own professional decision. Both ownership and normal department validation remain necessary. Declaring an interpretation only as a generic/aliased source cannot bypass explicit consumption.

## Selective Staleness

No global invalidation registry was added. Existing current-map and SourcePin hashes govern each actual dependency edge. A changed item or receipt makes its users stale; their existing downstream professional/Shot/Prompt/Book validation follows actual originals. Tests exercise I1→Camera→Lighting/Shot/Prompt-compiler while unrelated Costume remains valid. A shared whole LiteraryPackage pin intentionally invalidates all real consumers of that changed package; this preserves existing granularity rather than inventing per-sentence exemptions.

New versions require exact current predecessor and incremented version. Old hash-addressed originals remain readable. Historical replay does not imply current formal readiness. Physical deletion of a consumed original causes validation failure rather than broken provenance being accepted; no delete API was added.

## Consistency Review

`validate_consumption` compares the professional decision fingerprint, owner/scope and current approval chain. Reviewed DRIFT produces INTERPRETATION_DRIFT_CONCERN; UNREVIEWED blocks. Independent source evidence is resolved and routes SOURCE_PRIORITY_REVIEW_REQUIRED, without automatically overriding Canon or rejecting the evidence. Neither pathway rewrites a department. Professional/Director review owns the semantic judgment; Host does not guess whether a dark image or quiet soundtrack contradicts a novel.

## Prompt Isolation

Existing upstream professional projection validates the chain, then removes interpretationUses and interpretation/approval pins from projected records. Professional decisions remain owner-authored. Direct verbatim reuse of the interpretation claim as a professional value is rejected. A real test compiles an approved observable camera decision through existing VisualPromptIR→GPT Image and Seedance2PromptGenerator: interpretation text/IDs/confidence/evidence/counter-evidence/review metadata are absent from final model text. Generator and Provider code are unchanged.

The test assembles the IR from the professional decision explicitly; no automatic general department-to-IR translator was added. It verifies the legitimate handoff path and exact-prose guard, not semantic detection of arbitrary paraphrases. Previously compiled immutable IR/Prompt artifacts remain audit history; current submission/Book must use current dependencies.

## Legacy Reconciliation

No-facet artifacts preserve serialization and existing validation; no automatic formal approval/readiness upgrade. The same actual R3 candidate was replayed with the [unchanged R3B-R rechecker](r3c-recheck.json): S01/S02/S03 dramaturgy and mapper PASS, exact-turn 15/15 PASS, original Director-pin replay 15/15 PASS, local listener/silence PASS. S03's two current Director checks remain STALE_DIRECTOR_DRAMATURGY as before this task. No Director receipt was repaired/rebound, no screenplay revised, no adoption.

## Tests

- New R3D: **67 passed** ([log](pytest-r3d.txt)).
- Focused source/professional/Director/R3B/R3B-R/Seedance/IR/image boundaries: **400 passed** ([log](pytest-focused.txt)).
- Full pytest: **2902 passed in 136.61s (0:02:16)** ([log](pytest-full.txt)).
- Strict changed/new-file mypy with imported historic errors silenced: **13 files, zero errors** ([log](mypy-changed.txt)); full mypy separately **40 baseline errors in 13 files → same 40 errors in same files**, **0 new**; checked source files 203→205.
- `git diff --check`: PASS.
- [Source integrity](source-integrity.json): 1,106 existing files; exactly 6 intended existing Runtime edits, other 1,100 unchanged; no unexpected change.

All tests offline. They include existing local media-fixture regression tests; no image/video/audio generation service or paid API was invoked, and no current-work media was generated.

## Known Gaps / Authority Boundary

1. Semantic evidence quality, question-versus-HOW and drift still require honest professional review; labels alone do not establish literary truth. Runtime verifies exact evidence and review scope, not a free-prose literary theorem.
2. External Host supplies trusted approved_refs/current maps as in existing Director dispatch. This implementation does not introduce authentication, an approval UI, storage service or automatic user-approval inference.
3. The current work is deliberately unapproved. No formal specialized assets, score, new DPD or production pipeline run was authored from it. Downstream entry points that do not supply trusted interpretation context fail closed rather than infer permission from stored labels; production wiring is not an approval bypass.
4. Whole-package source dependencies retain their existing coarse granularity. Only item-level interpretation changes are independently selective.
5. Artistic visibility/audibility and audience recognition are not proven by contract tests. Current R3 S03's inherited stale Director receipt remains unresolved by design.

## Source Integrity — Before / After

Hashes are SHA-256 of file bytes; compared to the beginning of this turn, including pre-existing R3B-R changes. Full 1,106-file evidence is in source-integrity.json.

| Frozen input | Before | After |
|---|---|---|
| 04-screenplay-r3-candidate.md | `39a1f9fa35d1e1becbeac667b911dfb9ab2e0dbaef6fb10e8335044fc0aadb3f` | `39a1f9fa35d1e1becbeac667b911dfb9ab2e0dbaef6fb10e8335044fc0aadb3f` |
| screenplay-r3-dramaturgy-sidecar.json | `90ceeda49fee4542c1cb08b482bc9deb23fc6d4945690fdaddd26c876356a1a6` | `90ceeda49fee4542c1cb08b482bc9deb23fc6d4945690fdaddd26c876356a1a6` |
| director-performance-candidate.json | `4f1033e73234c5ae5dddbbb630694502e24250f4f9e4d1798c2debe6c94187ef` | `4f1033e73234c5ae5dddbbb630694502e24250f4f9e4d1798c2debe6c94187ef` |
| 04-screenplay-r2.md | `dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08` | `dae155c1d27e6091d8277e773fa22e1ca20b549e6a3e936322256a246b425c08` |
| literary-package.json | `1f5968b409ae1eec1ce5441ba9210749b30121ea047593c331fe82d23bd93edf` | `1f5968b409ae1eec1ce5441ba9210749b30121ea047593c331fe82d23bd93edf` |
| scene_dramaturgy.py | `f121449ad61278a58293a2a352b7bc822147d4403de763c324eeaa6458a3aaf1` | `f121449ad61278a58293a2a352b7bc822147d4403de763c324eeaa6458a3aaf1` |
| scene_dramaturgy.py | `c56f586be4954fe618fcb201233e259240b7789a270627ebfe6aef9d3444f118` | `c56f586be4954fe618fcb201233e259240b7789a270627ebfe6aef9d3444f118` |
| screenplay_playability.py | `e4cd188929d42e56bb289cc33215234b7f3da03ba5f8cdabed035b0b00d77160` | `e4cd188929d42e56bb289cc33215234b7f3da03ba5f8cdabed035b0b00d77160` |
| screenplay_playability.py | `1a04fd9fcbd1137615c8190d78370f083577af391182cf4d13f2f73f4748c2f3` | `1a04fd9fcbd1137615c8190d78370f083577af391182cf4d13f2f73f4748c2f3` |
| R3D-A reports (14 files; path/hash manifest digest) | `b41cbcde398d4727b34b3f6bac21bc58f47cf798eecb1ec848a695a4ce243ea6` | `b41cbcde398d4727b34b3f6bac21bc58f47cf798eecb1ec848a695a4ce243ea6` |
| Provider / Prompt boundaries (43 files; path/hash manifest digest) | `5dbe1bd197d9ede14ec86403edc148187113387d26ed825bf9f7096ec47a21cf` | `5dbe1bd197d9ede14ec86403edc148187113387d26ed825bf9f7096ec47a21cf` |
| MCP / Service (158 files; path/hash manifest digest) | `0a6e9a49422be0bca46df40d50ffee521c40a38c388aa3d23acc2fcc1730603e` | `0a6e9a49422be0bca46df40d50ffee521c40a38c388aa3d23acc2fcc1730603e` |

## Mandatory Status

```text
EVIDENCE_BOUND_INTERPRETATION_IMPLEMENTED = YES
COUNTER_EVIDENCE_IMPLEMENTED = YES
INTERPRETIVE_CONFIDENCE_IMPLEMENTED = YES
AMBIGUITY_MULTI_VALENCE_IMPLEMENTED = YES
INTERPRETIVE_SPINE_FACET_IMPLEMENTED = YES
SECOND_CANON_CREATED = NO
NEW_TOP_LEVEL_INTERPRETIVE_SKILL = NO
HUMAN_INTERPRETATION_APPROVAL_IMPLEMENTED = YES
FILM_INTERPRETATION_BOARD_IMPLEMENTED = YES
CHARACTER_STATE_HANDOFF_IMPLEMENTED = YES
WORLD_RELATION_HANDOFF_IMPLEMENTED = YES
MOTIF_RUNTIME_IMPLEMENTED = YES
CROSS_DEPARTMENT_IMPLICATION_IMPLEMENTED = YES
INTERPRETATION_DRIFT_REVIEW_IMPLEMENTED = YES
SELECTIVE_STALENESS_IMPLEMENTED = YES
PROMPT_DIRECT_INTERPRETATION_PROJECTION = NO
R3_SCREENPLAY_CHANGED = NO
R3C_R_STARTED = NO
PAID_GENERATION = 0
ONE_RIDICULOUS_MAN_INTERPRETATION_CANDIDATE_CREATED = YES
ONE_RIDICULOUS_MAN_INTERPRETATION_APPROVED = NO
STAR_TRACE_MATERIALIZED = YES
STAR_GENERIC_HOPE_REJECTED_AS_DEFAULT = YES
FILM_INTERPRETATION_BOARD_STATUS = AWAITING_USER_APPROVAL
READY_FOR_FILM_INTERPRETATION_BOARD_REVIEW = YES
```

Stop at user Board review. This is not R3 creative approval, R3 adoption, Book readiness or permission to begin R3C-R.
