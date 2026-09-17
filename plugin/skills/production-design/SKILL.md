---
name: production-design
description: Design reusable character casting, faction costume hierarchy, sets and visual motifs from story intent. Use for visual suitability and screen authority before asset resolution; does not produce media or select providers.
---

# Production Design & Casting

Decide what the world and characters should look like, using dramatic role, age,
experience, class, story phase and audience readability. Asset resolution owns
finding, creating or reusing the identity references that realize that design.
Identity continuity alone never proves casting suitability. For historical screen
drama, combine historical plausibility, modern cinematic screen appeal, character
personality and leading-character visual authority. History constrains facts and
period semantics; it does not require museum-reenactment plainness. Reasonable face
and body idealization is a design choice. Distinguish role-specific attractiveness
from idol styling or cosmetic perfection; do not make every role beautiful, every
antagonist ugly, or every hero muscular. Preserve explicitly intended ordinary or
unconventional casting. Never copy a real star or use fantasy armor to supply the
authority missing from the person.

For staged face, relative-scale and performance proof searches, use
[performance-casting](../performance-casting/SKILL.md); this skill retains stable
visual design authority. A neutral one-person portrait cannot establish a relative
stature claim.

Read the [design and handoff contract](references/design.md) when authoring a
revision. Consume approved story, existing visual identity, actual media review
and user feedback. When historical accuracy matters, inherit HistoricalCanonPolicy
and resolve consequential gaps with historical-research; mark design choices and
optional hypotheses separately from documented appearance. Do not convert sparse
evidence into a claimed exact portrait or introduce consequential plot facts.

Use only these four internal modes, selecting the ones the request needs:

- **Character / Casting Design:** CharacterVisualSpec and VisualAuthority; identify
  silhouette, body/face suitability, posture, economical movement, costume and
  spatial priority. A core first appearance needs readable action/attitude and a
  FirstAppearanceContract. Captions label identity; they cannot supply authority.
- **Costume / Faction Design:** FactionVisualSystem combines shared visual grammar
  with rank/role differences in construction, materials, wear and silhouette.
  Repeated identical costumes with different faces require revision. Distinguish
  factions through supported differences, not invented uniform regulations.
- **Location / Set Design:** LocationDesignSpec specifies usable space, paths,
  anchors, material and story state plus foreground/midground/background. It
  complements the VisualBible's look; an atmosphere adjective is not a set.
- **Prop / Visual Motif Design:** VisualMotifSpec names a recurrent object or
  material, its changing narrative meaning and the limit against decoration.

Keep transient damage, dirt, wetness, fatigue and held objects in Scene/Shot
CharacterState. Stable design must not absorb one shot's condition. Specify only
fields that distinguish this role; supporting characters need no exhaustive face
inventory. Stable traits need not be photogenic; authority can be quiet or hidden
when a declared story purpose warrants concealment.

Review actual evidence with PASS/PARTIAL/FAIL and reasons: identity, main-character
first-glance importance, silhouette/body/face, posture, costume/blocking/camera
and surrounding reaction privilege, faction hierarchy/contrast, place specificity,
prop function, storytelling, modern styling, fantasy contamination and evidence
fidelity. Keep unobserved image quality UNKNOWN. No beauty or hero numeric scores.
Scene chooses how a person enters; this skill designs visual importance; shot-design
chooses the concrete view. Do not author camera execution or provider prompts here.

For stable, reusable designs only, search existing Asset semantic keys before
creating a text-only OTHER Creative Asset. Use existing create/get/search and
`creative_assets.remember`; no dummy Media, new table or reference image is needed.
Preserve candidate status and prior revisions. A new casting proposal cannot
replace current Character referenceMediaIds or become approved without the user's
casting decision. Keep shot-specific proposals as working artifacts.

Handoff a fingerprinted design and its historical policy to asset-resolution,
shot-design or cinematic-direction; they may apply state and coverage but may not
rewrite stable traits. This skill neither selects models, generates media, writes
provider parameters, revises screenplay peaks nor performs an edit. Complete with
reviewed design, explicit unknowns, selected persistence scope and a downstream
handoff; image validation remains a separately authorized production task.

For missing supplied context, use `work.get_work`, `script.get_script`,
`episode.get_episode`, `scene.get_scene` or `shot.get_shot` by known identity;
use `context.build_context` only for unresolved context. Discover stable designs
with `asset.list_assets` / `asset.search_assets` and inspect `asset.get_asset`
and `media.get_media`. Verify consequential evidence with `research.search_sources`
and `research.verify_claim`. After a complete reusable candidate exists,
`asset.create_asset` is the first write; `asset.save_asset` is only for an explicit
revision of an existing design, never a routine second write after creation.

For a sequence, contribute source-pinned Bible entries and usable geography to the
[sequence package](../../docs/sequence-production-contract.md). Keep each declared
asset interaction test proportional to actual coverage needs; a motif description
does not by itself establish a prop's grip, scale, contact or continuity state.

For formal sequence production, freeze approved visual duties with typed ProductionDesignFreeze and CinematicStylizationPolicy in the [sequence contract](../../docs/sequence-production-contract.md#production-design-freeze-and-executable-closure). Candidate suitability never implies user casting approval; keep missing visual approvals separate from blocking-design readiness.

For parallel live-action/CG design, read [visual routes](references/visual-routes.md). Keep route-specific proposals and references separate from existing approved design.

## Film and scene preproduction

For full preproduction, use [film design, color script, scene packets and costume continuity](references/preproduction.md). Visual development stays in this skill. Consume screenplay readiness before finalization; use route-aware Historical Cinematic Stylization without changing Canon or implying Lookdev approval.
