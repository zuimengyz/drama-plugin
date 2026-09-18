# Visual Route v1 — additive creative sidecars

`visualRoute` is `live_action_realist` or `stylized_cinematic_cg`. It is the chosen visual language, not the existing provider/input route, casting proof order or a business entity. V1 is a design-only extension: it supplies deterministic resolution, casting projection, generic creative handoffs and read-only Asset discovery. It does not implement an approved CG production run or inherit adoption.

`contracts/visual_route.py` exports ProjectVisualRoutes, SequenceVisualRoute, ResolvedVisualRoute, RouteStyleContract, RouteContext and RouteCastingContext. Unknown fields/unregistered plain route names fail. Explicit provider:<mode> design routes are permitted with PROVIDER_DEFINED medium; no provider call or support is implied. Project defaults to live_action_realist and enables only that route until explicitly configured. A project can enable both while keeping its existing default. Sequence override names Work and sequence, requires a reason and must select an enabled route. There is no global config write.

Resolve project → sequence using `visual_route.resolve_visual_route`. One concrete clip has one route. For a side-by-side comparison create separate sequence keys referencing the same narrative source. Same-route settings may share style resources; each resolved snapshot pins project/sequence revisions. A changed context makes previous packets stale for new use, without changing those packets or their original approvals.

`RouteStyleContract` separates casting criteria, shape language, material/palette, camera, performance, historical boundary and forbidden drifts. Medium must match route. These are authored route-specific choices, not a list of IP styles or psychological anatomy deductions.

Use `skills/performance-casting/scripts/casting.py compile --route-context context.json` for route-bound authored profiles/plans. Profile identity, profile fingerprint, plan fingerprint and style route must match. The original compiler still handles source pointers, discriminants and proof responsibility. The route projection preserves exact discriminants and adds declared style duties. Output includes visualRoute, route, routeStyleFingerprint, routeContextFingerprint and routeStageConditionsFingerprint. Caller must keep route metadata with request/review evidence. `check-projection` verifies exact final pre-provider text. Without --route-context the old path returns identical content and hashes. No default field was added to old RoleArchetypeProfile, VisualCastingPlan, CharacterVisualSpec, CinematicShotSpec, DPD, LiteraryCandidate or their approved serialization.

V1 route-aware casting compile is SEARCH/DESIGN_DRY_RUN, not production eligibility. Legacy selection and brief CLI modes reject --route-context rather than ignoring it. Actual future route-specific stage reviews must carry both old proof evidence and the route context/conditions fingerprint; a prior live-action review cannot qualify CG. Formal paid integration is gated by the existing ProductionDesignFreeze and provider route qualification, not this dry-run helper.

`bind_route_artifact(payload, context, responsibility=...)` returns a separate DESIGN_DRY_RUN wrapper for CASTING / ART_DIRECTION / CAMERA / PERFORMANCE / AUTHORIAL_PRESENTATION. sourcePayload is a deep copy with its own fingerprint. Even an approved source is not an approved adaptation: productionAllowed=false and approvalTransferAllowed=false. `verify_route_artifact` verifies exact source, style, context and seal. `check_sequence_routes` rejects changed context, cross-work/sequence input and mixed routes. This wrapping operation is not a substitute for the underlying design/cinematic/literary owner's validation.

`discover_route_assets` filters already retrieved Asset snapshots by Work and content.visualRoute. `search_route_assets` uses only the existing asset.search_assets read tool. Untagged legacy records are returned separately for provenance review and never implicitly match CG. Same-route matches still need role, source, quality and approval review. Tags alone cannot prove a model's look or authorize use. Textual/historical materials may be reused as shared sources after reading; their visual references are not silently restyled.

For future authorized retention, use existing Asset/Media envelopes and search-before-create. A new route-specific design gets a distinct semantic key, e.g. production-design/<role>/stylized-cinematic-cg/<revision>, and content.visualRoute plus source references. Keep existing live-action Asset IDs/referenceMediaIds/approval fields. Never save a CG variant over an old Character to make discovery easier. No migration, table, tool or global route is added by this extension. V3-02 retains sidecars locally only.

Offline entry:

```
python skills/production-design/scripts/visual_route.py schema --output schema.json
python skills/production-design/scripts/visual_route.py resolve --context context.json --output route.json
python skills/production-design/scripts/visual_route.py bind --context context.json --input design.json --responsibility ART_DIRECTION --output handoff.json
python skills/production-design/scripts/visual_route.py discover --context context.json --input assets.json --output discovery.json
```

Authorial Gate and Literary Craft remain route-independent. Bind presentation requirements separately; never turn NO_AUTHORIAL_INTERVENTION into text eligibility, count unadopted alternatives as uses, or relabel original text as historical because it is rendered on a stone. A visual coda must preserve the same canon discipline.

Additional configurable design media: stylized_animation / DESIGNED_ANIMATION, hybrid / HYBRID; provider:<mode> / PROVIDER_DEFINED. Existing two-route performance/execution adapters remain separately gated and cannot silently map an unsupported route to realism or CG. All selections remain Work/Sequence scoped; defaults unchanged.
