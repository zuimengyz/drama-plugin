# Production language and subtitle boundary

`config/language.py` extends the existing typed config and `config/loader.py` consumes
the five `DRAMA_PLUGIN_*` language settings. Source metadata owns original language;
runtime owns spoken policy, review language and subtitle delivery. Language tags use a
BCP-47-compatible language/script/region/variant subset, not a full registry validator.

`SourceLanguageMetadata` is a hash-pinned provenance sidecar so frozen SourceArtifact hashes
remain stable. A translation follows its original artifact; artifact language never overwrites
original work language. Unknown and multilingual original languages block source-original routing.

`ProductionLanguageHost.bind_work` writes once in the existing DirectorArtifactStore.
Existing profiles survive env changes. Work create/update validates optional
`content.productionLanguageProfile` and rejects replacement/removal. Historical Work behavior
remains unchanged; no Historical source-original adapter is claimed.

Dialogue Design owns Production Language Adaptation. `compile_localization` consumes pinned
NarrationContext (literary package, screenplay, dramaturgy) and checks source anchors, source
quotes, adaptation destinations and meaning bindings. It does not judge linguistic quality.
`SpeechGenerationRequest` and both actual role-dubbing entry paths require approved production
text for Literary Work. `content.productionDialogueApprovals` stores the reviewed line hash.
Existing Fish Chinese design/ASR is not qualified for Russian by this change; that path fails
`FISH_LANGUAGE_CAPABILITY_REVIEW_REQUIRED` before side effects for other languages.

Native video dialogue uses the same `SpeechLanguageAuthorization` and Work approval
hashes. `resolve_profile` resolves pinned original-source metadata (Russian `ru`, even
when review text is Chinese); bind that approved profile to the Work before preparing
dialogue. `prepare_native_video_language` consumes the Work profile and reviewed
`ProductionDialogueLine` and sets Requirements.language; it does not translate or
change the frozen screenplay. `production_dialogue` travels with Requirements and,
for HTTP, VideoRequest. Cinematic projection and Seedance's canonical gate consume the
approved production text. Existing IR audio slots must contain that exact text and
language, not the review text; rebuild their source fingerprint after binding.

`require_native_video_submission` runs on the fresh Work at formal begin-submission
for both transports and at the HTTP Host before URL materialization. Missing bindings,
unresolved language, stale approval, conflicting current runtime language or Chinese
review text in a Russian production binding block before dispatch. HTTP adapters also
validate typed audio/production bindings before create. Legacy unbound projections
remain available for offline inspection, not live dialogue submission. A translated
line with old review-text character offsets blocks pending approved localized coverage.
Existing Work profiles remain immutable; a changed runtime setting cannot silently
rewrite or override them. No Fish capability or subtitle timing change is included.

Cinematic Finishing owns separate subtitle localization contracts. `compile_subtitle_track`
checks current production text, semantic intent and Work targets. Tracks are UNTIMED, delivered
only to post-production/player; final timing/export and adopted narration subtitle localization
remain future consumers. Narration NONE emits no narration task. Still-image compilers
do not consume language/subtitle settings; video consumes only approved spoken-language
bindings, not subtitle settings. Technical fixtures cannot enter speech production.

Reproducible current candidate dry-run (repository parent):

```sh
source scripts/load-env.sh ~/.config/historical-plugin/drama-plugin.env
PYTHONPATH=drama-plugin/plugin/src drama-mcp-service/.venv/bin/python artifacts/literary-cinema-p1c/verify_policy.py
```

The retained current Work is a local review candidate, not a new business database Work.
No live service write, translation model or media provider is used by this command.
