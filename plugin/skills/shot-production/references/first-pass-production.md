# First-pass image production

Use for new Shot images and image revisions. Existing adopted AV is outside this gate.

An explicit user request for one new comparison candidate may continue the same
Work-owned stage with `ProductionRoute.continuation`. Bind the authorization,
original stage/attempt fingerprints, same formal target, one new video and quoted
credit ceiling. Refresh current Canon rather than inheriting an old attempt's
duration. Save the route revision and replan the frame; preserve every original
attempt/review/output and the stage budget/exposure. This is not ordinary recovery
or authority to regenerate a PASS without that new request. Reusing the same
authorization cannot reset its baseline or grant a second generated candidate.

A fresh balance observation can enumerate `included_usage_events` already
reflected in that balance, but only completed/failed owned jobs with recorded
provider usage may be excluded from the additional cash hold. Their unknown
invoice settlement continues to retain the full reserve against the stage budget.
Never exclude an unknown/running job or invent a usage event. A continuation retry
requires explicit NO TASK and NO CHARGE evidence and is limited to one transport
retry; artistic retry remains outside its authorization.
The Host still owns provider execution; the Python helper only builds, validates,
reserves and records requests in local Agent Run Context. It neither creates Domain
records nor calls the cloud. Run it with the plugin's Python dependencies available.

## Compile before spending

Use `drama_plugin.visual.frame_request.FrameSpec`, `Template`, and `compile_frame`.
The concrete JSON fields are defined in `src/drama_plugin/visual/frame_request.py`.
Do not construct a second raw request beside the compiled request.

For each actor, bind the stable entity key to a distinct label, reviewed identity,
age/hair/beard, active costume, and this Shot's position/pose/action/gaze/visibility.
For a subjective Shot, mark the viewpoint actor POV, with visible hand/sleeve facts;
do not request their face in the background. Never change an actor's screen position
or action owner merely to accommodate a failed output. Use one entry moment for an
input frame. Future motion belongs in the video prompt. General acting directions
may modulate an approved action but cannot ban its posture, hand contact or gaze.

For focal props, specify current state, component geometry/count, front/rear and
attachment, hand contact and forbidden outcomes. A reference depicting an earlier
state requires an explicit `reference_delta`, and a representative of that state
transition must pass before expansion. Reuse a reviewed current-state reference if
available. Do not generate a new master automatically; if the old reference keeps
winning, stop and resolve the reference plan.

Freeze ordered references with entity key, Asset ID, Media ID, explicit version,
content hash and state. `reference_lock` maps `asset_id/media_id/version` to hash.
Do not select by same display name, filesystem newest time or provider filename.
Resolve/download the chosen Media, check its bytes, upload those bytes and save a
local JSON upload receipt containing `name` (the provider's actual returned name)
and `content_hash` (hash of the uploaded bytes). Bind `upload_receipt` to that file;
`uploaded_hash` must equal the frozen hash. A provider filename is not a byte hash.
Reject missing visible-character references; explicitly explain omitted secondary
references within the three-input cap. A rejected candidate is never an identity
master. Identity repair must retain the visible characters' formal master bindings;
a single failed-frame edit is insufficient evidence for identity recovery.

Inspect the official template once per revision: ordered image slots must match
actual image_1/2/3 links, prompt and seed slots must be overwritten, and output size
must match the target ratio or have a concrete reviewed crop plan. The 3-input Flux
Object Swap template inherits dimensions from its first reference. Text saying
“16:9” does not change its 3:2 input dimensions. Do not change a template graph or
create a workflow to bypass this check. Select another suitable official template
when necessary. `Template.evidence`/`graph_hash` retain the inspected capability
source; `supported_types` records the Host's intent assessment, not proven quality.
Save the inspected workflow object (its `nodes` and `links`) to `graph_path` and
fingerprint that object with `sha256_canonical` as `graph_hash`. The current helper
validates direct LoadImage-to-numbered-image ports and direct numeric dimensions
or GetImageSize from a PNG reference. Other port/dimension encodings fail closed;
add a narrowly tested inspection adapter before using another official template.

Route on task requirements as well as count: single static / two-person / person
with focal prop / complex pose / establishing. Count compatibility alone never
qualifies a model for identity, precise prop structure or pose fidelity. Requalify
representative shots when model, template or reference-state cohort changes. Do not
claim the correction model is universally better from an uncontrolled edit run.

## Reserve → submit → outcome → review

Compile the planned frames to a JSON array, then use the packaged helper:

```sh
python skills/shot-production/scripts/visual_preflight.py init --state /absolute/run/campaign.json --input /absolute/run/compiled.json
python skills/shot-production/scripts/visual_preflight.py reserve --state /absolute/run/campaign.json --shot SHOT_ID
```

The first command selects up to three actual planned representatives covering risk,
model/template and reference state. If coverage needs more, split the plan into
scoped cohorts; do not add extra test images. The second command **persists a
reservation before printing one provider item**. Submit only its `request`, then
record its `attempt_id`; never submit the entire `frames` map or reserve through a
second state file. Initial and repaired frames both consume the campaign ledger.

Only one image may be outstanding until reviewed. This deliberately bounds exposure
for this class of costly structured visual tasks. Review representatives before
reserving nonrepresentatives. Representatives remain usable deliverables. Use
`result --input outcome.json` with `attempt_id`, `status` (COMPLETED/UNKNOWN/FAILED/
NOT_CREATED), `job_id`, `output_hash` for a completion, and `evidence`. Optional
`credits` requires `billing_event_id`; unknown billing stays null, never zero.
When billing arrives later, use `billing --input billing.json` with `attempt_id`,
`job_id`, `credits` and `billing_event_id`. The job must match; the same event is
idempotent and cannot be counted on another attempt.
A timeout after submit stays UNKNOWN and prevents a fresh generation; recover the
same job. Terminal provider failures pause for recovery, separate from visual FAIL.

Use `review --input review.json` with `attempt_id`, the exact `output_hash`,
`reviewer`, evidence path/description, `checks`, and `findings`. Inspect identity,
costume, blocking, prop structure/state, scene, anatomy, modern artifacts and crop;
use their uppercase categories as check keys. Also check each `required:<text>`
and `forbidden:<text>` from the spec. A nonapplicable dimension needs a rationale in
evidence, not omission. UNKNOWN is incomplete; a completed job is never quality PASS.

Findings carry `category`, `severity`, `evidence` and `remedy`:

- MAJOR semantic/identity/costume/action/prop/anatomy failures require REGENERATE;
  keep the frozen actor/blocking/reference contract and fix only recorded failures.
- MINOR nonsemantic texture, small background details, or safe framing adjustments
  use ACCEPT or POSTPROCESS with rationale. Mark PASS_WITH_NOTES and retain the
  postprocessing task; do not regenerate a whole image for such details.
- A wristwatch is MAJOR when visible and historically material; if safely cropped
  without harming required evidence, record MINOR/CROP and the postprocessing plan.
  Missing required evidence can never be relabelled cosmetic.

Use the content-review standard in SKILL.md. A rejected candidate does not exhaust its target. Host replanning, reassessment and working-input selection use the same state and stage totals, without manual exceptions. Preserve prior pause/review/plan versions. Validate fingerprints and ownership of the new executable request, not obsolete local paths from earlier machines. Confirmed noncreation does not consume a generated-job slot; unknown creation blocks resubmission until reconciled.

Use `status` for first reviewed count, first usable count, first-pass yield,
unreviewed count, technical failures, known credits and unknown billing count.
PASS_WITH_NOTES counts as usable with its remaining postprocessing recorded.
Do not use the absence of a repair as retrospective proof of a formal PASS.
Persist the exact request fingerprint, attempt/job IDs, output hash, review reason
and billing event together for the next audit. The helper is a Host preflight gate;
unrelated direct provider calls cannot be intercepted by this plugin.

## Video and shared stage budgets

For a budgeted stage, use `init-stage` instead of separate image campaigns, with
`stage_id`, `authorization_ref`, `budget_credits`, `frames`, `protected_targets`.
`frames` includes compiled images or sealed video decisions. The same persistent
state owns all attempts, job outcomes, reviews and settlement, across model changes.
Before every `reserve`, pass `--input` containing `quote` and `balance`. Both carry
a current Evidence (`source`, `checked_at`, `expires_at`, `verified`). Quote fields
are `request_fingerprint`, `unit: credits`, `conservative_credits`, `uncertainty: []`;
balance fields are `unit: credits`, `available_credits`, `margin_credits` (>0).
Unknown settlement retains its reservation, including failed or cancelled jobs.
Do not create another stage/campaign file or directory to reset spending.

Use `replan` with a verified replacement `frame` and concrete `reason` after failure;
this preserves creative requirements and attempts and requalifies the changed path.
Use `inspect` for technical observations and output copies, then `review` for full
content checks. Video additionally requires ACTION, CAMERA, DIALOGUE, SPEAKER, SOUND,
CONTINUITY and ENDPOINTS. A partial observation remains PENDING_REVIEW, and technical
PASS does not adopt the video. Each video revision has a newly frozen request and
fresh quote; it is not generated by blindly appending text to the prior prompt.
For V2-07, stage limits are six total created images and two total
video attempts, including fallbacks. The Host-specific adapter guide provides the
source entry and live-loading checks. No provider calls occur inside this helper.
