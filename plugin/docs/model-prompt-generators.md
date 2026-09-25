# Model prompt generators

`VisualPromptIR` is the creative input. A generator translates its approved facts;
it cannot complete missing action, performance, character, camera or reference decisions.
Seedance 2.0 HTTP requests now compile through `Seedance2PromptGenerator`. Selection,
Director, Work/Scene/Shot ownership and media storage are unchanged.

## Entry points and readiness

Use `visual.video_prompt.compile_request_ir(request, provider=selected_provider,
model=selected_model)`. Explicit route arguments matter for an approved switch;
ContinuityPack.primary_model remains continuity history, not a new selection.
The actual model registry supplies the provider hard character limit. Soft budgets
are UNVALIDATED. `prompt_generators.registry.registry()` reports readiness and
supported modes. Reserved families cannot be dispatched by `get_generator`.
Other families retain existing routes; README presence is not implementation.

Seedance supports text_to_video, image_to_video, first_last_frame and reference.
Edit/extend fail capability admission. A Seedance request without canonical IR
cannot fall back to a generic prompt. `compile_ir(..., legacy_replay=True)` is
explicit offline historical replay; submission replays the new generator and
rejects a generic historical receipt.

## Source atoms and coverage

Each emitted IR leaf becomes one complete proposition, never a set of words.
Its receipt keeps source, professional owner domain, clip/scope, subjects, complete
relation/state, temporal position, literal negation and reference duty. Where
free prose does not separately identify target or negation, they remain embedded
in the complete proposition. No NLP extractor guesses those fields. Dedup requires
complete literal AND scoped semantic equality; uncertain relations are retained.
An obligation's receipt contains exactly one emitted span and, when applicable,
the reference tag, version/hash and duty. Several equivalent source obligations
can share one span. All CRITICAL/IMPORTANT and required rows must be covered.

Compiler paths, source locators, priorities, policies and review metadata stay in
the receipt. They are not copied into model prose. Existing CAPABILITY/FUTURE/
INTERNAL source-only fields stay non-projected; a required non-executable fact
still fails the existing IR gate. Only explicitly optional SECONDARY rows can be
dropped for budget. Other facts may be structurally shortened or exactly deduped,
but this version deliberately has no unreviewed natural-language paraphraser.
Supporting facts that still exceed the hard limit return to planning.

## Reference duties

A `VideoReference` can carry optional `prompt_binding` metadata:

```json
{
  "subject_id": "canonical-actor",
  "coverage": [{
    "path": "subject.canonical-actor.face",
    "source": "the exact existing Fact.source",
    "text_hash": "sha256_canonical of the exact Fact.text",
    "duty": "FACE_IDENTITY"
  }],
  "must_not_carry": ["pose", "lighting", "composition", "expression"]
}
```

This belongs inside the reviewed reference in the existing Canon ContinuityPack.
The request reference must equal that Canon reference, including this annotation.
The Host still reloads the canonical pack and verifies Media identity/hash before
submission. A caller cannot append an unreviewed coverage claim only to the request.
Absent coverage claims retain text. False source/hash/path/duty/actor claims fail.
Approved coverage supports face, hair, body, costume, scene architecture/topology
and specific props. Contact, direction, lighting, current pose, negation and
through-process continuity cannot be silently covered by a portrait.

Numbering follows `VideoRequest.references()`, which is also adapter content order:
first frame, last frame, reference images, videos, audios, with per-kind counters.
Use canonical actor tokens `{{actor:canonical-id}}` in prose. The generator also
recognizes exact, unambiguous approved Subject.role aliases; it never guesses new
aliases. Subject definitions retain their role once; subsequent references use
stable labels sorted by canonical actor ID. Duplicate role aliases require owner
resolution. Provider tags must not be pre-numbered inside source facts.

## Audio and camera annotations

Optional `VideoRequest.prompt_projection` carries source-bound audio annotations:
`path`, exact `source`, canonical `text_hash`, `kind` (DIALOGUE/BGM/SFX), and for
speech the canonical `speaker` plus approved `language`; `timing` preserves an
approved interval where present. These annotations contain no replacement text.
The IR audio leaf itself is the exact approved utterance/cue. Missing audio
bindings fail closed, even when native audio is enabled. Literal dialogue never
passes through subject alias replacement, paraphrase or pronunciation substitution.
CinematicShotSpec requests also check exact canonical speaker/text/interval and
reject additional dialogue. Subtitle/title generation has no new speculative
contract in this version; authoring a canonical scoped constraint remains possible.

A declared `camera_conflict` returns to cinematography. The narrow diagnostic for
explicit simultaneous push/pull also fails unless the compound is explicitly
approved by the same camera source. `approved_compound_camera_source` is source
metadata, not permission for the generator to choose or invent a move. This is
an experimental check, not a complete parser for arbitrary camera prose.

## Cinematic source admission

For frozen CinematicShotSpec HTTP requests, the source gate verifies endpoints,
each full approved timed beat, visual bible/camera/light/continuity sections,
required references, asset authority when present, and exact dialogue bindings.
Its source equality checks reuse `executable`/`prose` for matching complete
approved source sections in IR atoms; those helpers do not write the final prompt.
Professional owners must supply this mapping in the existing IR. A missing section
returns UNRESOLVED, rather than generating a generic intermediate prompt or
inventing facts. No new source Canon is stored.

## Validation boundary

All Seedance knowledge is LOCAL_EXPERIMENTAL. Unit tests prove deterministic
projection, gates and transport equality; they do not prove visual resemblance,
reference sufficiency in pixels, or actual Seedance quality. Hashes prove source
identity, not truth of a human review. The existing source review remains necessary.
A5 will assess prompt syntax and model behavior with separately authorized media
experiments. No external Skill is installed and no fixed quality/stability tail
is appended.
