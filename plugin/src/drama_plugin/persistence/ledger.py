"""Local durable Target ledger with typed immutable artifacts and CAS checkpoints.

The existing Drama Service owns Canon/Media. Its current schema has no generic
artifact/production-run table, so this deliberately small SQLite ledger owns
only new Target execution state. A configured path is required for formal runs.
"""
from __future__ import annotations

from contextlib import closing, contextmanager
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Iterator, cast

from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeContract, RuntimeRun, RuntimeScope, RuntimeState, validate_repair_history


class RetentionClass(str, Enum):
    CANONICAL = "CANONICAL"  # Owned by Canon Store; never written here.
    PRODUCTION_REQUIRED = "PRODUCTION_REQUIRED"
    REVIEW = "REVIEW"
    TEMPORARY = "TEMPORARY"
    LEGACY = "LEGACY"  # Old history remains with its old owner.


# This is an admission list, not a dynamic JSON warehouse. Each adapter also
# validates the original contract before writing and after reading.
ARTIFACT_TYPES: dict[str, tuple[str, str, RetentionClass]] = {
    "controlled-live-grant": ("controlled-live-grant-v1", "target-execution", RetentionClass.PRODUCTION_REQUIRED),
    "formal-media-registration": ("formal-media-registration-v1", "media-registration", RetentionClass.PRODUCTION_REQUIRED),
    "production-package": ("production-package-v1", "production-assembly", RetentionClass.PRODUCTION_REQUIRED),
    "assembly-validation": ("assembly-validation-v1", "production-assembly", RetentionClass.REVIEW),
    "reference-execution-binding": ("reference-execution-binding-v1", "production-assembly", RetentionClass.PRODUCTION_REQUIRED),
    "prompt-ir": ("target-prompt-ir-v1", "generation", RetentionClass.PRODUCTION_REQUIRED),
    "prompt-coverage": ("prompt-coverage-v1", "generation", RetentionClass.PRODUCTION_REQUIRED),
    "final-prompt": ("final-prompt-v1", "generation", RetentionClass.PRODUCTION_REQUIRED),
    "audio-plan": ("audio-execution-plan-v1", "generation", RetentionClass.PRODUCTION_REQUIRED),
    "generation-preparation": ("generation-preparation-v1", "generation", RetentionClass.PRODUCTION_REQUIRED),
    "execution-diagnostic": ("execution-diagnostic-v1", "review", RetentionClass.REVIEW),
    "gate-finding": ("gate-finding-v1", "review", RetentionClass.REVIEW),
    "gate-decision": ("gate-decision-v1", "review", RetentionClass.REVIEW),
    "user-decision": ("user-decision-v1", "review", RetentionClass.REVIEW),
}

# E1 extends the same typed immutable store; Media bytes stay with Media Store.
from drama_plugin.execution.contracts import EXECUTION_TYPES
ARTIFACT_TYPES.update({name: (name + "-v1", "target-execution", RetentionClass.REVIEW
    if name.endswith("review") else RetentionClass.PRODUCTION_REQUIRED) for name in EXECUTION_TYPES})

from drama_plugin.film.contracts import FILM_TYPES
ARTIFACT_TYPES.update({name: (name + "-v1", "film", RetentionClass.REVIEW
    if name.endswith("review") or name.endswith("qa") else RetentionClass.PRODUCTION_REQUIRED) for name in FILM_TYPES})

INDEX_TYPES = frozenset({
    "governance-input", "generation-input", "latest-decision", "prepared",
    "governance-maintenance", "generation-rebuild", "final-prompt-key",
    "execution-reference-current",
    "media-proof-authorization", "media-proof-cost-terms", "human-media-review", "execution-recovery-authorization",
    "creative-integrity-reconciliation",
    "execution-input", "creative-input", "creative-checkpoint", "film-input", "film-checkpoint", "formal-media-current", "execution-live-grant",
})


class ProductionLedger:
    """SQLite/WAL is a single-host durable implementation, not a Provider sender."""

    durability = "DURABLE_SQLITE_PRODUCTION_LEDGER"

    def __init__(self, path: Path | str):
        raw = Path(path).expanduser()
        if not raw.is_absolute():
            raise ValueError("ProductionLedger path must be absolute across process restarts")
        self.path = raw.resolve()
        if self.path.suffix not in {".sqlite", ".sqlite3", ".db"}:
            raise ValueError("ProductionLedger needs a named SQLite database file")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=30)) as db:
            db.execute("PRAGMA busy_timeout=30000")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS production_run (
                    run_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                    work_id TEXT NOT NULL, scene_id TEXT, shot_id TEXT,
                    mode TEXT NOT NULL, workflow_id TEXT NOT NULL,
                    state TEXT NOT NULL, cursor INTEGER NOT NULL,
                    checkpoint_json TEXT NOT NULL CHECK(length(CAST(checkpoint_json AS BLOB)) <= 32768)
                );
                CREATE TABLE IF NOT EXISTS immutable_artifact (
                    artifact_id TEXT NOT NULL, version INTEGER NOT NULL,
                    artifact_type TEXT NOT NULL, schema_version TEXT NOT NULL,
                    owner_domain TEXT NOT NULL, work_id TEXT NOT NULL,
                    scene_id TEXT, shot_id TEXT, fingerprint TEXT NOT NULL,
                    body_json TEXT NOT NULL, retention TEXT NOT NULL,
                    PRIMARY KEY (artifact_id, version)
                );
                CREATE INDEX IF NOT EXISTS artifact_scope ON immutable_artifact
                    (work_id, scene_id, shot_id, artifact_type);
                CREATE TABLE IF NOT EXISTS ledger_index (
                    index_type TEXT NOT NULL, index_key TEXT NOT NULL,
                    work_id TEXT, scene_id TEXT, shot_id TEXT,
                    value_json TEXT NOT NULL,
                    PRIMARY KEY (index_type, index_key)
                );
                CREATE INDEX IF NOT EXISTS ledger_index_scope ON ledger_index
                    (index_type, work_id, scene_id, shot_id);
                CREATE TABLE IF NOT EXISTS production_operation (
                    operation_id TEXT NOT NULL, attempt_identity TEXT NOT NULL,
                    run_id TEXT NOT NULL REFERENCES production_run(run_id),
                    dispatch_state TEXT NOT NULL,
                    external_task_ref TEXT, result_identity TEXT,
                    PRIMARY KEY (operation_id, attempt_identity)
                );
            """)
            db.execute("BEGIN IMMEDIATE")
            # Additive migration of the Foundation operation table. Old LOCAL_ONLY
            # rows and historical runs are never rewritten or migrated.
            columns = {row[1] for row in db.execute("PRAGMA table_info(production_operation)")}
            for name, declaration in (("operation_ref_json", "TEXT"), ("attempt_ref_json", "TEXT"),
                                      ("receipt_ref_json", "TEXT"), ("progress_json", "TEXT")):
                if name not in columns:
                    db.execute(f"ALTER TABLE production_operation ADD COLUMN {name} {declaration}")
            db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS target_dispatch_operation
                ON production_operation(operation_id) WHERE operation_ref_json IS NOT NULL""")
            db.commit()

    @contextmanager
    def transaction(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=30000")
            if write:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
            else:
                db.execute("BEGIN")
            yield db
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def create_run(self, run: RuntimeRun) -> RuntimeRun:
        run = RuntimeRun.model_validate(run.model_dump())
        with self.transaction(write=True) as db:
            self._insert_run(db, run)
        return run

    @staticmethod
    def _insert_run(db: sqlite3.Connection, run: RuntimeRun) -> None:
        try:
            db.execute("INSERT INTO production_run VALUES (?,?,?,?,?,?,?,?,?,?)", (
                run.run_id, run.revision, run.scope.work_id, run.scope.scene_id,
                run.scope.shot_id, run.mode.value, run.workflow_id, run.state.value,
                run.cursor, canonical_json(run)))
        except sqlite3.IntegrityError as error:
            raise ValueError("Runtime run already exists") from error

    def create_target_run(self, run: RuntimeRun, governance_input,
                          generation_input=None) -> RuntimeRun:
        """Atomically create a Target Run and its required typed initial bindings."""
        from drama_plugin.generation.contracts import GenerationInput
        from drama_plugin.governance.contracts import GovernanceInput
        run = RuntimeRun.model_validate(run.model_dump())
        governance_input = GovernanceInput.model_validate(
            governance_input.model_dump() if hasattr(governance_input, "model_dump") else governance_input)
        if generation_input is not None:
            generation_input = GenerationInput.model_validate(
                generation_input.model_dump() if hasattr(generation_input, "model_dump") else generation_input)
        with self.transaction(write=True) as db:
            self._insert_run(db, run)
            for index_type, value in (("governance-input", governance_input),
                                      ("generation-input", generation_input)):
                if value is not None:
                    db.execute("INSERT INTO ledger_index VALUES (?,?,?,?,?,?)",
                        (index_type, run.run_id, run.scope.work_id, run.scope.scene_id,
                            run.scope.shot_id, canonical_json(value)))
        return run

    def load_run(self, run_id: str) -> RuntimeRun:
        with self.transaction() as db:
            row = db.execute("SELECT * FROM production_run WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        run = RuntimeRun.model_validate_json(row["checkpoint_json"])
        if (run.run_id, run.revision, run.scope.work_id, run.scope.scene_id, run.scope.shot_id,
                run.mode.value, run.workflow_id, run.state.value, run.cursor) != tuple(row)[:9]:
            raise ValueError("ProductionRun checkpoint/index mismatch")
        return run

    def save_run(self, run: RuntimeRun, *, expected_revision: int) -> RuntimeRun:
        run = RuntimeRun.model_validate(run.model_dump())
        if run.revision != expected_revision + 1:
            raise ValueError("Runtime revision conflict")
        with self.transaction(write=True) as db:
            row = db.execute("SELECT checkpoint_json FROM production_run WHERE run_id=?", (run.run_id,)).fetchone()
            if row is None:
                raise KeyError(run.run_id)
            old = RuntimeRun.model_validate_json(row["checkpoint_json"])
            if old.revision != expected_revision:
                raise ValueError("Runtime revision conflict")
            validate_repair_history(old, run)
            for field in ("scope", "mode", "policy_id", "workflow_id", "workflow_fingerprint", "schema_version"):
                if getattr(old, field) != getattr(run, field):
                    raise ValueError("Runtime identity is immutable")
            changed = db.execute("""UPDATE production_run SET revision=?, state=?, cursor=?, checkpoint_json=?
                WHERE run_id=? AND revision=?""", (run.revision, run.state.value, run.cursor,
                canonical_json(run), run.run_id, expected_revision)).rowcount
            if changed != 1:
                raise ValueError("Runtime revision conflict")
            if run.state == RuntimeState.RUNNING:
                operation_id = f"{run.run_id}:{run.cursor}"
                attempt = run.attempt_identity()
                db.execute("""INSERT OR IGNORE INTO production_operation
                    (operation_id,attempt_identity,run_id,dispatch_state)
                    VALUES (?,?,?,'LOCAL_ONLY')""", (operation_id, attempt, run.run_id))
            elif old.state == RuntimeState.RUNNING and old.step_attempts:
                operation_id = f"{old.run_id}:{old.cursor}"
                attempt = old.attempt_identity()
                result_identity = sha256_canonical(run.last_result) if run.last_result is not None else None
                db.execute("""UPDATE production_operation SET result_identity=?
                    WHERE operation_id=? AND attempt_identity=? AND dispatch_state='LOCAL_ONLY'""",
                    (result_identity, operation_id, attempt))
        return run

    def put_artifact(self, artifact_type: str, ref: ArtifactReference, scope: RuntimeScope,
                     fingerprint: str, body: object) -> None:
        with self.transaction(write=True) as db:
            self._put_artifact(db, artifact_type, ref, scope, fingerprint, body)

    @staticmethod
    def _put_artifact(db: sqlite3.Connection, artifact_type: str, ref: ArtifactReference,
                      scope: RuntimeScope, fingerprint: str, body: object) -> None:
        if artifact_type not in ARTIFACT_TYPES or ref.version is None or not scope.work_id:
            raise ValueError("Unregistered or unscoped immutable artifact")
        # Revalidate at the storage boundary. A caller cannot use this generic
        # table as an arbitrary JSON/Canon payload sink by supplying a known tag.
        from drama_plugin.generation.contracts import (
            AudioExecutionPlan, DerivedArtifact, ExecutionDiagnostic, FinalPromptArtifact,
            GenerationPreparation, PromptCoverage, PromptIR,
        )
        from drama_plugin.governance.contracts import GateDecision, GateFinding
        from drama_plugin.production.contracts import AssemblyValidation, ProductionPackage
        from drama_plugin.production.references import ReferenceExecutionBinding
        from drama_plugin.persistence.review import UserDecisionRecord
        models: dict[str, type[RuntimeContract]] = {
            "production-package": ProductionPackage,
            "assembly-validation": AssemblyValidation,
            "reference-execution-binding": ReferenceExecutionBinding,
            "prompt-ir": PromptIR,
            "prompt-coverage": PromptCoverage,
            "final-prompt": FinalPromptArtifact,
            "audio-plan": AudioExecutionPlan,
            "generation-preparation": GenerationPreparation,
            "gate-finding": GateFinding,
            "gate-decision": GateDecision,
            "user-decision": UserDecisionRecord,
        }
        models.update(EXECUTION_TYPES)
        models.update(FILM_TYPES)
        from drama_plugin.execution.formal_media import FormalRegistration
        models["formal-media-registration"] = FormalRegistration
        from drama_plugin.execution.live_transport import ControlledLiveGrant
        models["controlled-live-grant"] = ControlledLiveGrant
        if artifact_type == "execution-diagnostic":
            if not isinstance(body, (list, tuple)) or len(body) > 128:
                raise ValueError("Execution diagnostics must be a bounded typed sequence")
            validated = [ExecutionDiagnostic.model_validate(item.model_dump() if hasattr(item, "model_dump") else item)
                for item in body]
            body = [item.model_dump(mode="json", by_alias=True) for item in validated]
            content_fingerprint = sha256_canonical(body)
        else:
            model = models[artifact_type]
            checked = model.model_validate(body.model_dump() if hasattr(body, "model_dump") else body)
            body = checked
            if artifact_type == "production-package":
                package = cast(ProductionPackage, checked)
                content_fingerprint = package.fingerprint
                actual_scope = RuntimeScope(work_id=package.scope.work.artifact_ref,
                    scene_id=package.scope.scene.artifact_ref, shot_id=package.scope.shot.artifact_ref)
            elif artifact_type == "reference-execution-binding":
                binding = cast(ReferenceExecutionBinding, checked)
                content_fingerprint = sha256_canonical(binding.source().body)
                actual_scope = binding.scope
            elif artifact_type in {"gate-finding", "gate-decision"}:
                content_fingerprint = sha256_canonical(checked)
                actual_scope = cast(GateFinding | GateDecision, checked).scope
            elif artifact_type == "user-decision":
                decision = cast(UserDecisionRecord, checked)
                content_fingerprint = decision.fingerprint
                actual_scope = decision.scope
            elif artifact_type == "assembly-validation":
                content_fingerprint = sha256_canonical(checked)
                actual_scope = scope
            else:
                derived = cast(DerivedArtifact, checked)
                content_fingerprint = derived.fingerprint
                actual_scope = getattr(derived, "scope", scope)
            if actual_scope != scope:
                raise ValueError("Artifact Shot scope mismatch")
            if artifact_type in EXECUTION_TYPES:
                from drama_plugin.execution.contracts import ExecutionArtifact
                from drama_plugin.execution.validation import validate_links
                execution = cast(ExecutionArtifact, checked)
                parent_run = db.execute("SELECT work_id,scene_id,shot_id FROM production_run WHERE run_id=?",
                                        (execution.run_id,)).fetchone()
                if parent_run is None or tuple(parent_run) != (scope.work_id, scope.scene_id, scope.shot_id):
                    raise ValueError("Execution artifact Run scope mismatch")
                def resolve_link(link: ArtifactReference) -> RuntimeContract:
                    row = db.execute("SELECT artifact_type,body_json FROM immutable_artifact WHERE artifact_id=? AND version=?",
                                     (link.artifact_ref, link.version)).fetchone()
                    if row is None or link.owner != row["artifact_type"] or row["artifact_type"] not in models:
                        raise ValueError("Missing or wrong execution lineage reference")
                    return models[row["artifact_type"]].model_validate_json(row["body_json"])
                validate_links(execution, resolve_link)
            if artifact_type in FILM_TYPES:
                from drama_plugin.film.contracts import FilmArtifact
                from drama_plugin.film.validation import validate_links as validate_film_links
                film = cast(FilmArtifact, checked)
                parent_run = db.execute("SELECT work_id,scene_id,shot_id FROM production_run WHERE run_id=?", (film.run_id,)).fetchone()
                if parent_run is None or tuple(parent_run) != (scope.work_id, scope.scene_id, scope.shot_id):
                    raise ValueError("Film artifact Run scope mismatch")
                def resolve_film_link(link: ArtifactReference) -> RuntimeContract:
                    row = db.execute("SELECT artifact_type,body_json FROM immutable_artifact WHERE artifact_id=? AND version=?", (link.artifact_ref, link.version)).fetchone()
                    if row is None or row["artifact_type"] != link.owner or link.owner not in models:
                        raise ValueError("Missing immutable Film lineage")
                    return models[link.owner].model_validate_json(row["body_json"])
                validate_film_links(film, resolve_film_link)
            if artifact_type in {"prompt-ir", "prompt-coverage", "final-prompt",
                                 "audio-plan", "generation-preparation"} or artifact_type in EXECUTION_TYPES:
                derived = cast(DerivedArtifact, checked)
                source = db.execute("""SELECT work_id,scene_id,shot_id FROM immutable_artifact
                    WHERE artifact_id=? AND version=? AND artifact_type='production-package'""",
                    (derived.source_package_ref.artifact_ref, derived.source_package_ref.version)).fetchone()
                if source is None or (source["work_id"], source["scene_id"], source["shot_id"]) != (
                        scope.work_id, scope.scene_id, scope.shot_id):
                    raise ValueError("Derived artifact requires an existing same-Shot ProductionPackage")
        expected_owner = "professional" if artifact_type == "reference-execution-binding" else artifact_type
        prefix = "execution-reference:" if artifact_type == "reference-execution-binding" else artifact_type + ":"
        if ref.owner != expected_owner or not ref.artifact_ref.startswith(prefix) or content_fingerprint != fingerprint:
            raise ValueError("Artifact type/owner/fingerprint mismatch")
        if artifact_type == "reference-execution-binding":
            binding = cast(ReferenceExecutionBinding, checked)
            if (ref.artifact_ref, ref.version) != (binding.source().artifact_ref, binding.version):
                raise ValueError("Reference Binding identity/version mismatch")
        elif artifact_type in {"assembly-validation", "execution-diagnostic"}:
            scoped = sha256_canonical([scope.model_dump(mode="json", by_alias=True),
                body if artifact_type == "execution-diagnostic" else
                cast(AssemblyValidation, body).model_dump(mode="json", by_alias=True)])
            if ref.artifact_ref != prefix + scoped or ref.version != 1:
                raise ValueError("Scoped diagnostic identity mismatch")
        elif ref.artifact_ref != prefix + fingerprint or ref.version != 1:
            raise ValueError("Content-addressed artifact identity mismatch")
        schema_version, owner_domain, retention = ARTIFACT_TYPES[artifact_type]
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint):
            raise ValueError("Invalid artifact fingerprint")
        encoded = canonical_json(body)
        existing = db.execute("SELECT * FROM immutable_artifact WHERE artifact_id=? AND version=?",
            (ref.artifact_ref, ref.version)).fetchone()
        if existing is not None:
            if (existing["artifact_type"], existing["schema_version"], existing["owner_domain"],
                    existing["work_id"], existing["scene_id"], existing["shot_id"],
                    existing["fingerprint"], existing["body_json"], existing["retention"]) != (
                    artifact_type, schema_version, owner_domain, scope.work_id,
                    scope.scene_id, scope.shot_id, fingerprint, encoded, retention.value):
                raise ValueError("Immutable artifact identity conflict")
            return
        db.execute("""INSERT INTO immutable_artifact VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
            ref.artifact_ref, ref.version, artifact_type, schema_version, owner_domain,
            scope.work_id, scope.scene_id, scope.shot_id, fingerprint, encoded, retention.value))

    def get_artifact(self, artifact_type: str, ref: ArtifactReference) -> tuple[dict | list, RuntimeScope, str]:
        if artifact_type not in ARTIFACT_TYPES or ref.version is None:
            raise ValueError("Unregistered artifact reference")
        with self.transaction() as db:
            row = db.execute("SELECT * FROM immutable_artifact WHERE artifact_id=? AND version=?",
                (ref.artifact_ref, ref.version)).fetchone()
        if row is None:
            raise KeyError(ref.artifact_ref)
        schema_version, owner_domain, retention = ARTIFACT_TYPES[artifact_type]
        if (row["artifact_type"], row["schema_version"], row["owner_domain"], row["retention"]) != (
                artifact_type, schema_version, owner_domain, retention.value):
            raise ValueError("Wrong immutable artifact type/owner")
        return json.loads(row["body_json"]), RuntimeScope(work_id=row["work_id"],
            scene_id=row["scene_id"], shot_id=row["shot_id"]), row["fingerprint"]

    def put_index(self, index_type: str, key: str, value: object, *, scope: RuntimeScope | None = None,
                  once: bool = False) -> bool:
        if index_type not in INDEX_TYPES or not key:
            raise ValueError("Unregistered ledger index")
        if scope is None or index_type == "execution-reference-current":
            raise ValueError("Ledger index needs a scope and registered owner API")
        from drama_plugin.generation.contracts import GenerationInput
        from drama_plugin.governance.contracts import GovernanceInput
        if index_type == "governance-input":
            value = GovernanceInput.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type == "generation-input":
            value = GenerationInput.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type in {"creative-input", "creative-checkpoint"}:
            from drama_plugin.creative_engine.contracts import FilmInput, CreativeCheckpoint
            model = FilmInput if index_type == "creative-input" else CreativeCheckpoint
            value = model.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type == "creative-integrity-reconciliation":
            from drama_plugin.creative_engine.contracts import CreativeIntegrityReconciliation
            value = CreativeIntegrityReconciliation.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type in {"film-input", "film-checkpoint"}:
            from drama_plugin.film.contracts import FilmInput as SourceFilmInput, FilmCheckpoint
            film_model = SourceFilmInput if index_type == "film-input" else FilmCheckpoint
            value = film_model.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type == "execution-input":
            from drama_plugin.execution.contracts import ExecutionInput
            value = ExecutionInput.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
        elif index_type in {"media-proof-authorization", "media-proof-cost-terms"}:
            from drama_plugin.execution.contracts import Authorization
            from drama_plugin.execution.live_transport import FinancialTerms
            parsed_model = Authorization if index_type == "media-proof-authorization" else FinancialTerms
            value = parsed_model.model_validate(value.model_dump() if hasattr(value,"model_dump") else value)
        elif index_type in {"latest-decision", "prepared", "final-prompt-key", "formal-media-current", "execution-live-grant", "human-media-review", "execution-recovery-authorization"}:
            value = ArtifactReference.model_validate(value.model_dump() if hasattr(value, "model_dump") else value)
            expected = {"latest-decision": "gate-decision", "prepared": "generation-preparation",
                "final-prompt-key": "final-prompt", "formal-media-current": "formal-media-registration", "execution-live-grant": "controlled-live-grant", "human-media-review":"creative-media-review", "execution-recovery-authorization":"user-decision"}[index_type]
            if value.owner != expected or value.version != 1:
                raise ValueError("Ledger index points to the wrong artifact owner")
        elif type(value) is not int or value != 1:
            raise ValueError("Maintenance claim is a single bounded flag")
        encoded = canonical_json(value)
        with self.transaction(write=True) as db:
            old = db.execute("SELECT value_json FROM ledger_index WHERE index_type=? AND index_key=?",
                (index_type, key)).fetchone()
            if old is not None and once:
                if old["value_json"] != encoded:
                    raise ValueError("Ledger binding already set")
                return False
            if old is not None and index_type == "execution-input" and old["value_json"] != encoded:
                from drama_plugin.execution.contracts import ExecutionInput
                previous = ExecutionInput.model_validate_json(old["value_json"])
                following = ExecutionInput.model_validate_json(encoded)
                external = db.execute("SELECT 1 FROM immutable_artifact WHERE artifact_type='execution-operation' AND json_extract(body_json,'$.runId')=? LIMIT 1",(key,)).fetchone()
                if (previous.model_dump(exclude={"authorization"}) != following.model_dump(exclude={"authorization"})
                        or external is not None):
                    raise ValueError("Execution input binding is immutable")
                # Only a new exact cost receipt can replace authorization before intent reservation.
                decision = db.execute("SELECT body_json FROM immutable_artifact WHERE artifact_id=? AND artifact_type='user-decision'",(following.authorization.approval_ref.artifact_ref,)).fetchone()
                if decision is None:
                    raise ValueError("Reauthorization requires exact durable cost decision")
                from drama_plugin.persistence.review import UserDecisionRecord
                receipt = UserDecisionRecord.model_validate_json(decision[0])
                from drama_plugin.runtime.contracts import DecisionCategory
                if (not receipt.accepted or receipt.category != DecisionCategory.COST_APPROVAL
                        or receipt.run_id != key or receipt.scope != scope or receipt.source_ref != following.preparation_ref):
                    raise ValueError("Reauthorization decision scope mismatch")
            if old is not None and old["value_json"] == encoded:
                return False
            db.execute("""INSERT INTO ledger_index VALUES (?,?,?,?,?,?)
                ON CONFLICT(index_type,index_key) DO UPDATE SET
                    work_id=excluded.work_id,scene_id=excluded.scene_id,
                    shot_id=excluded.shot_id,value_json=excluded.value_json""",
                (index_type, key, scope.work_id if scope else None, scope.scene_id if scope else None,
                    scope.shot_id if scope else None, encoded))
        return True

    def get_index(self, index_type: str, key: str) -> object:
        if index_type not in INDEX_TYPES:
            raise ValueError("Unregistered ledger index")
        with self.transaction() as db:
            row = db.execute("SELECT value_json FROM ledger_index WHERE index_type=? AND index_key=?",
                (index_type, key)).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row["value_json"])

    def scoped_index(self, index_type: str, scope: RuntimeScope) -> tuple[object, ...]:
        if index_type != "execution-reference-current":
            raise ValueError("Only current Reference Binding is indexed by Shot")
        with self.transaction() as db:
            rows = db.execute("""SELECT value_json FROM ledger_index
                WHERE index_type=? AND work_id=? AND scene_id=? AND shot_id=? ORDER BY index_key""",
                (index_type, scope.work_id, scope.scene_id, scope.shot_id)).fetchall()
        return tuple(json.loads(row["value_json"]) for row in rows)

    def register_reference(self, ref: ArtifactReference, scope: RuntimeScope,
                           fingerprint: str, body: object) -> None:
        """Atomically retain one binding version and advance the exact-Shot head."""
        with self.transaction(write=True) as db:
            old = db.execute("""SELECT value_json FROM ledger_index
                WHERE index_type='execution-reference-current' AND index_key=?""",
                (ref.artifact_ref,)).fetchone()
            if old is not None:
                prior = ArtifactReference.model_validate_json(old["value_json"])
                if prior.version is None or ref.version is None or ref.version < prior.version:
                    raise ValueError("Reference Binding version cannot go backwards")
                if ref.version == prior.version:
                    self._put_artifact(db, "reference-execution-binding", ref, scope, fingerprint, body)
                    return
                old_row = db.execute("SELECT work_id,scene_id,shot_id FROM immutable_artifact WHERE artifact_id=? AND version=?",
                    (prior.artifact_ref, prior.version)).fetchone()
                if old_row is None or (old_row["work_id"], old_row["scene_id"], old_row["shot_id"]) != (
                        scope.work_id, scope.scene_id, scope.shot_id):
                    raise ValueError("Reference Binding cannot change Shot scope")
            self._put_artifact(db, "reference-execution-binding", ref, scope, fingerprint, body)
            db.execute("""INSERT INTO ledger_index VALUES ('execution-reference-current',?,?,?,?,?)
                ON CONFLICT(index_type,index_key) DO UPDATE SET value_json=excluded.value_json""",
                (ref.artifact_ref, scope.work_id, scope.scene_id, scope.shot_id, canonical_json(ref)))

    def counts(self) -> dict[str, int]:
        with self.transaction() as db:
            return {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("production_run", "immutable_artifact", "ledger_index", "production_operation")}
