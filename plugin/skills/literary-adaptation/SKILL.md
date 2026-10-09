---
name: literary-adaptation
description: Decide what a literary adaptation preserves or changes and map source units to film destinations; no screenplay or media generation.
---

# Literary Adaptation

Own AdaptationContract and DramaticCompression in `contracts/creative_source.py`. Consume reviewed LiteraryAnalysis and PhilosophicalCore. Preserve must-keep units, core relationships/events, arc, theme conflict and narrative identity. Record permitted operations and a reason, source-unit reference and narrative effect for each decision. Decisions are ADAPTATION_INVENTION, including choices to preserve or compress source material; never write them back into analysis.

## Faithful dramatic invention

Before mapping operations, find what makes this particular work live: a relationship,
contradiction, fate, narrative address or way of knowing. Fidelity can require a new
dramatic process rather than reproducing the author's event summary. Separate the
adopted expression from explicit user locks; an authorized alternative remains a
candidate, not a silent revision of the adopted contract.

Read an omission in context. It may compress a process whose cost cinema needs to
let people experience, preserve a consequential uncertainty, or simply omit a
detail with no expressive importance. Do not assume every absence is intentional
ambiguity, and do not fill limited knowledge with a convenient fact. Ask what the
work would lose if the audience knew the answer, and what it loses if they never
experience the process. Core relationships and fate can constrain invention while
actions, exchanges, local time and the world's activity remain open.

Judge an invention by the encounter it makes possible: whose independent need can
now act, what another person receives or refuses, and what cost remains after the
event. Historically plausible scenery or an additional tactic is not that benefit.
Let ordinary activity, waiting, misunderstanding or persistent desire contribute
when they change the lived relation; do not require louder conflict, a new person,
tragic history or a philosophical speech. Compare a complete expanded passage with
a persuasive condensed form. Keep expansion when its experiential gain warrants
its loss of compression, uncertainty or narrative emphasis; keeping the condensed
form is equally legitimate. A forceful invention can still distort the work.

Hand the chosen opportunity, protected source relations and expressive tradeoff to
Story/Scene and Character, without dictating specialist realization. Record invented
facts and speech as invention, not recovered source evidence. Reconsider the
proposition when local gains damage the whole arc or first-person narrative form.

## Source accounting

Account for every source unit with KEEP, MERGE, COMPRESS, REMOVE, REORDER, EXTERNALIZE or an explicitly permitted other operation. Compression maps those same decision IDs to Film Beat/Scene IDs; do not maintain a second decision list or summarize without destinations. REMOVE has no destination. Preserved units cannot disappear. A significant causal or character change requires upstream contract revision and renewed review before screenplay persistence.

Bind the combined adaptation/compression review to the source revision. Rights come from supplied artifact assertions and the deterministic gate, not this Skill. No formal screenplay text belongs to this upstream package.

Use [Creative Source boundary](../../docs/creative-source.md) for review hashes, routing, persistence and source-map consumers. `source.prepare_screenplay` validates the complete reviewed package; it does not author missing specialist outputs.

For missing retained context read `work.get_work`, `script.get_script`, or `context.build_context`.
