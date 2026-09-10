# Video route preference

The Plugin Config loader parses `DRAMA_PLUGIN_VIDEO_ROUTE_MODE`,
`DRAMA_PLUGIN_VIDEO_MODEL_PREFERRED`, `DRAMA_PLUGIN_VIDEO_MODEL_FALLBACKS` into
`VideoRoutePolicy`. No settings means AUTO / DEFAULT_AUTO. YAML can use
`video_route_policy` with the same fields. Environment overlays Plugin defaults;
a Host-supplied typed `task_route_policy` overrides them, with TASK_OVERRIDE source.

AUTO retains V2-06 qualification, quality then cost ranking. PREFER evaluates only
preferred_model followed by the explicit ordered fallback list. PIN considers only
preferred_model; retained fallbacks are INACTIVE. Missing candidates have
NO_CANDIDATE_EVIDENCE; none of these policies admits an ineligible candidate.
Unknown keys fail at load/resolution, including inactive fallback keys. Keys are
`seedance-2.5`, `minimax-h3`, `flux-3`: the current adapter registry's model labels
normalized by its existing identity rule. This vocabulary adds no capability facts.

Host calls `choose(requirements, candidates, policy=config.video_route_policy,
task_policy=...)`; planning uses `choose_routes` and the existing `qualify_route`.
The actual `compile_video.py` supports `--plugin-config`, an optional typed
`task_route_policy` in its input, `candidates` and `host_adapters` keyed by candidate
ID (the existing singular candidate/host_adapter input still works). A provided
candidate is evidence, not implicit user PIN authorization. The compiler saves
route-policy-resolution.json before compiling the selected route. It never
uploads or submits. `route_preflight.py save-route` consumes the same parsed config
and optional `--task-route-policy` JSON file before saving a new formal plan.
Planning audit lives under existing Work productionPolicy metadata, outside canon.

Seal with the selection's `route_policy_resolution`. The existing decision
fingerprint covers effective/source/policy fingerprint, selected candidate/model,
qualification fingerprint and request. Verification uses that snapshot, never live
env. Changed preference requires a new qualification and seal; generation still
needs its exact current quote and existing stage authorization. Legacy seals lacking
policy metadata remain readable under their original contract.

An offline-only selection can retain the existing V2-12 cost-unknown compilation
exception. Its qualification remains ineligible; it emits dry_run_only and a seal
that cannot reserve/submit. It is neither a complete price nor a production permit.
No reference/capability/quality-evidence exception is introduced. Resolution and
CinematicShotSpec are independent of preference.

See [copyable settings](video-route-policy.env.example). Apply them only when the
user chooses. Do not transfer another Work's budget. PIN is recommended for a
future separately authorized controlled comparison.
