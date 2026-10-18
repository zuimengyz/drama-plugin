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

Use the configured formal asset author for asset-plan authorship and the configured
reference-artwork author for the still's realization. The Host supplies selected
sources, calls those authors and reviews their work; it does not disable them and
fill FrameSpec/prompt_ir as a substitute for this formal process. A retained author
context proves available evidence, not author execution. Preserve the actual text
request, raw response and selected candidate separately from the final image request.
Without authorized text spending, prepare the evidence and report that author work
is pending; do not label a Host-supplied frame as a formal author's result.

An explicit reassessment of an already prepared asset uses
`specialized_assets.revise_assets` with the source-bound request, current
preparation_ref and scoped accepted asset_ids, rather than reusing the cached
scene packet. This entry calls the configured asset author; it does not accept
Host-written replacement design fields.
Scope it to the requested accepted parents and retain their identity, costume,
materials and necessary spatial or object structure. Let the formal asset author
evaluate the old proof/view/light as candidates under the selected Film Look;
the old FrameSpec is evidence to assess, not a new author output or an answer to
copy. A reasonable choice may remain. Record its purpose, basis and tradeoff in
the existing rationale/reason and its visible consequences in proof/referenceLighting.
Keep this unadopted revision separate from the active preparation and adopted
assets. Its fresh reference child then calls design_asset_reference to realize
the newly authored plan; it must not be prefilled with the old FrameSpec. Review
author execution, aesthetic reasoning and final-request delivery separately.

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
from a proposed look. Do not author scene blocking, movie camera plans, shots or
editing. A still proof's viewing purpose and reference illumination stay within
this asset/reference responsibility; they do not direct the later movie Shot.

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

## Executable reference inheritance

For native `AssetChoice.design`, author visible single-line facts in the existing
leaves: `roleLabel`, `apparentAge`, `identity` (or `face`, never both), `hair`,
`body`, `costume`, `architecture`, `topology`, `workArea` (or `construction`),
`material`, `materials`, `geometry`, `scale`, and `proof`. Use only applicable
leaves; `proof` describes this still's view, not future motion. Keep rationale,
source uncertainty and package bindings in `reason`, `rationale`, `sourceBoundary`
and `characterPackage`; these are never sent as visible facts. For approved
reference illumination use `referenceLighting` with the existing Lighting keys
`time_of_day`, `light_sources`, `contrast`, `realism`. This is proof illumination,
not a permanent asset property or a replacement for Shot Lighting.

Target code copies these selected leaves into the existing typed image prompt
and checks their delivery in the serialized request. Reference artwork must not
re-author them in optional prose, backgrounds or edit corrections. If originals
are incomplete, ambiguous or use unmapped fields, the Host supplies the retained
professional context to the configured asset author (or Prop Design for object
appearance), then reviews the completed original. Do not replace that author's
visual choices by filling its fields in Host code. This is continuing author work,
not a request for the user to repair a Prompt or a new approval gate.
Preserve source uncertainty; do not invent historical facts or redesign identity.
Unknown fields are never silently omitted or flattened into a prompt. Change
the design original, not a sealed Prompt. Unadopted preparations can be revised through
`specialized_assets.revise_reference_designs`; in-flight or adopted references
retain their existing lifecycle and cannot be overwritten by that operation.
After saving the full replacement, resume the parent creative Run; it reads the
new selected preparation and compiles a fresh request automatically. Inspect the
actual serialized request, then continue under the existing spending/review
scope. Never finish the Host task merely by reporting this completion duty.

In a typed image prompt, `negative_constraints.positive_target` must express the
same selected limit as `constraint`; unrelated material or realism prose is not
an equivalent for excluding captions or diagram labels. Review both against the
serialized body. The current still compiler preserves the original limit with
the target and removes exact repetition; do not duplicate it across other fields.

Read current originals with `work.get_work`, `scene.get_scene`, `script.get_script`,
`episode.get_episode`, `shot.get_shot`, `asset.get_asset`, `context.build_context`.
Never create or overwrite Character Core.

## Still live-action professional knowledge

For opt-in STILL/LIVE_ACTION, `face.text` owns approved craniofacial relationships: shape, vertical proportion versus projection, orbit/brow, cheek/midface, jaw/chin and individual eyes/nose/lips/known ears. Use relational distinctions, not ideal ratios or mandatory measurements. `age_presentation` owns the approved stage's apparent age; source age and casting intent are distinct evidence. `hair` owns baseline hairline/density/texture; `surface_state` baseline complexion/region texture; `physical_identity` stable marks. Current expression belongs to Performance and current sweat/injury/makeup/fatigue to Look. A mixed old leaf returns to its author for clarification and renewed approval; mapping does not infer or rewrite it.

Reference Plan coverage cites these exact leaves and character/arc stage; it does not create a second face description. Unknown hidden hairline/ears stay unconfirmed. Neither pores/wrinkles/asymmetry nor clean skin is a universal requirement. Do not infer a jaw, eyes, nose or complexion from occupation, personality, class or ethnicity. Modern casting choices must be explicit approved interpretation, never historical fact. Knowledge provenance never enters the restricted AssetDecision source_refs as character evidence. Existing character-art remains a compatibility view.

Read [mapping and evidence profile](../../docs/still-professional-mapping.md) when preparing these still records. Knowledge remains LOCAL_EXPERIMENTAL until scoped A5 media evidence.
