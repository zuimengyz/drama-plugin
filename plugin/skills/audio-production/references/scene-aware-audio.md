# Scene-Aware Audio Rules

## Context and evidence gate

Before formal Dialogue speech generation, load the smallest persisted hierarchy that can answer who speaks, who listens, where the Scene occurs, what changed, why the line is spoken now, what outcome the speaker seeks, what remains unspoken, and which Shot contains the line. Use the Work actor hierarchy and Scene state first. A structured Character Asset may supplement identity without image Media.

Do not infer a complete person from a name, role, gender, age, or one line. For every inferred dimension record `value`, `confidence` (`LOW`, `MEDIUM`, or `HIGH`), and concise `evidenceRefs`. Use `UNKNOWN` with `LOW` confidence when evidence is absent. Do not generate Audio until the structured Character Understanding has passed the neutrality and evidence audit.

## Character Understanding

Build one provider-neutral, transient `CharacterUnderstanding` keyed only by stable `speakerKey`. It describes how the person usually exists, decides, regulates emotion, communicates, and relates to responsibility; it does not describe whether the person is admirable or blameworthy.

Select only evidence-supported fields from these neutral groups:

- identity/life stage: `lifeStage`, `perceivedAgeRange`, `socialRole`, `institutionalRole`, `professionalRole`, `commandResponsibility`, `socialStanding`;
- experience: `experienceDepth`, `domainExperience`, `leadershipExposure`, `conflictExposure`, `politicalExposure`, `physicalHardshipExposure`, `recentExperienceLoad`;
- decision style: `decisionTempo`, `informationThresholdBeforeAction`, `riskTolerance`, `uncertaintyTolerance`, `actionBias`, `planningHorizon`, `reversibilityPreference`;
- emotional regulation: `emotionalExpressiveness`, `emotionalContainment`, `stressResponse`, `angerExpression`, `fearExpression`, `frustrationExpression`, `recoveryTempo`;
- interaction: `interactionDirectness`, `socialDistancePreference`, `deferencePattern`, `dominanceExpression`, `persuasionStyle`, `conflictStyle`, `trustExpression`, `relationshipSensitivity`;
- authority/responsibility: `formalAuthority`, `situationalAuthority`, `commandResponsibility`, `decisionConsequenceWeight`, `accountabilityLoad`, `roleConstraintStrength`, `publicImageConstraint`;
- communication: `communicationDensity`, `sentenceLengthPreference`, `directness`, `verbosity`, `rhetoricalStyle`, `questionFrequency`, `commandFrequency`, `explanationTendency`, `pauseHabit`, `verbalPrecision`;
- physical baseline: `physicalCondition`, `fatigue`, `pain`, `illnessBurden`, `breathCapacity`, `mobilityConstraint`;
- presentation modes: `publicPresentation`, `privatePresentation`, `rolePerformance`, `maskingLevel`;
- alignment/constraints: `institutionalAlignment`, `loyaltyTarget`, `obligationStructure`, `interestConflict`, `roleConflict`, `boundaryConstraint`.

Use descriptive, behavioral, relational, and state language. Convert value judgments to observable decision, interaction, responsibility, or expression dimensions. Do not use moral, factional, heroic, villainous, intelligence, courage, cowardice, nobility, or worth labels as voice shortcuts.

## Stable traits and current Scene state

Keep Character Understanding stable. Create a separate `SceneState` for temporary conditions:

- `currentEmotion`, `emotionCause`, `internalActivation`, `externalExpressiveness`;
- `urgency`, `stressLevel`, `interactionTarget`, `speakerObjective`, `subtext`, `restraint`;
- current `physicalCondition` and `presentationMode`;
- evidence refs and unknown fields.

Never persist a temporary condition as a durable voice trait. In particular:

- high emotional containment does not imply low energy;
- high internal activation can coexist with low external expressiveness and high self-control;
- fatigue, pain, or illness do not imply weak judgment, low authority, or low command presence;
- older age does not imply slow pace;
- authority or responsibility does not imply loud volume;
- anger does not imply shouting; urgency does not always imply fast speech; low confidence does not always imply quiet speech.

`SceneState` remains an Audio v1 compatibility input. Its activation,
expressiveness/restraint, target, objective, and subtext fields overlap the newer
DPD Core and must not be treated as a second cross-modal authority. A later Audio
Projection migration may derive the Audio brief from an approved `DPDSnapshot`;
this Skill does not define that projection yet.

## Character Voice Profile

Derive a stable provider-neutral Voice Profile only after Character Understanding. Keep the understanding attached as auditable source context, but include only supported vocal consequences in the profile. Use canonical neutral values where possible and `UNKNOWN` where unsupported:

- `vocalAge`, `vocalWeight`, `resonanceDepth`, `timbreBrightness`, `texture`;
- `articulationFirmness`, `phraseAttack`, `baselinePace`, `baselineEnergy`, `breathSupport`;
- `commandPresence`, `gravitas`, `controlledPower`, `sentenceFinality`, `emotionalContainment`;
- language/register and consistency notes.

`commandPresence` means that an utterance naturally carries action consequences, not that it is loud. `controlledPower` means tension and force remain present without shouting. `sentenceFinality` means decisions, commands, refusals, or judgments close clearly when the text requires it; it does not make every sentence heavy.

Age and gender may filter incompatible Provider candidates but never determine the whole casting. Do not make direct age/gender-to-voice rules or infer pace, energy, authority, or intelligence from either.

## Voice candidates and binding

Character casting is separate from Dialogue performance. Submit the provider-neutral profile without a concrete mapping. The Provider adapter may rank at most three compatible candidates from the same profile. A generated Top-1 or short candidate remains `voiceBindingStatus=PENDING` until human review. Do not make it a permanent character binding, randomize the character between lines, or automatically generate every ranked candidate.

If an approved provider binding already exists for the same stable profile, reuse it across Scenes. A Scene changes Performance Intent, not the approved base voice.

## Performance Intent as baseline plus delta

For each Dialogue, derive a separate line-level Performance Intent from the stable Voice Profile plus current Scene State. Make the relation inspectable:

- `baseline`: relevant stable pace, energy, containment, articulation, and sentence-finality values;
- `sceneDelta`: `currentEmotion`, cause, internal activation, external expressiveness, urgency, stress, restraint, `paceAdjustment`, `volumeAdjustment`, pause plan, emphasis, breath adjustment, and sentence-finality adjustment;
- `interactionTarget`, speaker objective, subtext, listener relationship, immediate pressure, and performance boundary.

Do not collapse intent to one mood label. Do not overwrite the base voice with the current emotion or physical state. Preserve every compatible canonical Scene intent and do not invent a contradiction.

This open `PerformanceIntent` is retained for Audio v1 compatibility. Cross-modal
objective, target, activation, control, relationship, subtext, and boundaries now
belong to DPD Core; pace, volume, breath, articulation, emphasis, sentence closure,
and precise pause values belong to future Audio Projection. Do not synthesize a
DPD-to-Audio mapping until that projection contract is introduced.

## Provider-neutral generation specification

The `SpeechGenerationRequest` must carry stable speaker identity, Dialogue identity, exact canonical text, Character Understanding, Character Voice Profile, Scene State, Performance Intent, timing policy, and non-material Work/Script/Episode/Scene/Shot/character/listener references. The Skill decides what the person and this moment mean. The active Provider adapter only ranks compatible voices and translates the supplied semantics into provider syntax; it must not reinterpret the character.

The exact speech input must equal `Scene.content.spokenContent[].text`. Pronunciation and delivery guidance stay outside that field. If wording needs revision, stop and use the normal Dialogue revision path.

## Forbidden production shortcuts

Never:

- depend on a character name when deriving understanding, profile, or casting;
- use `speaker:validation-*` as a production character;
- accept a Provider default voice as casting or select from gender/age alone;
- turn a value judgment or historical reputation into a voice parameter;
- infer a complete personality where evidence is absent;
- merge temporary Scene state into the durable Character Voice Profile;
- equate restraint with low energy, physical burden with low authority, age with slow pace, authority with loudness, anger with shouting, urgency with speed, or uncertainty with quietness;
- ignore speaker/listener relationship or public/private presentation mode;
- manually embed a concrete provider, model, preset voice, or vendor instruction in Skill output;
- silently alter Dialogue text or let the Provider improve it;
- treat a technically valid candidate as an approved voice or performance.

Stop after the requested small candidate set is technically valid and traceable. Human review owns voice binding, character fit, emotion, rhythm, naturalness, and dramatic acceptance.
