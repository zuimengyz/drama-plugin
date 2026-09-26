# Screenplay playability and exact dialogue (R2)

Literary meaning is not playable direction. Preserve meaning in character, conflict,
structure and subtext; give each important actor/Beat a plain-language objective,
obstacle, action toward a person/object, current performance state, turn and reaction.
Emotion alone is not an objective or action. Do not invent a motive from an adjective.
A literary phrase may remain if its visible/audible carrier is clear; otherwise the
screenplay/performance owner designs that carrier from approved meaning. Missing
meaning returns upstream, never to a Prompt Generator for completion.

## One authority and existing contracts

Screenplay authors the source intention. `SceneDPD` / `BeatDPD` / `LineDPD` remain its
single source-bound performance interpretation. Objective, target, tactic, subtext,
obstacle and turn reuse those fields. `BeatDPD.playability` adds source scene hash,
exact carrier excerpt, existing `ObservableAction` values, CURRENT_BEAT performance
state, observable reaction and author review evidence. It is not another psychology
Bible or character identity. Keep physical expression under Performance, spatial paths
under Blocking, force/contact mechanics under Action. Technical Camera and Lighting
instructions stay in their departments. No precise joint angles or default durations.
Director still owns global emphasis, tradeoffs and arbitration.

`Scene.content.spokenContent` is the single exact dialogue authority: existing id,
speakerKey, text, intent, performanceIntent (delivery), plus an explicit current target.
DPD references that id; `LineDPD.playability` pins exact UTF-8 text hash, literal meaning,
speakability review, fragmentation mode and its dramatic purpose. Subtext remains DPD
and is never spoken automatically. Do not copy rewritten speech into a performance field.
Missing target/intent/delivery/subtext is UNRESOLVED for new formal production.

## Author review before mapping

Read each line aloud against its body state: is the information too complete, is an
author explaining through the character, are address and giver/receiver clear, does
punctuation change meaning, can the fragmented words still communicate the intended
request? Record concrete evidence, not a bare PASS. Stammering and interruption are
allowed. “妈妈……先生，妈妈……” fails AMBIGUOUS_DIALOGUE: naming mother and stranger
alone conveys no request. An intentionally unintelligible line requires the explicit
`INTENTIONALLY_UNINTELLIGIBLE` purpose; it is not a general escape for poor dialogue.
The R2 S02 request must actually communicate mother-in-trouble and follow-me.

## Runtime handoff and adoption

Use `map_screenplay_performance(scene, scene_dpd, beats, lines)` before handing source
intent to Performance/Blocking/Action. It returns existing DPD and exact source speech,
never completes or rewrites either. Formal Performance Book validation now requires
these witnesses for all bound actor beats and spoken lines. It compares current Scene
and text hashes, speakers, targets, source intent and action carriers. Structural checks
cannot prove literary quality: author review evidence and human creative review remain
necessary. Do not claim a regex understands all ambiguity or speakability.

Missing fields are UNRESOLVED and return to Screenplay/Dialogue/Performance owners.
Legacy snapshots omit absent playability and remain replayable with unchanged hashes;
they cannot pass new formal production review without source-bound re-authoring.
Local screenplay candidates use local role labels, are DESIGN_FIXTURE_ONLY and do not
update adopted Work/Scene/Speaker identities. After creative adoption, bind real formal
ids and recompute fingerprints; never relabel a local candidate as formal production.

Keep the readable screenplay free of intent headings. Store structured intent in its
source-pinned sidecar. Approved exact dialogue cannot be rewritten, completed, joined
or summarized by Performance, TTS, native audio, subtitles, audio checks or Prompt
Generators. An authorized screenplay revision is a new candidate with new hashes,
not a downstream repair. Existing separately approved language adaptation stays a
separate upstream workflow; never silently use it to alter the bound line.
