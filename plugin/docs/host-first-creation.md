# Host-first creation and screenplay continuity

The Host coordinates authorship, review, reconciliation and adoption. When the
configured FormalCanonAuthor or FormalDirectionAuthor is called, retain its actual
input/output and identify that independent author; do not label it Host-written.
When the Host writes a body itself, record that separately. Project permission,
creative preferences, professional context and user feedback reach the real author
through explicit `authorContext`, with source/version evidence retained by the caller.
Methods are advice, user boundaries remain binding, and old production choices do
not become permanent constraints. The author chooses substantial story and form.

## Actual entry and timing

`DramaPlugin.screenplays` is a small facet of the existing Target Creative Engine.
Its `screenplay.*` tools are registered on the real Plugin ToolRegistry and use
`CreativeVersionStore.objects` / `DirectorArtifactStore`. There is no new Host,
Runtime loop, database, model provider or production gate.

For a new complete film or a scene in an existing film:

1. Resolve current designated source and existing adopted facts. Retain exact
   context originals with `screenplay.retain_context`. Their status is source
   metadata supplied by the caller, not a new adoption decision. Existing source
   and rights authorities still govern formal writes and production.
2. Call `screenplay.begin`. A scene includes the **complete film framework**, not
   only neighbors. Pass project-specific `author_context` with adaptation authority, creative
   preferences and selected professional guidance. Do not silently inject old
   candidate solutions; supply them only when explicitly relevant and labelled.
3. Write the whole film/scene and call `screenplay.retain_v1` with its exact text.
   The text is immutable. A complete scene has action, interaction, speech or
   silence and an internal dramatic history; it is not an outline or shot list.
   Storage validates identity and nonempty bytes, not artistic completeness.
4. If useful, request selected specialties with `screenplay.support_packet`.
   Invoke existing professional Skills/agents on that exact original and source;
   retain their real contributions with `screenplay.retain_support`. Independent
   AIE criticism is advice. There is no mandatory department list or defect quota.
5. The Host reads original and advice, then calls `screenplay.decide`. `KEEP_ALL`
   selects the exact V1 reference and needs no substitute body. Other choices
   retain a new complete version. Record meaningful gains and losses, including
   a rejected local recommendation; no agreement or actual change is required.
6. `screenplay.shot_handoff` supplies the selected full body, exact reference,
   full-film/long-arc context and Host decision to meaningful precision work.
   It is explicitly **TEXT_DESIGN_ONLY / AUTHOR_CANDIDATE**. A proposed scene
   change returns to the Host. Formal production still requires the existing
   exact adopted Scene/dialogue/source/version route; selection is not adoption.

Expected session revision provides ordinary write-conflict protection. It is not
an artistic gate. There is no automatic specialty dispatch, revision, approval,
score or production advance in this facet.

## Existing automated native author paths

`FormalCanonAuthor` supplies the autonomous creation instruction and preserves the
explicit authorContext through native film and scene calls. `film_treatment` on the
existing FormalDirectionAuthor writes a complete director treatment before formal
Shot projection; proposed screenplay changes return as feedback for reconciliation.
For a new work, the single-scene and complete-film capabilities first request a
free whole-film body, retain it verbatim, and request the same writer's revision decision in a
separate call. Only afterwards does the existing Canon author derive the structured
Work, Script and Scene records. The selected `Script.screenplay` must match exactly;
a different body is rejected before the formal version is written. There is no
first-draft Work interpretation or Scene inventory schema in the free-body call.
An explicitly selected Host session can be bound using `screenplay_session_id`
on `create_film_run` (scene) or `create_source_film_run` (film). The complete selected
text, original context, Host decision and candidate status reach `author_payload`.
Binding freezes the exact handoff; later Host session decisions do not alter an
existing run. Default relevant memory is likewise pinned at creation, not reloaded
from a mutable index at each recovered author call.

An existing complete film original can likewise be retained and selected; an
already adopted film framework stays the formal source. Before formal Direction,
the default formal author writes a complete independent
scene original from the full-film framework, preserves it, then makes a separate
author revision decision. The Host must identify this as model-authored selection;
formal adoption and human-delegated creative coordination remain separate. This also runs when an existing adopted Scene skipped Canon
creation. Full-film Direction receives all selected complete scene bodies. Explicit
scene sessions reuse their chosen text exactly. These bounded text author calls
reuse the existing author/backend and capability; they add no Runtime loop or
production gate. This batch port requests no independent advisory research; richer
Host-requested support uses `screenplay.*` before binding. Formal department records
still use exact Canon identities/dialogue. Candidate new facts or lines require
existing adoption before production; prose cannot promote them by being bound.

Custom injected author ports remain compatibility ports and do not impersonate the
formal autonomous author. Old persisted runs without a screenplay ref remain
readable; new runs capture the creative context in their existing input record.
No provider, compiler, paid execution, recovery or Runtime-core behavior changes.

## Long-arc memory

`screenplay.retain_thread` stores a light source-pinned narrative original and a
reference-only index beside the existing artifact objects. It can connect any
scenes, e.g. 2, 7 and 12, contain no scheduled payoff, and develop later. It does
not require every question to be answered or insert motifs to satisfy a test.

`NarrativeThread.status` separates ADOPTED_FACT, AUTHOR_CONCEPT, OPEN_POSSIBILITY
and OBSERVED_RESULT. An adopted/observed thread must consume source originals of
that same status; candidate context cannot promote itself. Observed originals
require observation evidence. These are bounded source records, not proof of
semantic truth or a substitute for current authority/actual media observation.

`screenplay.begin` selects memory by current scene membership, author-requested
tags or explicit thread refs. It has no adjacent-scene restriction. Earlier author
concepts and open possibilities are explicit opt-in, grouped by status, so a new
original does not silently receive an old solution. A Host's selected unadopted
full-film framework may be included as its framework; it remains AUTHOR_CONCEPT.
Callers resolve fresh source authority before retaining context. A pin proves
exact bytes, not that an external Canon head is still current.

V1, support, decision, later versions and memory are separate objects. New
associations remain possibilities until the existing owner actually adopts them.
For a reused thread key the index selects its latest immutable account within each status by default; a candidate cannot supersede an adopted fact. Older originals remain accessible by explicit reference with `current=false`. The index imposes neither full-history loading nor a compulsory return scene.

## Professional and production boundaries

Literary, acting, cinematography, art, sound and editorial knowledge remain intact.
Their formal department outputs retain existing ownership and execution contracts.
Those restrictions do not forbid the Host from imagining performance or sound/image
relations in an autonomous screenplay body. Support can challenge the whole idea;
its argument and cost go to the Host, rather than automatically replacing it.

Cross-scene/full-film changes are proposals with affected source versions. Never
overwrite adopted screenplay, Scene, assets or historical media through this facet.
Use the existing authorized adoption mechanism later; no new Canon object type or
hard evaluation gate is introduced. User artistic acceptance stays separate from
local text judgment and technical validation.
