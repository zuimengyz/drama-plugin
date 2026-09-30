# T6 Target durable persistence

New Target production runs require an **absolute local SQLite ledger path**. Configure
`production_ledger_path` in Plugin YAML, set `DRAMA_PLUGIN_PRODUCTION_LEDGER_PATH`, or
pass `ledger_path=Path("/durable/volume/drama-production.sqlite3")` to `DramaPlugin.load`.
The selected path must be stable across process restarts and shared by every local
worker that may advance a Run. A normal Plugin without this setting refuses to
create formal Target generation/governance runs. Explicit `mock_data` continues to
use the original memory foundation when no ledger path is configured.

The Plugin composition root opens one `ProductionLedger` and injects durable
Run, Package, Gate/Review, Generation, and Reference Binding stores. It does not
move Work/Scene/Shot, Director or Professional Canon, Media bytes, or old Work
production history. Legacy tasks keep their old recovery path. The database
contains four small tables: CAS `production_run`, one typed immutable artifact
table, bounded run/current-reference indexes, and local operation identities.
Unknown artifact types and arbitrary JSON bodies are rejected. The artifact
table stores full **derived execution artifact** bodies once, including the
final prompt text, but only references to Canon and stable Media ID/hash.

```python
plugin = DramaPlugin.load(
    root="/absolute/path/to/drama-plugin/plugin",
    ledger_path="/durable/volume/drama-production.sqlite3",
    production_artifact_roots=(professional_source_root,),
)
run = plugin.create_generation_run(
    work_id=work_id, scene_id=scene_id, shot_id=shot_id, mode=RunMode.EXPERIMENT,
)
ready = await plugin.runtime.run(run.run_id)  # stops at READY_FOR_PROVIDER; no POST

# In a new Python process, with the same ledger path and Canon/Media readers:
restored = DramaPlugin.load(
    root="/absolute/path/to/drama-plugin/plugin",
    ledger_path="/durable/volume/drama-production.sqlite3",
    production_artifact_roots=(professional_source_root,),
)
checkpoint = await restored.runtime.recover_run(run.run_id)
continued = await restored.runtime.run(run.run_id)
```

`recover_run` reads the persisted checkpoint; it does not create or deserialize
a second Run. Completed steps remain completed. A crash during a local pure
capability leaves `RUNNING`; recovery changes it to `BLOCKED`, and only a
declared replay-safe capability can be retried. T6 does not implement paid
dispatch or claim exactly-once execution across a future Provider boundary.

The ledger uses SQLite WAL + FULL synchronous writes, a per-Run local process
lock around advancement, and SQL revision compare-and-swap on every checkpoint.
This is a **single-host durable implementation**. Do not place the SQLite file
on a network filesystem or use it as a cross-host distributed workflow store.
No MySQL migration or Provider transport change is part of T6.

User decisions for formal Target runs use `DramaPlugin.decide_target_run`, which
retains a typed Review receipt before advancing the existing decision ID.
Gate findings/decisions live in the Review namespace and RuntimeRun keeps only
their references. Retention labels distinguish production-required from review
artifacts; T6 does not run automatic garbage collection.
