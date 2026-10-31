# Director storyboard and cinematic animatic

Reuse `SequencePackage` / `EditorialRhythmPlan`, source-pinned originals in
`DirectorArtifactStore`, and `PictureEditPlan`. No new author loop or business
entity is required. Host retains the choice to keep, revise or reject a study.

## Artistic preview and technical rehearsal

When a production-board study is explicitly wanted, use the shared
[expressive storyboard method](../knowledge/shared-techniques/expressive-storyboarding.md)
to make framing, contact, camera/actor/gaze/light relations and continuous nodes
readable. Choose the useful medium and layout; no nine-cell grid, line-art-only
rule or redraw-until-pass loop follows. Such a labeled diagram is a design study,
not a substitute for a cinematic preview or a finished production keyframe.

For cinematic review, default to cinematic storyboard pictures from the project's
approved image route and current selected visual designs. In the current Literary
Cinema baseline this is Seedream 5.0 Pro; video remains Seedance 2.0. This is a
project choice, not a new multi-model router or a change to provider defaults.
Read the complete selected passage and current Director choices before selecting
keyframes. Frame changes should expose changes in attention, framing, performance
or relations; neither one image per Shot nor one per action is required.

Blender grayboxes, procedural people and composition diagrams are optional spatial,
contact or occlusion studies. They are not the default artistic preview and cannot
stand in for completed cinematic images or acting. Retain historical rough studies
with their original labels; don't silently upgrade them to cinematic deliverables.

## Asset authority and image purpose

Resolve selected character, costume, location and prop designs through existing
Asset Resolution / Specialized Asset Design / Reference Strategy. Keep their
version and source evidence in the study sidecar. A previous rendered frame can
prove a depicted state; it cannot automatically redefine a face, costume, light
scheme or instrument. A rejected or unreviewed experiment is not a baseline.
New viewpoints inherit the scene's physical light arrangement, not all illumination
of an unrelated preceding image. Keep non-tail evidence's true source/time.

Art storyboard pictures use the existing KEY_FRAME intent where appropriate.
They are neither automatically formal FIRST_FRAME assets nor video references.
Only an explicit later Host choice plus existing reference resolution and official
provenance requirements can assign those uses. A storyboard selection grants no
paid generation authority, video material eligibility, or production adoption.

Retain real reference IDs/version/hash and each picture's actual request/response
when generated. Do not invent upload receipts or downgrade a missing identity
reference into an unannounced text-only recasting. If approved references cannot
fit the existing route limit, resolve the actual required visual evidence with
its owner; a group image is useful only if it genuinely proves those members.
No mandatory atlas, asset rebuild or new approval chain is introduced.

Without current spending authority or usable assets, deliver keyframe choices,
source-linked design, native compiled text where possible, unresolved bindings,
planned costs and audio needs. Mark incomplete request bodies as unbound. Do not
submit, generate geometric substitutes for that cinematic deliverable, or call that
preparation a Cinematic Animatic. An explicitly requested technical diagram study
remains possible under its own limited purpose described above.

## Picture and listening timeline

Local adapter: `shot-design/scripts/render_animatic.py SEQUENCE BOARDS SOURCES
--output DIR`, with workspace `plugin/src` on PYTHONPATH. BOARDS maps each selected
Shot key to ordered actual still attachments `{path, duration}`. Multiple panels
can depict moments within a single film Shot; panel transitions are not new film
cuts or model requests. Panel holds total the selected provisional movie time.
The adapter verifies source fingerprints/image bytes and uses the native picture
renderer in DRAFT mode. It does not author or generate pictures.

Its output is a **picture-only draft with explicit placeholder silence**. Use the
existing Sound / Music / Dialogue owners and local Finishing renderer to place
available, provenance-supported temporary voices, continuous music and ambience.
Do not burn technical captions into artwork as a substitute for hearing the scene.
Label temporary voices honestly; absence of recordings remains an audible-work
limitation, not an artistic choice of silence. Don't fabricate licensing evidence.

Music phrases and room tone can span film cuts. Choose one continuous source range
for a continuous musical event; do not restart a cue at every Shot or technical
file. Resolve changes in distance and masking through the existing sound layers.
Time dialogue by real trial delivery when available; revise provisional coverage
rather than stretching words or looping a phrase to fill a generation window.
Finishing's render-only path need not retain/adopt into formal production records.

A cinematic animatic still cannot prove natural body motion, bow/string contact,
subtle acting, lip sync or Seedance preservation. Do not describe a static image
montage as observed continuous performance. Record what was actually seen/heard.

## Revision and downstream use

Keep provisional identities as DESIGN pins, separately from CANON. Link source
excerpts, department originals, entrance/exit states and audio choices. Never
fabricate formal Shot IDs. After Host review, a changed image changes its attachment
recipe; changed camera/state/time choices first revise their professional original
and SequencePackage. Then project through existing Shot/FilmDirection and native
Prompt compilation. Image replacement alone cannot rewrite a professional choice.

Film Shot != action Phase != generation unit != adopted source interval.
Host may change the design after watching; neither diagrams, case-library examples,
fixed durations, frame counts nor a new scoring or approval gate decide the art.

## Native scene storyboard selection (P0)

Use `storyboard.source(run_id, scene_id)` to read the current Native Film coverage
as a Sequence candidate. It preserves the selected Director and Canon pins; it
never invents panels or timing alternatives. Supply useful panel nodes under the
existing film Shot keys; one panel is sufficient when it expresses the intent.
Choose meaningful stable panel keys, a current-state description and `at` (seconds
from the Shot start). `at` marks the displayed node, not measured acting time.
The next node/Shot end determines its hold. Do not provide a second timeline.
Director may explicitly select ellipsis/parallel bridges and their reasons in the
existing Sequence; no new artistic gate or continuity score is introduced.

`storyboard.select(selection, current_fingerprints, directory, run_id=...)` retains
one immutable `SceneStoryboard` in the existing creative original store, validates
the Native Film source binding, and derives a scene overview. Complete selected
images also produce the picture-only Animatic automatically. An omitted `run_id`
is an isolated design study; it cannot start production. Formal adoption is never
changed. Old Sequence and three-input CLI records remain readable.

A panel references a native compiled Frame file by path/hash. Its existing Frame
references own exact character/location/prop/costume versions, scope and usage;
the scene view only projects these fields. For new art use
`storyboard.design_frame(selection_ref, panel_key, frame, directory)` to invoke the
existing visual compiler and retain that exact request. It clears an old image
when the underlying frame changes. This is design compilation, not paid generation.
A missing image is shown as pending; never synthesize one to make the timeline pass.

`storyboard.prepare_frame(selection_ref, panel_key, child_id)` fixes a selected
panel into the existing `specialized-asset-reference:v1` Target workflow. Continue
with the existing `specialized_assets.quote_reference`, cost decision,
`resume_reference` and `review_reference` capabilities. Existing reservation,
unknown-result recovery, formal Work/media delivery and review remain unchanged.
This target uses `STORYBOARD_REFERENCE` Media purpose; asset adoption/registration
steps have no asset effect. It is not a new asset identity or production loop.
No request is made by source/select/design_frame/prepare_frame/render.

After choosing a reviewed result, `storyboard.collect(selection_ref, panel_key,
child_id, directory, reason)` binds its exact output and production original into
a new selection. Results from the same design batch can be collected successively;
an intervening design/time/source change cannot silently accept old results.
The same operation refreshes the overview and, once all images exist, the Animatic.
`storyboard.render(selection_ref, directory)` reopens that exact selection. Frozen
history is retained, never rewritten from a later head. Paid dispatch checks the
current Native Film direction, even if an older selection can still be reviewed.

For no-Work local regression, use `DramaPlugin.render_scene_storyboard` or:

```sh
PYTHONPATH=plugin/src python plugin/skills/shot-design/scripts/render_animatic.py \
  --selection /absolute/input.json --output /absolute/output
```

The single input contains `selection` and `currentFingerprints`. Outputs include
`selection.json`, `view.json`, an HTML overview and a playable DRAFT MP4. Node IDs,
film-cut markers, reference duties, continuity bridges and times come from that
one selection. Artwork is copied byte-for-byte for display. Audio remains labeled
placeholder silence; sound finishing and observed video-to-node comparison remain
separate existing-owner work, not claims of P0 dynamic performance validation.
