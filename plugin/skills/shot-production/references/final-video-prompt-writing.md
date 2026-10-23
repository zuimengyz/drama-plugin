# One final video Prompt, organized by information owner

Use the existing Host final-writing handoff. Read the current screenplay, approved
shot decisions and relevant professional originals; an earlier Prompt is historical
comparison, not the source to summarize. Preserve those originals for their other
consumers. Organize current decisions directly into the modules below; omit empty
modules instead of inventing content. No extra model call, workflow or production
gate is introduced.

| Module | Sole responsibility and source |
| --- | --- |
| Context and intent | At most two concise paragraphs: present predicament, consequential relationships and expressive stakes, grounded in Work/script/Director/adjacent shots. Explain why the audiovisual design matters. Completed/future events stay context, never new shot action. |
| Reference use | Assign each actual input ordinal its information duties and exclusions. Identity/costume, spatial proof and actual action endpoint are separate uses. Never say “inherit everything.” |
| People | Stable descriptive alias, identity and necessary approved appearance/costume/material. No lighting, camera direction, incidental portrait pose or expression. Keep source names in Host records and exact speech protected. |
| Space | Confirmed world layout, fixed objects and actually adopted changes; no rearrangement to satisfy a composition. Opening pose/held objects belong to Action. |
| Action and performance | Opening physical state; causally ordered or explicitly parallel acts; receiving, gaze, listener reactions, contact/support/release, identity through occlusion, local rhythm. Keep the causal trajectory together. |
| Camera | Current approved viewpoint, side of axis, frame, lens intent, depth/focus, movement and endpoint. Same-take continuation inherits existing camera; a new cut uses its own approved view in the continuous world. |
| Lighting and color | Current scene/time's accepted sources, main/fill hierarchy, direction/quality, contrast, material/color and authored light changes. No focal length, framing or depth-of-field instruction. |
| Sound | Source, exact language/speaker/dialogue, delivery and timing/overlap, ambience, acoustic priorities, music/silence. Visual listener behavior remains with Action. |
| Ending | The existing completion/hold/cut condition and resulting state. Refer to established actions without replaying their complete instructions. Technical automatic-duration bounds appear once here. |

Joint decisions live once in the most suitable module: for example, a prop's
support transfer and the actor's reaction remain together in Action; Camera can
specify visibility of that contact without repeating its mechanics. Merge
synonymous requirements while retaining their different triggers, scopes,
exceptions and negations. Neither copying every original field nor semantic
compression of a completed draft is the writing method.

## Inherit by information type

- Approved assets/current design own identity, costume and intrinsic material.
  Incidental reference expression, pose and illumination apply only when assigned.
- Confirmed layout plus adopted actual changes own space/fixed objects. The
  preceding accepted actual result owns only the opening state it can establish;
  never substitute its planned endpoint or an old portrait pose.
- The accepted scene/time aesthetic owns light/color/texture. Later output drift
  does not become the baseline. Retain an explicitly designed local light change
  where present. Identify the exact baseline source in Host metadata, not local
  shot names in model prose.
- Current approved Action/Performance/Editorial/Sound own the intended acts,
  simultaneity, dialogue and ending. Brevity does not authorize changing them.

Resolve conflicts by these responsibilities and existing explicit decisions. If a
concrete gap remains, name it in the report; no template default or new gate.

## Existing native handoff and review

Retain the Host-authored `FinalPromptWriting` in the existing generation artifact
store and pass its reference as `GenerationTask.finalWritingRef`. Its paragraphs
are sourced to professional execution fact IDs and, where needed, exact supporting
source refs; its pin is the selected IR fingerprint, **not an old final Prompt**.
Multiple facts may share a single expression. `HOST_MAPPED` is a Host semantic
judgment with a final span, not automatic proof of equivalence. For exact speech,
place `{{speech:<execution fact ID>}}` in Sound; the existing audio owner inserts
the unchanged line, language and speaker. Canonical `{{actor:<subject ID>}}`
tokens resolve to this request's subject bindings. Descriptive aliases remain
stable across shots; input ordinals retain their assigned duties.

The existing compiler serializes these modules once. It adds only actual endpoint
reference labels and technical duration syntax in their own modules. It never
renders a full baseline first, rewrites a sealed draft, appends original leaves or
selects a shorter variant. Without Host writing, selected leaves remain literal
in the same module layout; this is not a substitute for Host semantic integration.

Use the existing complete-request review: compare professional decisions to final
module/span, then inspect the serialized provider body for omissions, conflicts,
names/local labels outside protected speech, duplicate additions, reference
order/roles/hashes and unchanged API parameters. Check concurrency and support
transfers as relations, not merely keywords. Correct the owning module and compile
the whole draft again. Do not append historical fixes or post-process the result.
Character count is an observation, not a target or permission to drop design.
Offline textual checks do not validate video performance, lighting or sound.

The former `promptExpressionRef` baseline/compression compiler is retired. Its
schema remains only to read frozen historical records; new compilation does not
execute it. There is no compression fallback under another name.
