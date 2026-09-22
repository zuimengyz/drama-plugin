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

Cinematic Finishing owns separate subtitle localization contracts. `compile_subtitle_track`
checks current production text, semantic intent and Work targets. Tracks are UNTIMED, delivered
only to post-production/player; final timing/export and adopted narration subtitle localization
remain future consumers. Narration NONE emits no narration task. Visual compilers do not
consume language/subtitle settings. Technical fixtures cannot enter speech production.

Reproducible current candidate dry-run (repository parent):

```sh
source scripts/load-env.sh ~/.config/historical-plugin/drama-plugin.env
PYTHONPATH=drama-plugin/plugin/src drama-mcp-service/.venv/bin/python artifacts/literary-cinema-p1c/verify_policy.py
```

The retained current Work is a local review candidate, not a new business database Work.
No live service write, translation model or media provider is used by this command.
