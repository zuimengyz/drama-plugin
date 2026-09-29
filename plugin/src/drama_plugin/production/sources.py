"""MIGRATION_ONLY read adapter. No Host execution, writes, DAG or Prompt projection."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Protocol

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.production.contracts import AssemblyIssueCode, SourceOwner, SourceReference
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.tools.registry import ToolRegistry


class SourceReadError(ValueError):
    def __init__(self, code: AssemblyIssueCode, owner: SourceOwner, artifact_ref: str):
        super().__init__(code.value)
        self.code, self.owner, self.artifact_ref = code, owner, artifact_ref


@dataclass(frozen=True)
class OwnedSource:
    owner: SourceOwner
    artifact_ref: str
    version: int | None
    body: dict[str, Any]

    def reference(self, *path: str) -> SourceReference:
        return SourceReference(owner=self.owner, artifact_ref=self.artifact_ref, version=self.version,
                               fingerprint=sha256_canonical(self.body), path=path)


class AssemblySources(Protocol):
    async def scope_sources(self, scope: RuntimeScope) -> tuple[OwnedSource, OwnedSource, OwnedSource]: ...
    async def professional(self, department: str, pin: SourcePin) -> OwnedSource: ...
    async def resolve(self, reference: SourceReference) -> Any: ...


class LegacyAssemblySources:
    """Explicit five Canon reads and keyed approved Bible reads from configured owner roots.

    Roots configure storage once; callers never select Camera/Lighting files per Shot.
    Bodies are transient owner reads, not stored in Runtime or ProductionPackage.
    """
    lifecycle = "MIGRATION_ONLY"
    READ_TOOLS = frozenset({"work.get_work", "scene.get_scene", "shot.get_shot",
                            "episode.get_episode", "script.get_script"})

    def __init__(self, tools: ToolRegistry, artifact_roots: tuple[Path, ...] = ()) -> None:
        self.tools = tools
        self.artifact_roots = tuple(Path(root).resolve() for root in artifact_roots)
        self._departments: dict[str, str] = {}

    async def _read(self, code: str, owner: SourceOwner, identity: str, argument: str) -> dict[str, Any]:
        if code not in self.READ_TOOLS:
            raise ValueError("Unregistered legacy source read")
        try:
            entity = await self.tools.invoke(code, **{argument: identity})
            body = dump_contract(entity)
        except Exception as error:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, owner, identity) from error
        if body.get("id") != identity:
            raise SourceReadError(AssemblyIssueCode.SCOPE_MISMATCH, owner, identity)
        if owner == SourceOwner.WORK:
            # These four known Legacy execution stores are not creative Work facts.
            # Normalize both identity and resolve reads; never mutate the owner.
            # Actual creative fields/version still participate in the source hash.
            for field in ("productionHistory", "promptHistory", "productionStage", "productionRoute"):
                body.get("content", {}).pop(field, None)
        return body

    async def scope_sources(self, scope: RuntimeScope) -> tuple[OwnedSource, OwnedSource, OwnedSource]:
        if scope.scene_id is None or scope.shot_id is None:
            raise SourceReadError(AssemblyIssueCode.SCOPE_MISMATCH, SourceOwner.SHOT, scope.work_id)
        work = await self._read("work.get_work", SourceOwner.WORK, scope.work_id, "work_id")
        scene = await self._read("scene.get_scene", SourceOwner.SCENE, scope.scene_id, "scene_id")
        shot = await self._read("shot.get_shot", SourceOwner.SHOT, scope.shot_id, "shot_id")
        episode = await self._read("episode.get_episode", SourceOwner.SCENE, scene["episodeId"], "episode_id")
        script = await self._read("script.get_script", SourceOwner.WORK, episode["scriptId"], "script_id")
        if shot["sceneId"] != scene["id"] or script["workId"] != work["id"]:
            raise SourceReadError(AssemblyIssueCode.SCOPE_MISMATCH, SourceOwner.SHOT, scope.shot_id)
        return (OwnedSource(SourceOwner.WORK, work["id"], work["version"], work),
                OwnedSource(SourceOwner.SCENE, scene["id"], None, scene),
                OwnedSource(SourceOwner.SHOT, shot["id"], None, shot))

    def _bible(self, department: str, key: str) -> dict[str, Any]:
        if not department or any(c not in "abcdefghijklmnopqrstuvwxyz-0123456789" for c in department):
            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, SourceOwner.PROFESSIONAL, key)
        candidates: list[dict[str, Any]] = []
        for root in self.artifact_roots:
            path = root / (department + ".json")
            if not path.is_file():
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, SourceOwner.PROFESSIONAL, key) from error
            if isinstance(value, dict) and "bible:" + str(value.get("id")) == key:
                candidates.append(value)
        if not candidates:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, SourceOwner.PROFESSIONAL, key)
        if len({sha256_canonical(value) for value in candidates}) != 1:
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, SourceOwner.PROFESSIONAL, key)
        self._departments[key] = department
        return candidates[0]

    async def professional(self, department: str, pin: SourcePin) -> OwnedSource:
        if pin.kind not in {"DESIGN", "DIRECTION"}:
            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, SourceOwner.PROFESSIONAL, pin.key)
        value = self._bible(department, pin.key)
        if sha256_canonical(value) != pin.fingerprint:
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, SourceOwner.PROFESSIONAL, pin.key)
        try:
            bible = CreativeBible.model_validate(value)
        except ValueError as error:
            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, SourceOwner.PROFESSIONAL, pin.key) from error
        if bible.created_by_capability != department or bible.status not in {"APPROVED", "NOT_REQUIRED"}:
            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, SourceOwner.PROFESSIONAL, pin.key)
        owner = SourceOwner.DIRECTION if department in {"director", "shot-design", "editorial-design"} else SourceOwner.PROFESSIONAL
        return OwnedSource(owner, pin.key, bible.version, value)

    async def resolve(self, reference: SourceReference) -> Any:
        if reference.owner in {SourceOwner.WORK, SourceOwner.SCENE, SourceOwner.SHOT}:
            name = reference.owner.value
            body = await self._read(f"{name}.get_{name}", reference.owner, reference.artifact_ref, f"{name}_id")
            version = body.get("version")
        else:
            # Only configured keyed files; no filesystem path supplied by a package.
            body = None
            department = self._departments.get(reference.artifact_ref)
            if department is not None:
                source = await self.professional(department, SourcePin(key=reference.artifact_ref,
                    kind="DESIGN", fingerprint=reference.fingerprint))
                if source.owner != reference.owner:
                    raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, reference.owner, reference.artifact_ref)
                body = source.body
            for root in (() if body is not None else self.artifact_roots):
                for path in root.glob("*.json"):
                    try:
                        value = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        continue
                    if isinstance(value, dict) and "bible:" + str(value.get("id")) == reference.artifact_ref:
                        department = value.get("createdByCapability", "")
                        source = await self.professional(department, SourcePin(key=reference.artifact_ref,
                            kind="DESIGN", fingerprint=reference.fingerprint))
                        if source.owner != reference.owner:
                            raise SourceReadError(AssemblyIssueCode.AUTHORITY_MISMATCH, reference.owner, reference.artifact_ref)
                        body = source.body
                        break
                if body is not None:
                    break
            if body is None:
                raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref)
            version = body.get("version")
        if version != reference.version or sha256_canonical(body) != reference.fingerprint:
            raise SourceReadError(AssemblyIssueCode.VERSION_MISMATCH, reference.owner, reference.artifact_ref)
        selected: Any = body
        try:
            for segment in reference.path:
                selected = selected[int(segment)] if isinstance(selected, list) else selected[segment]
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise SourceReadError(AssemblyIssueCode.MISSING_REQUIRED_SOURCE, reference.owner, reference.artifact_ref) from error
        return selected
