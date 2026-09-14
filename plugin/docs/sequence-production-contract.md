# Sequence production package and whole-film evidence

A sequence is a production scope over existing Scenes and Shots, not a new Canon
entity or Skill. The Host coordinates existing owners. Shot-design owns coverage;
production-design owns stable design; cinematic-direction owns per-shot execution;
asset-resolution owns identity and durable references; finishing owns the actual
edit and sound. `contracts/sequence.py` composes their decisions without becoming a
second screenplay, asset database, model selector or approval authority.

## Compose before spending

Read current sources and pin their full-content hashes. Use `SequencePackage` to
join the existing EditorialRhythmPlan to ordered storyboard cards, Bible indexes,
Scene geography and one ClipBridge per adjacent pair. A card may be a proposed
subshot of an existing formal Shot: retain sourceShotId and keep it RECOMMENDED
until the appropriate formal coverage change is authorized. It does not create a
new Shot just because its local key differs.

Character, Location, Prop and optional Creature Bible entries index current source
references, stable invariants, scene-state variables, required interactions,
reference duties and unknowns. They do not duplicate approved identity authority.
A horse may need rider contact, load, gait and tack continuity; that does not imply
fantastical creatures in a historical Work. Geography describes paths, entrances,
obstacles, sightlines, scale and the relation between world axis and camera view.
Design assumptions remain distinct from Canon and measured historical geography.

A bridge names what the outgoing image/action/sound leaves for the incoming view.
For continuous action, compare the declared carried state keys: owner of a prop,
support foot, direction, gaze target, costume/damage, physical position or attention.
Use only relevant keys, then review their semantics. String equality checks alone
cannot prove real continuity. A time or space ellipsis explicitly explains its
jump; it must not accidentally carry continuous sound or imply adjacent geography.
Motion, visual and audio bridges may be deliberately absent with a reason. Never
force an occlusion wipe, matched object, J-cut or camera move onto every boundary.

`sequence.sequence_handoff` checks current source fingerprints and produces a
sealed, portable package. Missing assets and approval questions remain unresolved;
a designReady result grants **no** generation or adoption permission. Existing MCP
route, capability expiry, budget, input fulfillment and user casting approval still
apply. No Desktop fallback or new Provider-control schema is introduced.

Storyboard cards should provide enough information to stage action, not only make
attractive stills: goal, spatial relation, initial action, changed condition, camera
reason, final action and usable edit handles. Board files and source Media are
referenced when they actually exist; do not create every angle as a default.

## Execute the reviewed picture edit

Reuse `PictureEditPlan` and `production_design.picture_edit_handoff`. The local
`scripts/edit_picture.py` in cinematic-finishing calls `hosts.picture_edit`:

```
python skills/cinematic-finishing/scripts/edit_picture.py PLAN.json SOURCES.json \
  --current-canon-fingerprint SHA256 --output CANDIDATE_DIRECTORY --fps 24
```

The current bounded implementation supports equal-size, square-pixel sources with
one picture and one audio stream, hard picture cuts, and synchronized native audio
trims. It rejects unreviewed plans, changed hashes/Canon/duration, extra tracks,
mixed geometry, rotations, missing audio and conflicting retained output. It makes
a new H.264/AAC candidate; picture re-encoding is explicit. It cannot perform J/L
sound edits, dubbing, stabilization, color grading, retiming or visual repair.
An `audioCarry` creative instruction is **not executed** by this renderer: when a
plan requires a sound bridge, retain that obligation for the existing finishing
recipe and do not claim the picture assembly is the finished sequence.

The Host must verify current business ownership before supplying local paths.
Rendering records source/recipe/output hashes and measured duration; it never saves
Work/Shot/Asset or imports Media. Before formal delivery, use existing
`complete_retained_media` import/get/resolve/full-hash/business binding. Recover a
successful render from its journal; corruption or incomplete persistence does not
authorize generation or overwriting the retained result. Sound finishing keeps its
existing packet-preservation contract for the newly edited source.

## Whole-film review and repair

`FilmReview` pins exact rendered bytes and measured duration. Record normal-speed
AV observation ranges, observer and evidence. Extracted stills, waveforms, ASR,
technical decode and isolated key shots are useful evidence with different modes;
none satisfy full normal AV observation. Tool limitations remain UNKNOWN, including
when the Host cannot hear. A review record is an accountable observer statement,
not a machine's proof that the statement is true.

Review story/payoff and rhythm, then space/continuity/performance and sound across
the complete scope. FilmFinding includes time range, concrete observed defect,
narrative consequence, responsible owner and bounded repair. Repair the first
material audience-facing failure; do not regenerate a whole sequence for a local
problem. Recheck the repaired passage and affected neighbors, then review the new
complete output. Changed output hash invalidates old final review. A major finding
cannot be resolved without recheck evidence. Generation repair still requires the
existing generation permission and technical/artistic retry rules.

`film_review_verdict` will not report content review complete without full normal
AV coverage, positive domain reviews, resolved major findings and verified durable
persistence. User adoption stays separate. A production supervisor is this Host
responsibility and evidence loop, not a new creative Skill or automatic approver.
Genre preferences remain optional project profiles; shot counts, long takes,
color palettes and attractive faces are not universal platform quotas.

## Production Design Freeze and executable closure

`contracts/production_freeze.py` is an immutable sidecar, not a new business
entity. Its typed CinematicStylizationPolicy distinguishes historical plausibility
from modern screen idealization without universal beauty scores. A Freeze fixes
scope, revision, source lineage and all production-critical duties: character,
costume, faction, location, prop and optional mount/living asset. Requirements are
scope-specific; an interior dialogue does not need a horse. A selected optional
entry is still pinned and changes require resealing.

Each REQUIRED entry needs the current Asset ID/content hash and explicit
USER_APPROVED evidence. If its execution duty needs real visual Media, Media ID
and verified byte hash are also required. Text knowledge may be frozen without
Media only when the actual duty is text-only. HOST_WORKING_REFERENCE, candidate
review PASS, PROJECT_DERIVED and a portrait's existence do not prove user approval.
Do not infer a new casting approval from a legacy formal Character's existence.
The Host resolves fresh Asset/Media/approval evidence; the pure gate cannot
authenticate fabricated approval assertions. Byte verification remains the existing
asset-resolution / Media completion responsibility.

`SequencePackage.productionDesignFreeze` pins snapshot ID and full canonical hash.
Changing face, references, costume, source revision, approval or scope invalidates
old preflight; do not refresh old execution text silently. `executable_sequence_handoff`
checks sources, seal, clip requirements, receiver coverage and mount Bible use,
then reports independent states: designReady, productionDesignComplete,
generationAuthorized, produced, reviewed and userAdopted. Bible visual unknowns
may coexist with executable blocking design; actual incomplete choreography stays
in receiver/package unresolved. Even a complete design and complete freeze grant
no spending or adoption permission.

Executable ShotReceivers retain continuityIn/Out and add ProductionClip: purpose,
new information, blocking, typed ActionChoreographyBeat, camera, Bible Asset refs,
REQUIRED/OPTIONAL/NOT_APPLICABLE ReferenceDuties, audio obligations, edit boundary,
generation group, observable acceptance and fallback. Action connects approach,
orientation, weapon/contact, force, target/mount response, changed space, follower
opportunity and the next receiver. MountInteraction keeps identity/scale/tack,
rider/terrain/other-mount contacts and continuity state in the existing Bible.
These are directing semantics, not a physics engine or evidence of generated motion.
Sound carries and J/L candidates remain obligations for finishing, never executed
by a text package. Acceptance is UNKNOWN until actual evidence permits PASS,
PARTIAL or FAIL; no automatic aesthetic score.

Run the packaged offline entry with the four named paths:

```
python skills/shot-production/scripts/sequence_preflight.py \
  --package SEQUENCE.json --freeze FREEZE.json \
  --current-evidence CURRENT.json --output HANDOFF.json
```

CURRENT contains sourceFingerprints and freezeEntries resolved for this scope.
An artifact is a dry-run snapshot; formal execution must refresh the business
sources and verified Media. For formal Sequence submissions the Host MUST enter
`hosts.sequence_execution.invoke_sequence_reserved`, including retries/resumes,
not call the single-shot submit helper directly. It checks the freeze BEFORE
MCP discovery, submission claim or invocation, then delegates to existing
`mcp_execution.invoke_reserved`; existing route, projection, expiry, quote,
reservation and paid-scope checks remain in force. SequenceRequestBinding pins
package, freeze, clip and the exact projected provider request hash. Recompile and
rebind when any changes; never attach a new package to an unrelated old request.
This is the Sequence Host entry, not a change to legacy Shot ledger history or a
new backend authorization service. The MCP adapter remains the only execution
transport; there is no Desktop fallback. Provider-specific projection limitations
still require replan, not omission of REQUIRED duties.

After real output, retain its exact Media ID/hash and create FilmReview for those
bytes. No design readiness flag, contact board or still-image review can satisfy
normal-speed AV coverage or user adoption. Preserve the existing finishing/QC gates.
