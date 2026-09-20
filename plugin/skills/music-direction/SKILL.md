---
name: music-direction
description: Design a source-bound film score thesis, motifs, silence, scene music decisions, cues and composer briefs under Director intent. Review music against performance; do not generate audio, direct historical verse, select providers or mix timelines.
---

# Music Direction

Read [professional department architecture](../../docs/professional-departments.md).

## Role and authority

Score HOW under Director WHY; own nondiegetic music and deliberate no-score zones.

## Inputs and dependencies

Director Vision, scene/performance/sound originals and editorial rhythm intention.

## Outputs

Music Bible backed by FilmScorePlan and reviewed scene/cue decisions.

## Forbidden authority

No diegetic vocal authorship, sound design, dialogue rewrite, provider execution or measured mixing.

## Quality gates

Every Scene has a current music/silence decision; source and performance priorities survive.

## Failure and escalation

Return score conflicts to Director; return historical verse to diegetic-vocal; missing listening stays UNKNOWN.


Read [Film Score planning and boundaries](../../docs/film-score-direction.md). Own HOW score serves the Director's WHY. Preserve Script dialogue/purpose, DPD and DirectorPerformanceIntent. Return a DepartmentConflict when music conflicts with acting, source sound, silence or release; the Director decides. Do not make a second Director or rewrite acting to fit music.

Existing read tools: `work.get_work`, `script.get_script`, `episode.get_episode`, `scene.get_scene`, `shot.get_shot`, `asset.search_assets`, `asset.get_asset`, `media.get_media`, `context.build_context`. Read only the missing source context; do not write formal objects or dispatch generation.

## Begin with the complete film

Read the approved scope and current pins, film intent, every Scene, performance direction and source sound. Use supplied original artifacts first; existing read tools only for missing context. Establish a score thesis that describes a dramatic job, not “epic/sad/Chinese style”. Define timbre, density, rhythm and texture with plausible historical flavor and deliberate modern cinematic freedom. Avoid automatic fantasy, pop song, MMO or trailer conventions.

Review every Scene before assessing generated candidates. Record SCORE_REQUIRED, SCORE_OPTIONAL, TRANSITION_ONLY, DIEGETIC_ONLY, NO_SCORE or NO_SCORE_MUST_PRESERVE (legacy SCORE_PRESENT remains readable). Silence is a complete decision. Ask what music adds that actors, dialogue and native sound do not already express. Tears, battles, escape and joy do not prescribe a musical answer. Bind withholding, foreshadowing, release or interruption to the current audience-knowledge design and approved Director intent; no sample story determines their order.

Use a small motif system only where development and payoff justify it. NO_CHARACTER_THEME is valid. Resolve character, motif, location, prop and cue names from the bound context; reuse the R3 isolation validator and retain semantic review evidence. No sample prose may supply a missing source fact.

## Three passes

1. DRAMATIC SCORE DESIGN: screenplay/intent/performance → why, what, event-based entry and exit. Approximate duration may inform requirements; no exact timeline-only cue design.
2. CUE DESIGN: after real Shot/Beat/transition refs exist, bind cues and sync points to them. Do not invent formal Shots for a proposal.
3. PICTURE CONFORM: cinematic-finishing owns measured in/out, fade, duck, crossfade and stem automation on real Media. FilmScorePlan never becomes a second actual edit timeline.

## Sources and rights

Choose each cue's source strategy before composition: ORIGINAL_AI, ORIGINAL_HUMAN, OWNED_EXISTING, LICENSED_LIBRARY, PUBLIC_DOMAIN_COMPOSITION_WITH_CLEARED_RECORDING or TEMP_REFERENCE. NO_SCORE creates no generation request. TEMP_REFERENCE is never production eligible. Composition rights and recording/master rights require distinct evidence; a public-domain composition does not clear a particular recording. Existing Asset/Media lineage and Rights remain authoritative.

For ORIGINAL_AI derive a provider-neutral Composer Brief and MusicGenerationRequirements within FilmScorePlan. Require dramatic function, cue arc, motif/timbre/rhythm, instrumental/vocal policy, dialogue windows, native/SFX priority, duration range, revision/continuation/editability, stems, lossless delivery and commercial rights. Default INSTRUMENTAL: voice/choir needs explicit source-pinned Director and Music approvals. Do not add female humming or epic choir because a model can.

Historical verse performance belongs to Audio/Visual acting, never this Skill. Honor a current user amendment over an older design fixture. DECLAMED_VERSE does not claim melody or ancient authenticity. Shared response without approved lyrics or resolved realization stays unresolved; never invent a duet. Such refs are excluded from score cues and Composer Briefs.

## Finish and review

Produce one FilmScorePlan, with nested motif/cue/requirements values and human-readable Bible/Cue Sheet. Use review_score_plan against all actual Scene IDs and pinned performance intents. Design review is not listening, production authorization or generated music. Actual music findings use FilmReview/FilmFinding, evidence and a repair owner, with review before adoption.

Full Production Book completion must include an explicit reviewed FilmScorePlan even if all Scenes choose NO_SCORE. Do not pass on missing music direction. No new Tool, Agent or DB is involved. A provider adapter executes only a separately authorized source-bound brief; its technical qualification, listening, placement review and adoption remain independent. Missing qualification stays BLOCKED.

## Presence, yield and realized function

SCORE IS NOT WALLPAPER. For every Scene answer what music adds, whether native performance is enough, whether it duplicates emotion or predicts an outcome, whether it reduces physical weight or spatial clarity, and what event requires its exit. NO_SCORE_MUST_PRESERVE is an active protection, not missing material. Changing it requires Director/music-direction re-review.

Every newly placed cue needs nested MusicCue.yieldPolicy. Pin entry/development/exit to actual source actions and declare dialogue, impact, native breath, partner response and diegetic priorities. BUILD → DROP → IMPACT, BUILD → IMPACT → CONTINUE and BUILD → THIN → DIALOGUE → reviewed RETURN are distinct justified choices. Musical climax need not coincide with physical climax. No automatic return at a cut, pursuit, smile or death. Dialogue may coexist with score only with a reason preserving listening.

Before picture conform use event triggers, not seconds or invented Shot IDs. A source action containing both approach and collision must later be split into observed phases; it is not blanket permission to score that whole action. Use review_placement for current action pins and the existing finishing scorePlacement facet for enforcement. Do not omit a known plan to bypass its silence.

Record GeneratedMusicCharacterReview as an artifact/review facet. Keep PLANNED FUNCTION, REALIZED FUNCTION and ADOPTED distinct. Good material may receive REPLACE_FUNCTION with PARTIAL mismatch without GENERATION_FAILED. Bind user listening to exact file hashes; waveforms cannot establish vocals, emotional color, genre or artistic success. Never choose a winner or infer adoption from acceptable content.
