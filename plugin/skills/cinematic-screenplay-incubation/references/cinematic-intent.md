# Cinematic intent: meaning survives, execution remains open

Read for screenplay-to-scene/shot handoff or a suspected loss of cinematic meaning.
Keep a small local sidecar beside the frozen screenplay/Bible. Pin source file hashes
and exact scene/anchor locators. Do not duplicate dialogue or create a Domain identity.

## Extract and prioritize

Select only consequential POV, opening, closing, key moments, subjective moments,
visual-emotional bridges and historical constraints. Each item has a local `id`,
`sceneIds`, `kind`, `priority`, `meaning`, `why`, and `source` locator. Use one list,
not separate mandatory schemas for every kind. Record `avoid` only for real risks.
Describe whose experience, audience distance, subjective/objective relation and allowed
perspective shift in the relevant POV item. A subjective moment includes its objective
return. Preserve first/last effective perception and purpose from the existing anchors.

- MUST: losing the meaning changes drama, POV, a decisive visual cause or historical
  boundary. Implementation may change; this is not a lens, movement or duration command.
- SHOULD: a valuable emphasis with room for a better interpretation. Explain an
  alternative by the experience it preserves. An omission needs a reason and review.
- FREE: optional suggestion, freely replaceable or discardable; omission never blocks.

Do not manufacture priority for every sentence. If intent is ambiguous, resolve that
upstream ambiguity before inventing certainty. Freeze source acceptance separately
from acceptance of the new interpretation. Older sources without an intent sidecar
remain valid; extract on demand, never retrospectively invent author approval.

## Project and translate

Global Bible → Episode Working Set → Scene Working Set → Shot Relevant Intent.
Attach only items assigned to the scene; include its episode opening/closing only when
this scene actually carries that boundary. Preserve IDs, priority, source and meaning
through projection. Fetch missing relevant context rather than forwarding the Bible.
Author historical constraints remain distinct from character knowledge.

For a shot or contiguous coverage group select only current characters, state,
relationships, author constraints and applicable intent from the scene set. A subjective
return may span adjacent shots: retain the group obligation rather than forcing it into
each shot. Group review checks every assigned intent, so local selection cannot hide an
omitted MUST. Do not forward future arcs, all setups or unrelated historical evidence.

Scene development preserves the approved playable action and intent; it does not add
camera instructions. Shot design translates meaning into subject/action, blocking,
composition, camera relation, sequence, transition and continuity. Avoid copy-pasting
an intent as a shot without specifying what happens. Its existing planned durations
and canonical speech bindings remain unchanged conventions. A pretty new ending
cannot cover over a MUST closing. Do not bind explanatory epilogue text as dialogue.

## Review the complete assigned coverage

For every original item record priority → actual shot IDs and implementation evidence
→ PASS / ACCEPTABLE_INTERPRETATION / INTENT_LOSS / CONFLICT / N/A. Read the plan;
an ID link proves traceability, not preserved meaning. PASS preserves the meaning;
ACCEPTABLE_INTERPRETATION preserves it through another implementation, including for
MUST. N/A is for discarded FREE suggestions, not an escape from a MUST or SHOULD.
An omitted SHOULD records INTENT_LOSS with rationale and a conscious reviewer disposition;
it is not automatically a critical failure. Any conflict with a historical constraint
or MUST meaning blocks the group. Review subjective return, opening position and final
effective image/sound in the actual sequence, not merely their presence somewhere.

When source and intent are correct but coverage loses meaning, owner = SHOT_PLANNING.
Declare finding, priority, affected shots/continuity neighbors, unaffected screenplay/
dialogue/history, then revise only that scope and re-review the complete group. If the
source is ambiguous or wrong, route to the relevant screenplay/intent owner instead.
Use the existing maximum of two targeted rounds; do not manufacture a defect to use it.

The optional [handoff checker](../scripts/check_handoff.py) projects explicit selections,
checks review coverage/references and epilogue attribution. It cannot judge cinematic
meaning or source truth. Its record pass is not user cinematic acceptance. Review evidence
is stale when the consumed source intent or shot plan changes; retain before/after hashes
and recheck only actual consumers. No global all-to-all fingerprint cascade is required.

## Downstream boundary

Keep review records and source locators in the working sidecar. Reviewed shot action,
camera and continuity facts use existing open Shot content when persistence is requested;
do not hide a whole Bible or reviewer scratchpad there. Selected intent may accompany
the approved production context. Breathing, attention and perceptual distance remain
advisory inputs to later Visual and DPD/Audio interpretation, never new DPD fields.
This handoff does not authorize media generation or claim final audiovisual preservation.
