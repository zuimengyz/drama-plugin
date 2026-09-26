# Literary Cinema R3D-R — Approval Context Propagation Reconciliation

## Outcome / Baseline

**R3CR-RT01 resolved. READY_TO_RESUME_R3C_R = YES.** Only the runtime integration blocker and professional-chain preflight are completed. R3C-R creative rewriting has not resumed; this is not creative approval, adoption, production readiness or permission to generate media.

Baseline HEAD: `df625f9d01cc62c3f1ffed2774e88166ab37bae5`. The starting working tree already contained R3B-R, R3D and R3C-R work. [Baseline](baseline.json) records that status and freezes 641 existing files before this repair. The R3C-R Anti-Drift report, R3D Runtime Implementation report and Gate Evidence were reread against current source, including the actual Host and pure-validator callers, rather than relying on old line numbers.

## R3CR-RT01 reproduction

The existing R3C-R diagnostic used a temporary offline Specialized Asset fixture, not a newly authored current-work Character or Costume design. This round preserves that distinction and reuses its fixture setup in [r3d_r_helpers.py](../../../plugin/tests/r3d_r_helpers.py).

[Before evidence](reproduction-before.json): direct `validate_bible` with the exact external approval passes; `SpecializedAssetHost.submit` without context raises `USER_INTERPRETATION_APPROVAL_REQUIRED`; passing the external context to that Host raises `TypeError` for an unexpected keyword. The old diagnostic and its evidence were not overwritten.

## Root cause / Trust boundary

The R3D validator correctly failed closed. Its caller chain could not deliver the authorized execution's approval pins. The same omission existed in compilation replay and the professional projection branch, not in the approved interpretation itself.

`approved_interpretation_refs: tuple[SourcePin, ...] = ()` remains a keyword-only, external caller parameter, consistent with ProfessionalDepartmentHost. It is never read from candidate JSON, Work content, a retained receipt or an InterpretationUse. No approval semantics, claim, review fingerprint, source freshness or scope rule was relaxed. No new context class, taxonomy, contract field, entity, storage mechanism or skill was introduced.

Stored provenance answers what was consumed. External context answers whether this execution may consume it. Every revalidating entry requires that context again. Supplying a stored artifact containing a USER receipt still fails when external context is absent.

## Changed Runtime Files

Exactly five existing runtime files changed in this round:

| File | Repair |
|---|---|
| `plugin/src/drama_plugin/hosts/specialized_asset.py` | Accept and forward explicit trusted context through submit, compile, department_records, optional save_style validation, and production authority / request / authority-context replay wrappers. No trusted refs serialized into payloads. |
| `plugin/src/drama_plugin/specialized_asset.py` | Forward context through validate_assets → upstream → validate_bible; department_values' literary branch; compile_asset and provider_projection replay. Projection text and schema unchanged. |
| `plugin/src/drama_plugin/professional.py` | Forward the already accepted context through SPECIALIZED_ASSET_PROJECTION validation and exact department_values replay. |
| `plugin/src/drama_plugin/hosts/professional.py` | Resolve declared Specialized Asset record source pins and optional Global Visual Style imaging source pins during original/package replay. These resolve provenance only; they do not confer trust. |
| `plugin/src/drama_plugin/visual/still_knowledge.py` | Its optional validate_imaging professional validation accepts and forwards the same external context. No IR mapping or prompt serializer changed. |

Tests: [test_r3d_r_approval_context.py](../../../plugin/tests/test_r3d_r_approval_context.py). Diagnostic: [preflight.py](preflight.py). Existing Interpretation contracts and validators, creative-source/Director stores, R3B-R, Prompt Generator and Provider implementations remain byte-identical to the baseline.

## Specialized Asset propagation

The formal chain is now:

```text
authorized caller's explicit refs
→ SpecializedAssetHost.submit / compile / department_records
→ validate_assets
→ upstream (Character / Director / source-world originals)
→ validate_bible
→ require_record_consumption / validate_consumption
→ approved_interpretation
```

The identical tuple also travels through each repeated validation. Default empty context retains legacy behavior and rejects opted-in dependencies. No candidate-side fallback exists.

## Compile / records / replay

Compilation validates before creating its receipt; provider_projection recompiles with the same external context before checking exact equality. The name provider_projection describes an existing pure projection function; no Provider or Prompt Generator implementation was altered.

Character and Costume views still contain their existing exact Specialized Asset source pin. Their dependency graph reaches the unchanged Character record containing interpretation ref, approval ref, implication, scope and professional decision fingerprint. The view does not copy that InterpretationUse onto a different professional decision, which would misrepresent its owner and fingerprint. The immutable original retains the actual use.

Professional Host submit, original-only resolution and DirectorPackage retention revalidate that graph. Tests exercise successful trusted replay and rejection without context after prior successful storage. Production authority validation, authority-context compilation/replay and nested video request validation also require explicit context; they never promote retained provenance into execution authority. These are offline validation tests, not media submissions.

## Same-pattern consumer audit

“Opt-in” below means an actual InterpretationUse or an actual consumed dependency containing one. It does not mean every request must opt in.

| Consumer | Opt-in Interpretation? | Host accepts trusted refs? | Validation receives refs? | Result |
|---|---:|---:|---:|---|
| Specialized Asset | Yes, via owned upstreams | Yes, repaired | Yes, repaired | Exact blocker, compile, records and replay PASS |
| Costume | Yes, same typed asset path / projected professional view | Yes | Yes, repaired projection branch | No separate costume authoring bypass; PASS |
| Character professional | Yes, direct CreativeRecord | Yes, existing ProfessionalDepartmentHost | Yes, existing generic validator | Positive and missing-context tests PASS |
| Cinematography | Yes, direct CreativeRecord | Yes, existing generic Host | Yes | Positive and missing-context tests PASS |
| Lighting | Yes, direct or consumed professional dependencies | Yes, existing generic Host | Yes | Positive/missing-context and R3D dependency tests PASS |
| Sound | Yes, direct CreativeRecord | Yes, existing generic Host | Yes | Positive/missing-context and R3D drift tests PASS |
| Editorial | Yes, direct CreativeRecord | Yes, existing generic Host | Yes | Positive and missing-context tests PASS |
| Optional global-style imaging basis | Yes, when approved camera/director basis opts in | Yes, repaired save_style | Yes, repaired validate_imaging | Trusted/missing context and original resolution PASS |

Additional same-root repairs are counted as **2 paths** beyond the core Specialized Asset lifecycle: (1) downstream professional projection/original-package replay; (2) optional global-style imaging professional validation. Resolver additions are part of those paths, not separate architectural features. No new department was opted into Interpretation.

## Positive tests / Negative tests

| Case | Expected | Observed |
|---|---|---|
| Exact original blocker: Character + valid use + trusted exact receipt | Formal submit PASS | PASS |
| Same candidate with no external context | USER_INTERPRETATION_APPROVAL_REQUIRED | Rejected |
| Different interpretation's approval | Reject | Rejected |
| Changed current interpretation, evidence source or approval fingerprint | Reject stale | Rejected (3 cases) |
| Trusted receipt with wrong scope, subject or evidence fingerprint | Reject despite trust | Rejected (3 cases) |
| JSON declares USER/approved; stored original already contains USER receipt | No self-approval | Extra field rejected; no-context execution rejected |
| Asset character stage differs from approved upstream | Reject | CHARACTER_DRAMATURGY_STAGE_MISMATCH |
| Character / Costume compile and department_records | PASS only with external context | PASS / missing context rejected |
| Stored projected view and full DirectorPackage replay | PASS only with external context | PASS / missing context rejected |
| Production original/authority/request replay | No retained-authority bypass | PASS with context; fail closed without it |
| Forged trusted-ref field in Work content | Ignore as execution authority | Still rejected |
| Legacy no Interpretation | No approval requirement added | PASS; identical explicit-empty/default output |
| Optional imaging original resolution | Preserve approved upstream context | PASS / missing context rejected |

## Prompt isolation / R3B-R regression

Context is only passed as a function parameter. No new approval/evidence metadata is inserted into compilation bodies, IR or provider text. Tests inspect the actual asset projection and bound request prompt; the unchanged R3D isolation test executes professional projection through Seedance 2 and GPT Image serializers. Interpretation meaning, IDs, approval keys, evidence/review/confidence metadata are absent from final text.

Contextual vocative, self-directed action and same-R3-candidate regression tests passed. Their runtime and test sources are unchanged. No dialogue, actor/target, response or exact-turn rule was modified.

## Regression results

- New focused suite: **17 tests**, all included in the passing focused and full runs.
- [Focused regression](pytest-focused.txt): **329 passed in 27.72s** (R3D, professional, Specialized Asset, still knowledge, R3B-R, Seedance and visual prompt isolation).
- [Full pytest](pytest-full.txt): **2919 passed in 143.18s**. This also includes existing R3B and all other repository pytest tests.
- [Strict changed/new-file mypy](mypy-changed.txt): **8 files, zero errors**, using the established `--follow-imports=silent` approach to separate imported historical test errors.
- [Full mypy before](mypy-before.txt) / [after](mypy-after.txt): **40 errors in 13 files, 205 source files checked**, unchanged. [Normalized comparison](mypy-comparison.json): **0 new errors, 0 removed errors**.
- [git diff --check](diff-check.txt): PASS.

All execution was local/offline. Existing regression tests may create local test fixtures; no current-work media or paid generation was performed.

## R3C-R preflight recheck

[After evidence](preflight-after.json) separates real current-work approval verification from the same offline professional-entry fixture used by R3C-R:

1. Read-only revalidation of **11 exact existing user approvals**: PASS.
2. Recomputed **15 existing department handoffs**, checked for equality: PASS, including Character, Costume and Specialized Asset.
3. Same R3CR-RT01 fixture: direct validator and formal Host submit PASS with trusted refs; missing context still fails.
4. Character and Costume compile / department_records: PASS.

The diagnostic caller's allowlist is frozen separately in [authorized-context.json](authorized-context.json), tied to the baseline approval artifact hash and the user's explicit authorization to reuse existing receipts. Runtime never loads that file or infers authority from a candidate. No new user approval was requested or minted. Temporary synthetic professional receipts are test fixtures only.

No new current-work professional HOW, screenplay, DPD or Director candidate was created. Preflight success resolves the integration blocker; it does not evaluate a still-unwritten creative revision.

## Source Integrity

[Full before/after manifest](source-integrity.json): **641 existing files checked; 5 intended runtime files changed; 636 unchanged; 0 unexpected changes**. This includes all existing creative files under the work, prior R3C-R/R3D/R3D-A reports, approval/Board originals, R3B-R sources, and Provider/Prompt source files. Current-work Interpretation claims, Board claims, user receipts and their immutable store objects remain unchanged.

| Frozen source | Unchanged SHA-256 |
|---|---|
| R3 screenplay | `39a1f9fa35d1e1becbeac667b911dfb9ab2e0dbaef6fb10e8335044fc0aadb3f` |
| R3 dramaturgy sidecar | `90ceeda49fee4542c1cb08b482bc9deb23fc6d4945690fdaddd26c876356a1a6` |
| R3 Director candidate | `4f1033e73234c5ae5dddbbb630694502e24250f4f9e4d1798c2debe6c94187ef` |

## Known gaps / Authority boundary

- External authorized callers must continue supplying trusted refs and current pins. Persisted provenance does not authenticate a future caller; no authentication or approval storage architecture was added.
- This scope verifies the existing professional preflight and explicit Specialized Asset revalidation APIs. It does not opt every legacy media adapter into Interpretation or authorize production. A caller that omits context for an opted-in original continues to fail closed.
- Owner reviews still determine artistic meaning, implication scope and professional consistency. This repair adds no prose classifier or artistic decision.
- R3C-R creative rewriting remains unstarted, including its previously documented current Director freshness issue. No adoption, Book approval or A5 readiness is claimed.

## Mandatory Status

```text
R3CR_RT01_FIXED = YES
SPECIALIZED_ASSET_HOST_ACCEPTS_APPROVAL_CONTEXT = YES
SPECIALIZED_ASSET_VALIDATION_PROPAGATES_CONTEXT = YES
SPECIALIZED_ASSET_COMPILE_REVALIDATES_CONTEXT = YES
SPECIALIZED_ASSET_RECORDS_PRESERVE_DEPENDENCY = YES
CANDIDATE_SELF_APPROVAL_BYPASS = NO
LEGACY_NO_INTERPRETATION_PATH_REGRESSION = NO
SAME_PATTERN_AUDIT_COMPLETED = YES
ADDITIONAL_SAME_ROOT_FIXES = 2
R3B_R_REGRESSION = NO
PROMPT_INTERPRETATION_LEAK = NO
R3_SCREENPLAY_CHANGED = NO
INTERPRETATION_CLAIMS_CHANGED = NO
PAID_GENERATION = 0
READY_TO_RESUME_R3C_R = YES
```

STOP. Do not resume R3C-R creative work in this repair.
