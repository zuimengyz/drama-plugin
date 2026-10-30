# Film World / Film Look inheritance

After the writer original, distinguish **world evidence** from **Director choices**.
World locates era/range, region and social life, inhabited architecture, season,
day/night and elapsed story time. Source facts, researched inferences, adaptation
choices and unknowns stay distinguishable in readable prose. A publication date
does not date the story; an implied country does not establish a precise city.
Literary Source Analysis supplies evidence; Director and the relevant art owners
may propose unresolved choices. Never turn a candidate into a historical fact.

Film Look is the Director's positive proposition for how this world is experienced:
viewpoint and distance, material/color relations, light quality and reach,
composition/motion, time, sound and changes across the film. Give an artistic
reason and an observable consequence. Low saturation, soft light or realism are
not defaults. Expressionist light, saturated color and unusual camera positions
can be deliberate baselines or explicit local exceptions. Knowledge helps develop
the chosen experience; it does not choose the film's style.

## Existing original and selection path

Use `screenplay.retain_context` for Markdown world/look/analysis/scene-state prose
(normally AUTHOR_CONCEPT for new creative proposals; preserve source status).
On the selected screenplay handoff, `screenplay.bind_professional_context` accepts
optional `world_ref`, `look_ref`, `analysis_ref`, `scene_state_refs` and `reason`,
alongside its existing `design_refs`. These select **one complete snapshot**;
resupply the retained world/look refs when changing a scene state. Omitted roles
in a new snapshot are not silently filled from history. The old handoff remains
unchanged. Selected does not mean formally adopted.

For a World/Look snapshot update, use the same binding tool with optional
`include_selection_changes=true` to see `{handoffRef, filmIdentityChanges}` directly;
pass `handoffRef` to subsequent tools. Omission preserves the old SourcePin response.
Read the handoff's `filmIdentityChanges` before continuing authorship:
it lists exact before/after pins as ADDED, RETAINED, REPLACED or REMOVED, including
scene states. An omitted World/Look in a new snapshot is visibly REMOVED; correct
an accidental omission by explicitly rebinding the intended complete selection.
This is an informational receipt, not another approval or production gate. It is
excluded from author views so cancelled originals do not return as creative input.

Film Look may instead use the existing structured WorkDirectingAuthority through
`design_refs`; choose one baseline, not simultaneous prose and structured look
versions. No translation to a mandatory rule table is needed for prose. Existing
inputs without these selections remain valid. If no basis is selected, Director
develops readable world/look candidates within the film treatment and makes their
uncertainties clear; missing selections do not authorize guessed exact dates.

`filmIdentity` supplies selected prose, status and content fingerprints. The
immutable handoff retains exact SourcePins and Host reason. `film_treatment`
reads this alongside the screenplay and selected structured Film Look, then
creates a readable world/aesthetic account and audiovisual narrative. It need
not duplicate every paragraph. Changing the selected basis requires a conscious
new Director selection for fresh coverage; it never rewrites old originals.

## Scene and professional use

Start scene treatment with a short readable heading: place/interior-exterior,
era if relevant, season and time window, inhabited environment, inherited look
and current sources. Then write the continuous viewing/listening experience.
This is not a mandatory form: exact unknowns remain unknown; settled film facts
may be inherited by a clear reference. Distinguish historical era, story season,
time of day, elapsed time between scenes, and sources changing within a scene.
A later season is not a new location design; dawn changes illumination without
resetting the film aesthetic. Current scene-state prose may state an authored
exception and its purpose without changing every other scene's baseline.

Shot Design carries the current viewing relation in existing Shot fields.
Camera, Lighting, Color, World/asset owners and Sound realize the same selected
place and time: camera/actor/source positions, material colors under that light,
visible spatial relations, audible activity and cut/hold conditions. Production
Design aligns those originals without reauthoring them. Preserve uncertain facts
and existing asset identities rather than inventing an era, street or window.

Only current executable consequences enter the existing owner projection and
PromptIR. World/look prose, case names, source citations and reasoning remain
upstream. A chosen color exception can be projected; schema acceptance does not
prove historical accuracy, visual consistency or artistic quality. Frozen Shots
and old tasks do not acquire a new creative backfill or approval loop.
