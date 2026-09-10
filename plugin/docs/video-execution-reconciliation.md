# Video execution contract reconciliation (V2-12)

The existing selection/production loop owns state and cost. No new Skill, service,
database or provider framework is introduced.

For `cinematic-shot-v1`, the canonical Scene words and DPD dramatic direction feed
one CinematicShotSpec. Host `cinematic_projection.project` emits readable sections
and a leaf-level destination manifest, not the whole JSON. The adapter consumes
frozen beat times; it does not design or retime the Shot. All present critical
fields must map to PROMPT, PARAMETER, REFERENCE or UPSTREAM_LOCK. Recompilation
before execution verifies the sealed projection and exact request.

`SourceSoundIntent` belongs to the director IR. REQUIRED/PREFERRED/DISABLED is
resolved against the route's sound scheme and verified node controls. Dialogue
IDs match canonical bindings. Ambient and diegetic intentions are generation
instructions, not a finishing mix. Original generated AV remains immutable.

A shared dialogue planning artifact contains a contiguous ordered group of formal
Shot projections, the canonical Scene spoken-content fingerprint and group turns.
Each turn has startMs/endMs and Host-reviewed character ranges per Shot. Replay
computes intersections with formal Shot durations; it validates exact text coverage,
order, role and estimates. Shot bindings remain text/timing-free. Full canonical
words stay upstream; only the current fragment reaches the provider prompt. The
formal Host rereads the group before production. This is planned coverage, never
measured/accepted audio timing.

`ReferenceDuty` names role, subject, exact purpose, target Shot and actual Media
identity/sourceRef/hash/MIME/slot. Core rejects missing REQUIRED duties and static
images masquerading as performance/camera references. The Host checks actual
slot wiring, local bytes, upload receipt and formal Media readback. Endpoint use
requires the observed state to match frozen Opening/Ending. Semantic suitability
is a documented Host observation; string equality does not prove pixels are good.

A reviewed EQUIVALENT may use exact frozen spatial/effect text for LOCATION,
COMPOSITION or VFX where no unique visual identity is required. Its destination
is explicitly prompt, not a fake Media. It cannot substitute for CHARACTER,
COSTUME, PERFORMANCE or CAMERA_MOTION. Existing project video input limits remain.

The existing `seal_decision` uses the single Host `execution_sealer` boundary;
Core imports no concrete provider. The Comfy Host registers that callback, like
production's existing video_verifier. The seal binds director, canonical dialogue,
references, candidate qualification, graph/schema/capability, resolution, duration,
audio and projection. A new schema cannot seal without the Host boundary.

`compile_video.py` is an offline entry only. Its dry_run_only seal can retain an
unknown complete cost, but verify_decision/production reject it for reservation.
Formal `route_preflight.py` rereads canon and Media before reservation; the generic
legacy tool and local legacy reservation CLI cannot consume new-schema requests
as a shortcut. A real paid run needs current complete price, budget, metadata and
formal input/receipt checks, then a newly sealed request on the same stage.

Current Seedance node/template facts live in Host capability evidence, not the
Skill Core. `bind_capability` pins L1 node metadata to the inspected L2 graph/schema
and original capture time. Changed or expired facts require requalification. No
global 2000-character limit remains; only a verified node max_length may reject
an oversized prompt, and no code truncates it.

Legacy VisualPerformanceBrief remains available for historical schemas. Passing
it as another execution prompt to the new schema fails; nested lineage may be
retained without being compiled. RealizedPerformanceSnapshot remains downstream
observation. No final artistic acceptance or visual quality is inferred offline.
