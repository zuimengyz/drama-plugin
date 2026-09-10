# Cinematic finishing Host contract

This opt-in finishing layer extends the existing audio layer; exact-text speech,
native AV selection and earlier assemblies retain their existing authorities.
It neither calls a generation provider nor revises Dialogue.

Run `skills/cinematic-finishing/scripts/finish.py --help` using the existing
Python runtime. `render` reads a recipe and a local Media-ID-to-path map;
`retain` uses the configured public service adapters; `recover` starts from a
Work and revision and downloads its verified source/derived references.

Recipe version 1 uses **container seconds**, not frame-relative Shot seconds:
`revision`, `workId`, `sourceMediaId`, `sourceHash`, `sceneIds`, `scope`,
`soundPlan`, `sources` (Media ID/hash), `protectedDialogue` (start/end),
`patches` (start/end/fade, donor mediaId/sourceStart, gain, evidence),
`layers` (mediaId/sourceStart/duration/start, gain points in relative seconds,
optional lowpassHz), `review`. SoundPlan includes `bgm.decision`, purpose and
source availability, persistent cues and limitations. BGM layer roles must
agree with the decision; GENERATED is not executed by this entry. External
LOCAL_LICENSED material must first become a formal Media with provenance.

All numbers are finite and ranges refer to probed streams. Patches replace only
non-dialogue windows with complementary ramps and continuous donor audio.
Layer envelopes implement perspective and ducking without tying sound cuts to
Shot boundaries. The Host chooses cues/ranges; code does not adjudicate art.
No looping, source separation or unheard listening claim is supplied implicitly.

Artifacts contain exact filter graph/command/probes and output fingerprint.
Formal Work.content.finishingRevisions keeps the compact recipe without machine
paths, its digest and delivery. Scene.content.finishingReferences points to the
Work revision and Media. The common Media completion performs import/reuse,
get/resolve/hash and business binding. A retry reconciles those same references.
Revision identity conflicts fail instead of silently overwriting old outputs.

The renderer only copies video packets; it also compares their per-packet hashes,
PTS/DTS and duration before accepting output. Technical decode/peak checks do not
equal listening. Retained candidates keep userAdoption=PENDING, even when the
source picture was previously approved.
