---
name: specialized-asset-design
description: Author source-pinned character appearance, costume and scene assets from approved dramaturgy, Director intent and movie runtime medium. Use for concrete asset design and revision, without media generation.
---

# Specialized Asset Design

After the complete film screenplay is selected, prepare assets in its narrative
Scene order, independently of the requested shooting order. The native Professional
entry uses `SpecializedAssetSequence`: read accepted assets, design the current
Scene's increment, and finish its necessary references/adoption before advancing
asset preparation to the next Scene. Missing assets are normal resumable preparation;
they do not authorize skipping predecessors, recasting, or shooting earlier videos.
Establish a CHARACTER baseline only at that person's first appearance. Later Scenes
reuse it; justified variations select an accepted parent and retain identity/root,
version, reason and sources. Reuse locations/props according to actual identity and
artistic relation, rather than applying the character rule to every object.
For a screenplay-derived continuity-critical PROP, consume the independent Prop
Design original and Asset Manifest. Prepare its necessary reference at the first
narrative appearance through the same existing asset sequence, then select
reuseSelection for the same object in later Scenes. Prop owns appearance; Action
owns current handling/open/closed state. A structural view and a current-state
proof serve different uses of that same identity. Keep a required reference
pending when generation is unavailable rather than downgrading it to text.
Preserve existing adoption and media. Unproven historical relations remain unknown.
These rules govern post-selection professional design, not Host first writing.

For a missing native asset reference, `design_asset_reference` receives this Scene's retained professional context and the exact selected asset original. It authors
one still proof; system projection assigns identity, source fingerprint and the
existing image route. Asset Resolution advances its native reference child through
compile, quote, spending decision, retention, review, adoption and registration.
Do not call a legacy Work stage or reinterpret a route label as an art original.
Use reference_mode=text_to_image by default. Select image_to_image only when it
is explicitly required, with accepted reference_selections or the inherited
parent. Do not infer the mode from available media. Retain parent identity design
for text-rendered variants; I2I also retains its exact adopted identity image.

Use `DramaPlugin.specialized_asset_host()` and the contracts in
[Core Creative R1](../../docs/core-creative-r1.md). Own concrete CharacterAsset,
CostumeAsset and SceneAsset decisions. Existing character-art, costume-design,
environment-design, environment-art and set-decoration are read-only compatibility
views, not additional authors. Prop Design retains its independent existing contract.

Read current original Character Dramaturgy before CharacterAsset or CostumeAsset.
Pin its record, characterId, arcStage, behavior_pattern and social_position fields.
Read Scene/Story Dramaturgy before SceneAsset. All assets also pin Director Intent
and Source/World constraints. Missing context returns UPSTREAM_INFORMATION_REQUIRED.
Never infer personality, belief, desire, fear, arc, relationships or dramatic purpose
from a proposed look. Do not author blocking, camera, shots or editing.

Runtime medium is fixed per Work. Read the saved movie pin; never change it or infer
it from Historical/Literary, importance, provider, or individual asset. Global Style
sets only shared rendering, realism, materials, light and readability boundaries.
For CG it explicitly selects renderStylization. For LIVE_ACTION no CG style contract
is legal. Author observable medium-neutral facts; the compiler applies those limits.

Every concrete choice has a reason and original source references. Keep sourced
constraints distinct from visual interpretation. If an interpretation conflicts
with dramaturgy, return it upstream; appearance cannot revise identity. Design
continuity changes against the specified arc stage; do not reveal later states early.

Translate the selected Film Look into durable asset relationships: identifiable
silhouette and construction, material response, local surface colors, and only
source-justified wear or ornament. Characters, places and props may share a visual
logic without identical colors or textures. Preserve distinctions needed to read
the person, spatial layout and object use. Low saturation, dirt, photographic
realism and sparse decoration are choices, not defaults. Prop Design remains the
object's appearance owner. Do not manufacture a history from an attractive patina.

For a reference proof, separate these durable facts from temporary illumination,
pose and background. Keep approved face, construction and material legible; do not
copy a dramatic shot's darkness or crop at the expense of the proof's duty. The
current shot's Camera, Lighting and Color may later vary attention and illumination
without repainting or redesigning the asset. In the existing typed image prompt,
put selected appearance in subject/environment facts, view in camera, illumination
in lighting, and concise necessary material/color relationships in preserve.
Use edit_delta only for an approved edit. Essential aesthetics are not optional
secondary_details; include only what this proof must render, without the work's
literary rationale, style-name suffix or a second copy in every field. Finishing
owns optional grain and final grading. Learning examples are not referenceInputs.

At reuse, distinguish inherited identity, target costume/location and sourced
temporary state. Read Look for fatigue, dirt or injury and Performance/Blocking
for expression and pose; do not derive them from an identity image. A recognizably
continuous face does not validate the clothes or room. If a take imports those
incidental properties, preserve the accepted identity and repair the selected
use with its existing owners; a failed take does not authorize recasting.
HERO_CASTING changes prominence and expressive readability only. It cannot add
muscle, broaden shoulders, beautify, reduce age or upgrade costume/social position.

Submit SpecializedAssetBible, then compile the retained version and replay the
provider projection. Retain sourceMap and promptFingerprint. Text validation is not
visual quality review or spending approval. No provider enhancer may add design.
Frozen approved prompts are read-only replay artifacts.

Read current originals with `work.get_work`, `scene.get_scene`, `script.get_script`,
`episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`.
Never create or overwrite Character Core.

## Still live-action professional knowledge

For opt-in STILL/LIVE_ACTION, `face.text` owns approved craniofacial relationships: shape, vertical proportion versus projection, orbit/brow, cheek/midface, jaw/chin and individual eyes/nose/lips/known ears. Use relational distinctions, not ideal ratios or mandatory measurements. `age_presentation` owns the approved stage's apparent age; source age and casting intent are distinct evidence. `hair` owns baseline hairline/density/texture; `surface_state` baseline complexion/region texture; `physical_identity` stable marks. Current expression belongs to Performance and current sweat/injury/makeup/fatigue to Look. A mixed old leaf returns to its author for clarification and renewed approval; mapping does not infer or rewrite it.

Reference Plan coverage cites these exact leaves and character/arc stage; it does not create a second face description. Unknown hidden hairline/ears stay unconfirmed. Neither pores/wrinkles/asymmetry nor clean skin is a universal requirement. Do not infer a jaw, eyes, nose or complexion from occupation, personality, class or ethnicity. Modern casting choices must be explicit approved interpretation, never historical fact. Knowledge provenance never enters the restricted AssetDecision source_refs as character evidence. Existing character-art remains a compatibility view.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
