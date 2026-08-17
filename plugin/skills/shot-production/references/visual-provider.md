# Visual Provider Capability

Apply this contract when planning or executing an image or video output. Context reads, non-visual planning, research, and creative development remain independent of it.

## Preflight

Confirm the required Drama capabilities for stable Asset/Media discovery, resolution, and import. Then confirm that the Host exposes the visual capabilities needed for the request:

- `visual.template.discover`: find and inspect a suitable official template only when the verified preference is unavailable or unsuitable.
- `visual.input.upload`: upload each resolved local reference.
- `visual.image.generate`: start one image generation with a business prompt and fixed inputs.
- `visual.job.wait`: wait for and inspect terminal job status.
- `visual.output.fetch`: fetch the completed physical output.

The runtime provider owns the executable tool schemas. Do not reproduce those schemas or convert provider tool names into Drama domain fields.

Stop with `DRAMA_PROVIDER_UNAVAILABLE` when required Drama capabilities are absent. Stop with `VISUAL_PROVIDER_UNAVAILABLE` when no visual provider is available. Stop with `VISUAL_PROVIDER_CAPABILITY_MISSING` when the provider lacks any capability required by this request.

## Technical retry policy

Apply this policy to every external visual-provider operation. Keep `technicalRetryCount` separate from `generationCount` and Visual Review revision. For each independent operation, allow the initial attempt plus at most two technical retries (`MAX_TECHNICAL_RETRIES = 2`, `MAX_TOTAL_ATTEMPTS = 3`) with a short bounded wait before retry 1 and a slightly longer bounded wait before retry 2. Honor `Retry-After` for HTTP 429 within the same budget. A technical retry never changes Stable Facts, the Reference Plan, the business prompt, or `generationCount`.

Treat HTTP 502, 503, 504, and 429; connection reset or temporary unavailability; connect/read timeout; temporary TLS interruption; transient MCP initialize, tool discovery, upload, job wait/status, output fetch, or download failure; and errors explicitly marked temporary, unavailable, or overloaded as `RETRYABLE_PROVIDER_ERROR` unless permanent evidence is present.

Do not technically retry invalid arguments or tool inputs, unsupported reference counts or templates, contract validation failures, missing Asset/Media or stable references, reference hash mismatch, content or safety rejection, explicitly permanent 4xx errors, Visual Review FAIL, or Cross-Shot Review FAIL. Route those through their business rule. Classify OAuth authorization required, `invalid_grant`, and refresh-token reuse as `PROVIDER_AUTH_REQUIRED`: allow at most one official OAuth recovery and one retry of the original preflight. OAuth recovery does not consume the technical retry budget.

Apply idempotency by operation stage:

- **Initialize / preflight / discovery**: retry the same no-consumption operation.
- **Reference upload**: retry the same local bytes with the same hash and Reference Plan. If receipt is uncertain and no recovery query exists, the identical upload may be repeated because it is not a generation.
- **Generation submit**: retry only when the Provider explicitly proves that no job was created. If a sent request times out, disconnects, loses its response, or otherwise leaves job creation uncertain, return `PROVIDER_SUBMISSION_OUTCOME_UNKNOWN`; first use available recent-job, prompt/job identity, or status recovery. Reuse a recovered job and never blindly resubmit.
- **Job wait / status**: after obtaining a `jobId`, retry only the same operation for the same `jobId`; never submit another generation because polling failed.
- **Output fetch**: for a completed job, retry `get_output` for the same `jobId`. Refresh an expired signed URL through `get_output` for that completed job, without regeneration.
- **Output download**: retry the same generated output. On signed-URL expiry, refresh it through `get_output` for the same job, then resume download.

Budgets are per independent operation, not shared across a Batch. Do not restart the production loop when a later stage exhausts its budget. On exhaustion, return `VISUAL_PROVIDER_TEMPORARILY_UNAVAILABLE` with failed stage, error class, total attempt count, last error, and any existing `jobId`; never record infrastructure failure as Visual Review or generation-quality failure.

Technical retry is not Visual Revise. A completed generation increments `generationCount`; a concrete Visual Review FAIL may trigger the one allowed targeted revision and increments `generationCount` again. Transport retries, status polling retries, output fetch retries, and download retries do not.

## Reference policy

Use the smallest sufficient reference set and enforce `referenceCount ∈ {0, 1, 2, 3}`. Reject more than three references; do not construct a dynamic workflow.

Select the most consequential visual facts for the production goal, commonly character identity, costume identity, and scene identity. Their ordering is contextual, not a fixed business rule. Formal references should originate from stable Drama Asset/Media identity rather than a prior provider session, an unexplained local file, or a PoC artifact.

Route by both generation intent and reference count:

- 0: a verified official text-to-image template.
- 1: a verified official single-reference image generation or edit template.
- 2: a verified official two-reference image generation or edit template.
- 3: a verified official three-reference image generation or edit template.

Use the Host adapter's current verified preference when it remains available and matches the intent. Discover a replacement official template only when that preference is missing or cannot perform the required intent. Do not create a saved, custom, or dynamic workflow.

## Input and output handoff

Prepare each formal reference through this semantic path:

```text
stable Asset -> stable Media -> resolve -> local download -> visual input upload
```

After generation, require:

```text
wait -> fetch local output -> Visual Review PASS -> Drama Media import -> stable mediaId
```

Visual Review checks that the file is valid, the intended subject is present, selected references have a reasonable effect, the Shot or Asset goal is met, and no obvious prohibited content appears. Apply the detailed semantic and continuity gates in [production-rules.md](production-rules.md). On Review FAIL, allow at most one minimal revision, targeted only at confirmed errors, while preserving Stable Facts and the Reference Plan; change that plan only when review proves it incorrect. If the revision fails, return the production or review failure; do not benchmark models or repair workflows automatically.
