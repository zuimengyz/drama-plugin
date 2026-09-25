# Professional creative departments

The professional registry in `drama_plugin.professional` is the routing and authority map. The typed Bible/package contracts are in `contracts.professional`; the local artifact/Host entry is in `hosts.professional`. A Skill is a creative method; its tool list is not permission to invent another department’s output. Director chooses intent, priority and acceptance, requests the missing specialty, and reviews its original. The Host exposes Department, Task, Status, Dependency, Output Ref and Validation Status rather than a single Director DONE flag.

## Originals, scope and authority

Historical Research owns facts and uncertainty; Adaptation Boundary owns their permitted dramatic use. Story, Character, Scene and Dialogue own narrative decisions. Director Vision owns film interpretation, tone, emphasis, restraint and rhythm intention. Visual, staging, camera, audio and editorial departments own professional implementation inside those constraints. No creative owner may upgrade evidence, rewrite locked dialogue, or silently change another department’s records. Director arbitration returns a revision to the owner instead of editing that owner’s Bible.

Every Bible has a stable ID/type/version, Work/Script/Episode and relevant Scene/Shot scope, source refs, dependency refs, status, creator capability, approval evidence, content, continuity refs and timestamps. Records distinguish archival `MIGRATED_FROM_R1`, active `NEW_PROFESSIONAL_ELABORATION`, and deterministic `SPECIALIZED_ASSET_PROJECTION`. Old visual writers reject active authoring; archival validation does not authorize production. A migrated field cites its existing original; elaboration explains how it develops an existing intention without changing causality. `NOT_REQUIRED` requires a reason and is preferable to invented work. Contract validity, semantic design review, user approval, media observation and production authorization are separate facts.

The DirectorPackage indexes originals. SceneAssembly references dramaturgy, dialogue, characters/states, environment and the participating departments. ShotAssembly carries purpose, subjects, start/end states and specialist refs. Neither assembly copies full faces, costumes, sets or sound designs. Canonical legacy Scene/Shot content and old composite schemas remain readable; their compatibility storage does not grant new creative authority.

## Department topology

| Group | Independent creative owners | Deterministic responsibility |
|---|---|---|
| Historical | historical-research; adaptation-boundary | historical-entity-registry resolves identity only from explicit evidence |
| Screenwriting | story-architecture; character-dramaturgy; scene-development; dialogue-design | canonical source bindings and immutable migration comparisons |
| Director | director | package indexing and scoped request state |
| Art | specialized-asset-design; look-continuity; prop-design; animal-design | runtime-visual-medium; global-visual-style; read-only character-art / costume-design / environment-design / environment-art / set-decoration projections |
| Visual supervision | production-design | alignment report indexes findings; professional judgment remains in the skill |
| Staging | scene-layout; blocking; dramatic-performance-direction; action-choreography; battle-crowd-choreography | zone, path and dependency checks |
| Cinematography | cinematography; lighting-design; color-design; shot-design | CinematicShotSpec compatibility projection |
| Audio | voice-direction; voice-identity; diegetic-vocal; sound-design; music-direction | exact speech binding and approved request compilation |
| Post | editorial-design; vfx-planning; color-grading; graphics-design | measured conform and observation evidence |
| Production planning | asset-planning; reference-strategy; clip-decomposition; video-model-selection | prompt-compiler and provider adapters |
| Continuity / QA | owners submit state changes and semantic reviews | continuity-supervisor; historical, visual, performance, AV and spatial QA |

Specialized Asset Design owns concrete character, costume and environment decisions. Character Art, Costume, Environment Functional/Art and Set Decoration retain separate read-only projection schemas for downstream consumers. They cannot author competing designs; `SPECIALIZED_ASSET_PROJECTION` records are replay-validated against the exact specialized original. Hair/makeup/injury are state-bearing Look decisions rather than loose scene adjectives. Props supply objects; Animal Design supplies living mount identity. Scene Layout places things; Blocking moves performers; Action supplies body/contact mechanics; Battle/Crowd supplies group causality. Performance owns expression; Voice Direction owns how exact words are delivered; Voice Identity persists across delivery changes; historical vocal mode/composition uncertainty belongs to Diegetic Vocal, never BGM.

Production Design coordinates and evaluates visual coherence. It cannot become a new container that secretly authors the originals. Color Script develops narrative palettes; Grade defines final matching/tonal intent, with actual correction dependent on footage. Shot Design covers an event; Editorial owns cut, hold and compression decisions. Finishing consumes these decisions against measured media.

## Dependency and revision

Use the registry’s actual DAG rather than assuming every department can work immediately. Evidence precedes boundary and narrative; Director Vision constrains implementation. Functional Environment precedes Environment Art and Layout. Blocking and physical object requirements precede complex Action. Camera consumes staged action; Lighting consumes Camera and Art; Color consumes lighting and visual intention. Shot coverage consumes Camera, Blocking and Action. Dialogue and Performance precede Voice Direction. Sound consumes physical action/environment. Editorial consumes shot/performance/sound/music decisions. Continuity aggregation and QA examine the package before production planning.

These are authored dependency edges, not a rigid all-skills pipeline. A narrow request loads only necessary owners; a full package must give every required department an output or explicit `NOT_REQUIRED`. Artistic iteration does not require cyclic artifact dependencies: a revision pins the prior approved input and produces a new version; downstream consumers become stale until reviewed. Production Design alignment can review new Color versions without becoming Color’s author.

A failed prerequisite returns the missing department and expected artifact. Final action cannot assume missing Blocking, and final Environment Art cannot invent missing topology. Feasibility findings never authorize provider-driven creative rewriting. Rework remains scoped to the owner and affected dependents; unrelated creative originals remain unchanged.

## Continuity and QA

Continuity is a shared structured ledger of entity/domain/property/state with effective_from, effective_until, changed_by, Scene and optional Shot refs. Track character, art, costume, hair, makeup, injury, prop/weapon, animal, environment/dressing, spatial, lighting/color, time/weather, army strength and audio state. A repair needs a cause; temporary securing is not full restoration. The aggregator may flag gaps, overlap or unauthorized changes but never invent a repair event. Departments, thin assemblies, compiler and future observer bindings consume the same ledger.

Historical, visual, performance, AV and spatial validators combine deterministic checks with separately recorded semantic findings. A text-only package cannot prove face fidelity, lip sync, actual sound or artistic execution. Preserve `UNKNOWN` for unobserved media. Evidence-bound failures route to the responsible owner; no QA gate silently modifies art or story.

## Why Skill, module, validator or aggregator

A Skill exists where there is an independent professional judgment, reusable output and repair boundary: how a face reads, how a tent feels occupied, whether a grip can lead to mounting, or when a cut should wait. These are not schema fields masquerading as professions. Alignment is likewise judgment and retains the existing Production Design skill.

Entity indexing, source hashing, dependency ordering, package storage and provider request formatting do not invent creative choices, so they are modules. Continuity merges authorized state changes and exposes conflicts, so it is an aggregator. QA decides whether declared constraints and evidence hold and returns findings, so it is a validator. The Host executes these modules and dispatches creative work under its existing permissions; no Java creative engine or per-Bible database table is required.

## Provider-neutral production boundary

Asset Manifest, Reference Plan and Generation Clip Plan can be authored before production. Route qualification binds execution capabilities only after creative decisions exist; Prompt Compiler projects approved records and continuity into a request while retaining lineage. Provider/model/template details stay in route, compiler and adapters. A creative Bible fingerprint must not change merely because the execution provider changes. Unimplemented routes remain unavailable; a contract is not a claim that every provider has a working adapter.

No professional package, dependency PASS or source-pinned design authorizes image/video/TTS/music generation, paid API calls, casting adoption, or Phase II. Those retain existing authorization and execution gates.

The current visual entry, typed contracts, runtime pin and consumer migration are documented in [Core Creative R1](core-creative-r1.md).

## Opt-in still live-action source mapping

The existing owners can use the [still professional mapping profile](still-professional-mapping.md) for approved cinematography, facial identity and Reference Plan decisions. This adds no department or creative permission. GlobalVisualStyle exposes optional imaging_character; FrameSpec pins professional originals and the derived receipt. QA observations retain the existing Review dispositions and route repairs to one existing owner. The profile's knowledge catalog is provenance, never a character fact source.
