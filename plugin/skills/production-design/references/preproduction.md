# Film and scene production design

Read [shared preproduction contract](../../../docs/cinematic-preproduction.md).
Consume READY_FOR_DIRECTION/READY_WITH_NOTES, current Canon, Director preliminary
intent, route and VisualBible. A failed readiness permits gap analysis only.

## Historical Cinematic Stylization Policy

CG design is historically credible, cinematically stylized, aesthetically elevated,
CG-readable and dramatically functional. Record three layers:

1. Hard invariants: identity, hierarchy, cultural meaning, causal history, major
   technology, era credibility, faction meaning, important object function.
2. Soft realization: silhouette, garment/armor layering, ornament density,
   material richness, refined colors, surface treatment, architectural proportions
   and simplification, prop emphasis.
3. Expression freedom: motivated dramatic light, contrast, color progression,
   hero/support hierarchy, depth, silhouette separation, composition, atmosphere.

Evidence constrains plausibility and meaning, not the aesthetic ceiling. Neither
sparse records nor historical discipline require plain museum reconstruction.
Fine workmanship, richer layered armor, coherent materials, stronger silhouettes
and elegant color hierarchy are allowed when compatible with status, movement,
faction and era. Plain functional design is equally valid for its dramatic job.
Reject fantasy/MMO skins, neon/glowing runes, impossible structures, modern
fashion tailoring, oversized purposeless decoration and universal legendary gear.
Do not beautify all people alike. Ordinary occupations need specific movement,
wear, material economy and social position, not gray interchangeable props.

Record quality evidence for hierarchy, coherent materials, depth, distinction,
light compatibility, composition and readability. StylizationReview only certifies
text policy consistency; CG images and artistic approval remain unobserved.
Apply this CG policy only to stylized_cinematic_cg. General design/readiness/layout
and continuity also serve live action; live action retains its own route grammar.

## Film → color → scene

FilmProductionDesign references existing VisualBible/Canon/intent, then defines
style position and boundary, environment/architecture, material system, costume
and armor, props, crowd/army, weather/day strategy, dirt/damage, motifs and visual
hierarchy. Color Script develops the palette over dramatic phases: hue family,
warm/cool, saturation, value, contrast, character separation, dramatic function,
continuity in/out for each scene. Scene color keys descend from this script;
a list of filters is insufficient. Existing palette is input, not a finished arc.

SceneProductionDesignPacket contains LocationDesignSpec plus geography/terrain,
architecture, entrances/exits, zones/power center, props in zones, foreground,
midground/background, crowd, weather/atmosphere/time, materials, color key,
practical sources, camera-accessible areas and sound zones. Use zone/path IDs and
character start/end positions so blocking can be checked against doorways and
paths. No camera may pass through a wall because its virtual movement is easy.
Keep historical claims separate from stage-layout choices. Functional scale and
movement clearances matter; survey precision or renderer coordinates do not.

Visual development stays in this owner: scene look proposals, staged spatial
alternatives, text layout and future concept briefs. Declare what each future
image would test without generating it. Lookdev approval is downstream.

## Costume and props remember the story

CostumeBible references CharacterVisualSpec; records identity/status/class/faction,
silhouette, layers, armor, materials/colors/ornament, hero/support hierarchy,
historical plausibility, stylization and occupational movement/wear.
CostumeState extends CharacterState per scene: clothing, armor, equipment, dirt,
dust, wetness, sweat, damage, missing gear and necessary blood; predecessor pin,
continuity in/out and cause for each change. Battle dust does not disappear in
rain: it can become mud. Dawn does not repair a torn sleeve. An offscreen change
requires a supported interval/action; preserve UNKNOWN instead of inventing one.
PropDesign distinguishes hero, functional, environmental and historical props:
function, relationship, material, scale, wear, handling and continuity.

Handoff design refs to DPD/blocking/camera/light. Production-design owns WHAT;
cinematic-direction owns lighting/camera HOW; shot-design owns coverage and paths
in the shot. Stable design never becomes an asset approval just by appearing in a
book. Do not save these proposals into formal objects unless separately authorized.
