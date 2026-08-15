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

Visual Review checks that the file is valid, the intended subject is present, selected references have a reasonable effect, the Shot or Asset goal is met, and no obvious prohibited content appears. On Review FAIL, allow at most one minimal revision by adjusting the prompt or reference selection. If it fails again, return the production or review failure; do not benchmark models or repair workflows automatically.
