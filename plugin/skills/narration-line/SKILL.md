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

Begin with the whole scene and its neighboring narrative movement, not a defense
of individual cues. Whose experience governs attention? Can other people make
claims the narrator has not already explained, and can the event leave an unresolved
cost? A sequence of individually valuable admissions may collectively settle the
relationship too early. Conversely, a sustained act of recollection, thought,
irony or address can itself be the film's living dramatic event. Do not measure
narrative autonomy by how little speech remains.

Compare complete passages with different narration organizations that pursue the
same source and dramatic purpose. Give action and partners enough design to work;
muting an unfinished scene is not a fair alternative. Compare what the audience
experiences before, during and after the encounter, including losses from moving
thought into a later scene. Keep essential thought where its accumulation creates
questions, choices or narrative identity, rather than hiding it merely to favor
images. A local gain must not leave the whole film without its necessary voice.

Then return to each cue: what do action/performance/sound/silence already achieve,
what literary function would be lost, and which speaker, listener or temporal
relation do the words add? A description of a visible act can perform hindsight,
self-indictment, irony or selective memory; overlap alone is not failure. Compare
the exact text with silence and, for disputed placement, another semantic position.
Assess the living partner's scope for response as well as the narrator's knowledge,
responsibility and uncertainty. The partner cannot receive a later explanation:
hand off what they actually hear separately from the audience's hindsight. Preserve
a deliberate fusion when it earns its effect. Do not diagnose motives, assign
sympathy or recite the Philosophical Core to certify meaning. Greater clarity and
fewer words do not by themselves make the encounter more lived.

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

## Spoken language

Bind the narrative identity and delivery of each approved spoken event separately:
inner narration, retrospective voice-over, camera-addressed self-description and
story-world dialogue may coexist in one shot. Narration does not silence every
visible actor or turn their separately assigned lines into voice-over. Preserve
exact words and inter-event relations. Hand semantic perspective, pauses and
foreground priorities to Sound; continuity of the same voice need not imply an
artificially different timbre for narration and dialogue.

Consume the Work `ProductionLanguageProfile`; all adopted narration types use its resolved
production language. Review language never selects speech language. `NONE` creates zero
narration localization tasks. Language configuration cannot adopt a cue or change Narration Bible.
See [production language](../../docs/production-language.md).
