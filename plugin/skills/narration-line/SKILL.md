---
name: narration-line
description: Decide whether a film needs narration and author a source-bound continuous Narration Bible, cues or explicit silence; compare narration with cinema without TTS or adoption.
---

# Narration Line

Own narration strategy, words, literary function and semantic placement across the
film. NONE is a complete result. Consume current screenplay, literary package,
Character Dramaturgy and Director intent. Do not reanalyse source, change rights,
choose visual medium or rewrite upstream. Use the existing compiled source truth;
Chinese adaptation of a Russian narrator is newly adapted text, not a modern
translation quotation.

Read [Narration contract](../../docs/narration-line.md). The current executable
adapter consumes LiteraryPackage/ScreenplayInput. Historical authorial codas retain
their existing path; do not pretend this adapter accepts HistoricalPackage.

Distinguish AUTHORIAL_NARRATION, CHARACTER_VOICE_OVER, INTERNAL_MONOLOGUE and
EXPOSITORY_NARRATION. Source narrator is not character mind. Keep narrator identity,
distance, knowledge, temporal position, irony, density and rhythm consistent in one
NarrationBible. Each scene records NARRATION or SILENCE with a reason. Silence is
chosen, not an empty cue. No mechanical word-count budget substitutes for function.

Before a cue, ask what action/performance/sound/silence already achieves, what
literary function would be lost, and why words add something different. Source
narration may become action, performance or silence. Do not paraphrase visible
behavior, explain motives, diagnose, announce tragedy, assign sympathy or recite
the Philosophical Core. Compare the actual text against silence, including its cost
to performance and whether the film becomes narrated rather than lived.

Each cue owns exact candidate text, source layer, unit/anchor IDs, adaptation
decision, Director reason, placement, dialogue/performance relationship and a pinned
specialist review. Newly invented narration enters HUMAN_CONFLICT; a self-declared
FUNCTION_ONLY label cannot waive that boundary. Explicit theme claims need source
support and human judgment, not a keyword filter. Hashes cannot prove literary merit.

A new VO cannot bypass the existing cinema ExplicitnessException. If the source
package lacks that grant, record UPSTREAM_CHANGE_REQUEST with targetAuthority,
currentValue, problem, sourceEvidence, proposedChange and downstreamImpact. Retain
the B study but do not revise upstream or compile it as an accepted Director plan.

[Authorial Voice](../authorial-voice/SKILL.md) retains node/coda eligibility, literary
forms and actual-use scarcity. It does not own a parallel whole-film spoken track.
At a closure, reuse its eligibility result before proposing an intervention here;
do not create a second coda eligibility engine. An existing LiteraryCandidate may
supply a proposal, never bypass this line's source/placement/continuity gates. Dry-run
alternatives are not actual interventions. Dialogue remains with dialogue-design;
Director recommends and coordinates, never rewrites this Bible inline.

Run `scripts/narration.py schema`, `narration --input ...` or `director --input ...`.
The input carries context plus plan (and narration for director mode). It validates
current originals and review fingerprints, returning candidate/conflict status.
Keep both A/B and recommendation USER_APPROVAL_PENDING. Do not adopt or start P2.

Future NarrationPerformanceIntent describes distance, restraint, irony, certainty,
tempo, pauses and emotional temperature. Never select provider, speaker, voice clone,
TTS model, EQ, mix or generate audio. Director tells sound/music what yields to
narration; downstream professionals implement only after their own approval.

Read supplied originals first. Missing scoped originals may be read with
`work.get_work` or `script.get_script`. `source.prepare_screenplay` is the upstream
compiler entry only after an authorized upstream revision; a locked P1 study does
not authorize that revision or a new business write.
