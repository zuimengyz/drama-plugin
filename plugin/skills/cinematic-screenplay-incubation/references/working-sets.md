# Selective context and dependency-aware revision

Global Bible is the author/reviewer store, not every scene's prompt. Select an Episode
Working Set, then a smaller Scene Working Set. Retain only relevant facts, current
character/relationship/knowledge states, continuity, active setups, previous output,
current job and style/lens. Projecting an author fact never gives it to a character.
If a causal constraint is necessary, include it even if it makes the set larger; do not
truncate blindly to a word budget. Measure omissions and explain the selection.

The optional helper uses existing JSON plus these small conventions:

- Scene `episodeId`, `pov`, `omniscience` (declared scope IDs, often empty), and `context`:
  `factIds`, `characterIds`, `relationshipIds`, `stateKeys`, `setupIds`, `lensIds`.
  Relationships/setups/moments have stable local `id`s. Unknown references fail rather
  than silently disappearing. `project(bible, scene_id=...)` returns a scene set;
  `project(bible, episode_id=...)` unions its selected references, not the whole Bible.
- State is projected from the first scene input and selected previous scene output;
  each scene contributes its relevant knowledgeIn and receipts separately. No later
  scene's information is merged into another speaker's opening knowledge. Historical
  facts remain clearly labelled authorConstraints. Detail can be fetched by ID only
  when needed. Audience POV privileges never bypass knowledge receipt checks.
- Optional `dependencies`: `{source, target, reason}` links stable local facts/scenes/
  guidance IDs. `affected_scopes` computes reachability only; it is not a scheduler.
  Record dependencies for facts actually consumed, not every object in the Bible.
  A body-state change reaches dependent blocking/capability but not unrelated politics.
  Key changes by material (for example `scene:body` versus `scene:lens`), not just
  whole-scene identity. A wording/lens edit does not imply its historical output
  changed; propagate into later facts only when those facts actually change.
- A revision round may add `invalidation`: `changedNodes`, `affectedScopes`,
  `unaffectedScopes`, `recheckedScopes`. Declare it before changing text. Only affected
  body scopes may be edited; all reachable dependents require recheck. If a dependency
  changes too, expand the declared graph and scope first and explain why. Hashes still
  protect unchanged text; unchanged words do not exempt a dependent from review.

Meta record checks activate only when direction.meta exists. They check declared load
and aperture, allowed scene POV/omniscience, anchored subjective moments with no fact
overrides, justified deviations, episode boundary state and intention-only anchors.
They cannot detect an unrecorded omniscient sentence or prove historical truth. Read
the body and compare it to the working set. No new Domain, runtime framework or CRUD.
