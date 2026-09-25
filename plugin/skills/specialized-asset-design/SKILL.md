---
name: specialized-asset-design
description: Author source-pinned character appearance, costume and scene assets from approved dramaturgy, Director intent and movie runtime medium. Use for concrete asset design and revision, without media generation.
---

# Specialized Asset Design

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
