---
name: cinematic-finishing
description: Finish existing edited drama with scene sound continuity, local ambience repair, optional BGM and a retained derived Media. Use after picture editing when dialogue, performances and picture timing should remain intact.
---

# Cinematic Finishing

Recover the selected assembly with `work.get_work`, its actual `shot.get_shot`
and `scene.get_scene` relations, and `media.get_media` / `media.resolve_media`.
Use `media.list_media` for scoped source material discovery. Source bytes, hash,
duration, tracks, timeline and ownership must agree before editing. Preserve the
original. A filename is not selection or recovery authority.

## Scene Sound Plan

Plan the continuous dramatic passage first, independently of Shot file edges:
Dialogue; Diegetic / Source Sound; Persistent Ambience; BGM; Transition; Silence.
Give each meaningful cue a source, narrative function, passage range, entry/exit
and changes in distance, direction, spectrum or attention. One cue can cross
several Shots and adjacent Scenes. A cut does not restart or stop it. Use J/L
cuts, crossfades and envelopes only where they serve space, action or attention.
Do not mechanically loop a short vocal/music phrase to fill a longer passage.

Default priority is Dialogue > narratively important diegetic sound > persistent
ambience > BGM. Protect the actual words and synchronized action sounds. Duck
lower layers around measured dialogue, with natural ramps. Do not mute mixed
dialogue to remove an overlapping effect. Seek original tracks first; if only a
mix exists, use a localized, evidenced repair and disclose its collateral limits.
An isolated wrong sound does not justify inventing a new battle or changing story.

## BGM decision

Choose NO_BGM, SUBTLE or ACTIVE for the Scene/passage. If no concrete dramatic
function is identifiable, choose NO_BGM: this is a complete artistic decision.
Distinguish it from unavailable music. For music, state whose situation it helps
the audience understand, its entry/exit, cross-Shot scope, and how dialogue and
important source sounds retain attention. An emotion label alone is insufficient.
Do not automatically score sadness/battle, cover editing errors, or fade every
Shot independently. Diegetic singing is not automatically BGM.

Sources may be EXISTING_MEDIA or LOCAL_LICENSED with traceable usage rights;
GENERATED is a future capability seam, never an implicit fallback. Retain any
adopted local material through `media.import_media`, verify full hash/get/resolve,
then use its stable Media ID and source ranges. Missing material stops only the
dependent finishing operation with a precise source/range recovery point. It
never authorizes new picture, voice or music generation.

## Local execution and review

The Host translates the plan into a local recipe: verified inputs, source trims,
placements, envelopes, replacement windows, protected dialogue and remux. Use
the packaged `scripts/finish.py` entry and [Host contract](../../docs/cinematic-finishing-host.md).
The Core makes creative decisions; the Host handles extraction, trim, fades,
crossfade, ducking, mixing, probe and video stream copy. Verify compressed video
packets AND timestamps; a changed container hash is expected. Do not re-encode
picture as a convenience. Preserve original audio outside approved edits.

Review the full passage at normal playback, especially cue continuity, dialogue,
transitions, perspective and unwanted sound sources. Tiny noise/loudness
differences alone do not block. A major finding states observed sound/picture,
broken requirement and narrative consequence. Re-plan locally in scope without
repeated creative approval. Do not infer failure or PASS from absent evidence.
ASR, waveforms and spectral checks support localization, not listening. If the
Host cannot actually hear, keep audio review UNKNOWN and retain a clearly named
candidate; never claim final audible repair. Seek available observation first.

## Persistence and recovery

Use `work.save_work` and `scene.save_scene` to merge the current finishing
revision and references into existing content (save replaces content: preserve
unrelated fields). Keep source Media/hash, scope, sound plan, compact numeric
recipe with stable source IDs/ranges, derived Media/hash, review and userAdoption.
Local commands/PCM/probes are working artifacts, not the only recovery memory.
Keep historical revisions; changing a sealed recipe needs a new revision.

Use the shared import/get/resolve/full-hash/business-binding completion for the
new derived Media. A retained UNKNOWN candidate is not an adopted final. Host
selection and the user's eventual USER_SELECTED are distinct. Repeating the same
revision reuses the same Media; ambiguous imports are queried before any write.
Storage failure recovers identical output, never generates another picture.
Completion states exactly what was rendered, heard, verified and still unknown.
