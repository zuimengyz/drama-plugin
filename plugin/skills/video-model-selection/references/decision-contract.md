# Decision and execution contract

`drama_plugin.visual.video_selection` defines provider-neutral run-context records.
The Host supplies inspected evidence; a boolean alone is not a source. Requirements
and input roles are immutable. Capabilities are verified at official/interface/
template/project layers; combination support is explicit. Quality observations
include task scope, sample count and evidence independently of capability.

`qualify` returns exclusions and LIMITED_TRIAL or QUALIFIED for each candidate.
`choose` orders eligible candidates by fewer documented fit concerns, then scoped
quality evidence, then complete cost. LIMITED_TRIAL is permitted only in trial
scope and does not grant batch production. The caller records the decision rationale
and fallback triggers; `seal_decision` binds the exact request, requirements,
candidate and budget scope. Expired evidence or changed material invalidates it.

The existing production helper accepts video decisions alongside compiled images.
Use its `init-stage` command once with `stage_id`, explicit `authorization_ref`,
`budget_credits`, `frames` and `protected_targets`. This same file owns all stage
attempts, images and videos. Never initialize another state to restart the budget.
`reserve` requires a fresh `quote` bound to request fingerprint and a current
`balance` observation. Reserves count confirmed costs plus all unsettled estimates;
failed/cancelled jobs are not presumed refunded. One outstanding unreviewed request
blocks further spending. Limits are three initial images, one correction per image,
and two videos across all models. Input preparation also uses this stage file.

Use `replan` after evidence-based diagnosis to replace a failed path or add a
necessary input target, preserving requirements and every attempt. Model, mode,
template, sound and parameter changes require a new sealed decision and quote.
No successful target can be regenerated. The same result/review/billing commands
and pause rules apply; unknown submission is recovered against its original job.
The adapter never alters the reserved request after reservation.

Record `technical` and `copies` with `inspect`: file hash, local path, provider
upload name, stable Media ID and storage object have distinct fields. Copies bind
to one attempt/job and do not add generations. Record complete content checks
through `review`; partial observation stays pending and blocks new spending.
User adoption remains PENDING until separate explicit user evidence exists.

The helper controls the documented Host entry point, not arbitrary external tool
calls. The Host must refresh live template/node/price/input evidence before paid
execution and submit only the persisted returned request. The adapter integration
guide documents concrete tool mappings and loading checks.
