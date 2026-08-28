# Dialogue Layer content convention

This convention defines the minimal platform-neutral Dialogue Layer carried by the existing open `content` objects. It creates no domain entity, table, Tool, workflow, or audio-production contract.

## Ownership and field names

- `Scene.content.spokenContent` is the only source of truth for reviewed dialogue and narration. It is an array and may be empty when action, silence, environment, or visual information is sufficient.
- `Shot.content.spokenContentBindings` contains coverage relationships only. It never copies spoken text.
- `Shot.content.plannedDurationMs` is the machine-readable planned Shot duration. A prose rhythm description may coexist but cannot drive the duration gate.
- Do not accept aliases such as `dialogues`, `dialogueLines`, `spokenLines`, `speech`, `spokenContentRefs`, or Shot-local `spokenContent`. Existing summaries such as `dialogueSubtextIntent` may remain supporting facts but never replace required exact text.

## Work-scoped speaker identity

Reuse the Work's existing actor or character structure. In the current Work convention, an individual `historicalActorHierarchy` entry that may speak receives a nonblank `speakerKey`; the existing `actor` value remains its display name. A `speakerKey` is unique and stable within the Work and is reused in every Scene revision and every Scene in that Work.

Do not create a parallel Scene-local speaker registry. A visual `assetId` is optional enrichment only: missing visual identity must not block dialogue design. For narration, use a stable Work-scoped key beginning with `narrator:`, normally `narrator:default`; it does not resolve to a visual character or require an Asset.

## Scene spoken item

```json
{
  "id": "stable-within-parent-scene",
  "kind": "DIALOGUE",
  "speakerKey": "speaker:advisor",
  "text": "Reviewed exact spoken text.",
  "intent": "The immediate dramatic action performed by the line.",
  "mustKeep": true,
  "performanceIntent": "Concise provider-agnostic delivery intent.",
  "provenance": {
    "relation": "ADAPTED",
    "sourceRefs": ["source-or-evidence-ref"],
    "adaptationNote": "What was compressed or transformed."
  },
  "estimatedDurationMs": 1800
}
```

Required fields are `id`, `kind`, `speakerKey`, `text`, `intent`, `mustKeep`, `performanceIntent`, `provenance`, and `estimatedDurationMs`. `kind` is exactly `DIALOGUE` or `NARRATION`. Text, identity, intent, and performance intent are nonblank. `estimatedDurationMs` is a positive integer estimate, never actual media duration.

The concise string `performanceIntent` remains a compatibility field for the
current Dialogue/Audio contract. It is not the typed DPD authority and must not be
expanded into Provider controls. A later compatibility migration may deprecate it
after DPD projection is wired; 7.3A does not remove or reinterpret it.

For `DIALOGUE`, `speakerKey` resolves to the current Work's actor/character structure. For `NARRATION`, it uses the `narrator:` convention. SFX, ambience, foley, music, mixing, voice IDs, audio Media IDs, actual duration, subtitle timing, lip sync, and language variants do not belong here.

## Historical provenance

`provenance.relation` is exactly one of:

- `DIRECT_QUOTE`: the spoken text is a documented quotation;
- `ADAPTED`: the text compresses or rewrites supported source meaning;
- `DRAMATIZED`: the text is compatible dramatic invention within the approved historical boundary;
- `FUNCTIONAL`: the text only performs a dramatic connection or practical function.

`DIRECT_QUOTE` is a hard gate. It requires nonblank `sourceRef`, exact `locator`, and `excerpt`, and the spoken `text` must match the cited excerpt apart from non-semantic whitespace or punctuation normalization. A beat ID, volume title, or general evidence reference alone is insufficient. If any condition fails, Review fails or the relation is explicitly downgraded; it is never silently promoted.

`ADAPTED` requires at least one concise `sourceRefs` entry and a nonblank `adaptationNote`. `DRAMATIZED` retains only the evidence/source references needed to establish its boundary plus a concise note. `FUNCTIONAL` need not copy research material. Never embed a full research document in a spoken item.

## Stable item identity

An item ID is unique within its parent Scene. Wording, performance, duration-estimate, or provenance-detail revision of the same logical item preserves the ID. Adding or deleting an item, splitting one item, or merging items may create or retire affected IDs; every unaffected item retains its ID. A Scene full-replacement save must therefore reconcile IDs before persistence rather than regenerate the whole array.

## Shot binding

```json
{
  "spokenContentId": "stable-within-parent-scene",
  "coverageIntent": "ON_SCREEN_SPEAKER"
}
```

Both fields are required. `coverageIntent` is exactly one of:

- `ON_SCREEN_SPEAKER`: the speaking character is visibly delivering the line;
- `REACTION`: the image observes another subject's response while the same item continues;
- `OFF_SCREEN`: Scene dialogue is heard while its speaker is outside the frame;
- `VOICE_OVER`: narration or deliberately non-diegetic speech accompanies the image.

A binding must resolve to `spokenContent` in the parent Scene. The same item may bind to multiple Shots for speaker/reaction or other continuous coverage, but it remains one item and future audio is generated once. Bindings contain no text, timing, voice, subtitle, or audio fields.

## Duration estimation and feasibility

Estimate speech duration before Shot planning with a language-appropriate character/word-rate heuristic, then adjust for the reviewed performance intent, deliberate pauses, and intelligibility. Record the result as positive integer `estimatedDurationMs`; keep the heuristic and uncertainty in temporary planning state, not as fake actual duration.

Every Shot has positive integer `plannedDurationMs`. For a standalone Shot, the sum of distinct bound item estimates must fit its planned duration. For one spoken item covered continuously by multiple Shots, evaluate the contiguous coverage group: deduplicate item IDs and compare total spoken estimate with total planned duration, then check that action, reaction, and silence still have playable room. Passing the arithmetic lower bound is necessary but not sufficient.

On conflict, fail `DURATION_FEASIBILITY` before physical visual production. Resolve it through reviewed Scene/Shot changes such as compressing non-`mustKeep` content, extending or splitting coverage, using a reaction Shot, or choosing another approved expression. A visual or audio Provider may not delete, create, or rewrite spoken content.
