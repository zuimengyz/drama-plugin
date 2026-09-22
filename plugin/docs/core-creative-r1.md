# Core Creative R1 executable authority

Configure `DRAMA_PLUGIN_VISUAL_MEDIUM=live_action|cg` and one absolute
`DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT` shared by all Hosts for the project.
Configuration files may supply deployment values; explicit environment wins.
No missing-medium fallback is inferred. Read-only legacy inspection needs no medium.

`DramaPlugin.specialized_asset_host()` → `bind_movie(work_id)` persists a write-once
MovieVisualMedium. Reloading with another env retains the existing movie medium;
a new Work receives the new configuration. Keep the authority store with project
state; replacing/deleting it is not a supported way to revise a movie.

Call `save_style(GlobalVisualStyle)`, then `submit(SpecializedAssetBible, current=...)`.
Store originals in the existing DirectorArtifactStore, with their exact SourcePins.
The current map must be the current approved upstream revision map, not reconstructed
from stale design inputs. Character and costume require approved Character Bible
record fields character_ref, arc_stage, behavior_pattern, social_position; Scene
requires approved scene_ref and relevant scene/story fields. All consume approved
Director and adaptation/source/world records. Missing/stale/wrong-owner inputs fail.

`compile(ref, asset_id, current=..., casting_mode=...)` returns a retained compilation,
source map and exact provider-neutral projection. Character CG uses the existing CG
compiler. No new provider is selected. Actual provider adapters must support disabled
enhancement and exact prompt transfer; an unsupported adapter cannot authorize production.

Professional registry lists runtime-visual-medium, global-visual-style and
specialized-asset-design. Their formal contracts use the specialized Host rather than
CreativeBible. Old concrete visual department records remain archival read-only views;
new independent writes are rejected. `department_records` creates `SPECIALIZED_ASSET_PROJECTION` records; the ordinary department Host and Validator replay their values against the specialized original before retaining or consuming them. They have no canCreate/canModify authority and forward
to the specialist. Narrative, performance, lighting, camera, prop and Director owners
remain separate. Pure legacy compilers retain byte-replay compatibility.

Before visual submission, the official Work must carry movieVisualMediumRef,
specializedAssetCompilationRefs and visualSourceCurrent. Runtime gate reopens saved
originals and replays each compiler receipt. Existing route, approval and budget gates
still apply. A source-map gate does not establish semantic quality or legal rights.
No media production is needed to test these contracts.


## Review and actual downstream consumption

Design-only preview may compile before final review. Production requires an exact
`SPECIALIZED_ASSET_REVIEW` original (`decision=APPROVE`, workId, reviewer,
subjectFingerprint of the Bible excluding approvalRef, checkedBoundaries containing
DRAMATURGY / DIRECTOR_INTENT / SOURCE_WORLD / GLOBAL_STYLE). Pin this as approvalRef;
changed assets invalidate it. This records an actual reviewer decision, never an
LLM self-granted conclusion or a deterministic claim of semantic quality.

`bind_video_request(work, request)` projects exact asset compiler output into the
existing VideoRequest and its continuity source pins. The existing route reservation,
HTTP provider lifecycle and immutable recovery remain in place. `begin-submission`
replays the visual originals, checks runtime medium, rejects enabled prompt enhancement
and requires that the submitted prompt actually consumes the retained compilation.
A valid unrelated asset reference alone is insufficient.

Existing image/casting compilers remain byte-replay compatible. Their historical
Seedream `standard` enhancement projection is not new R1 production authority:
the new paid reservation gate rejects enhancement and unconsumed specialized assets.
Do not invent an unsupported provider switch. A future authorized image route must
have verified exact-prompt capability and retain the R1 receipt. This task performs
no capability purchase, generation or media adoption.

Free-text consistency is reviewed against the pinned upstreams. Deterministic
validation proves ownership, shape, freshness and exact receipt binding, not that
every possible prose assertion is artistically or semantically faithful.
