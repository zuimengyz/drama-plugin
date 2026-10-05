"""Offline contract bounds and structured relation selection; no production or Provider IO."""
from pathlib import Path

import pytest
from pydantic import JsonValue, ValidationError

from drama_plugin.config.video_route import VideoRoutePolicy
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.generation.contracts import OperationSelection
from drama_plugin.generation.operation import OperationResolver
from drama_plugin.generation.sources import PackageReader
from drama_plugin.persistence.ledger import ProductionLedger
from drama_plugin.production.contracts import (
    AssemblyBoundary, DomainReference, GenerationIntent, PackageContent, PackageScope,
    ProductionPackage, SourceDomain, SourceOwner, SourceReference,
)
from drama_plugin.runtime.contracts import ArtifactReference, RunMode


def ref(owner: SourceOwner, identity: str, path: tuple[str, ...] = ()) -> SourceReference:
    return SourceReference(owner=owner, artifact_ref=identity, version=1, fingerprint="a" * 64, path=path)


def selection(count: int) -> OperationSelection:
    action = ref(SourceOwner.PROFESSIONAL, "action", ("content", "actionPhases", "0", "action"))
    return OperationSelection(beat_ids=("beat-0",), action_refs=(action,), start_ref=action, end_ref=action,
        fact_refs=tuple(DomainReference(domain=SourceDomain.WORLD,
            reference=ref(SourceOwner.PROFESSIONAL, "world", ("content", "setting", str(i)))) for i in range(count)),
        reference_disposition=())


@pytest.mark.parametrize("count", [64, 66, 128])
def test_fact_refs_capacity_and_serialization(count: int) -> None:
    value = selection(count)
    assert len(value.fact_refs) == count
    assert OperationSelection.model_validate_json(value.model_dump_json(by_alias=True)) == value


def test_fact_refs_rejects_129_and_empty() -> None:
    for count in (0, 129):
        with pytest.raises(ValidationError) as failure:
            selection(count)
        assert failure.value.errors()[0]["loc"] == ("fact_refs",)


def test_generated_schema_has_same_capacity() -> None:
    field = OperationSelection.model_json_schema(by_alias=True)["properties"]["factRefs"]
    assert (field["minItems"], field["maxItems"]) == (1, 128)


@pytest.mark.parametrize("field,bad", [("owner", "provider"), ("path", [".."]), ("fingerprint", "invalid")])
def test_capacity_does_not_relax_source_identity(field: str, bad: JsonValue) -> None:
    body = selection(128).model_dump(mode="json", by_alias=True)
    body["factRefs"][0]["reference"][field] = bad
    with pytest.raises(ValidationError):
        OperationSelection.model_validate(body)


class ExactSources:
    def __init__(self, records: dict[str, JsonValue]) -> None:
        self.records = records

    async def resolve(self, reference: SourceReference) -> JsonValue:
        value = self.records[reference.artifact_ref]
        if reference.fingerprint != sha256_canonical(value):
            raise ValueError("SOURCE_HASH_MISMATCH")
        for segment in reference.path:
            if isinstance(value, dict):
                value = value[segment]
            elif isinstance(value, list):
                value = value[int(segment)]
            else:
                raise ValueError("INVALID_SOURCE_PATH")
        return value


def package_and_reader(count: int) -> tuple[ProductionPackage, PackageReader]:
    records: dict[str, JsonValue] = {
        "ACTION": {"content": {"actionPhases": [{"beatId": "beat-0", "spokenIds": [],
            "entryState": "Standing.", "observable": "Stopped.", "action": "One step."}]}},
        "PERFORMANCE": {"content": {"beats": [{"id": "beat-0", "physicalExpression": "Turns."},
            {"id": "beat-other", "physicalExpression": "Must stay outside this unit."}]}},
        "WORLD": {"content": {"setting": [f"Approved setting fact {i}." for i in range(count - 6)]}},
        "SOUND": {"content": {"ambience": [{"design": "Rain."}],
            "speechRelations": [{"eventId": "line-0", "targetEventId": "line-1", "relation": "BEFORE"}]}},
    }
    scope = PackageScope(work=ref(SourceOwner.WORK, "work"), scene=ref(SourceOwner.SCENE, "scene"),
        shot=ref(SourceOwner.SHOT, "shot"))
    sources = tuple(DomainReference(domain=SourceDomain(name), reference=SourceReference(
        owner=SourceOwner.PROFESSIONAL, artifact_ref=name, version=1,
        fingerprint=sha256_canonical(body), path=("content",))) for name, body in sorted(records.items()))
    content = PackageContent(scope=scope, sources=sources,
        obligations=(scope.shot.model_copy(update={"path": ("content", "purpose")}),),
        generation_intent=GenerationIntent(duration_ms=4000,
            duration_ref=scope.shot.model_copy(update={"path": ("content", "plannedDurationMs")})),
        boundary=AssemblyBoundary(mode=RunMode.PRODUCTION,
            policy_ref=ArtifactReference(owner="policy", artifact_ref="offline-operation-test")))
    return ProductionPackage.freeze(content), PackageReader(ExactSources(records))


@pytest.mark.parametrize("count", [64, 66, 128])
async def test_select_unit_keeps_relations_structured_and_exact(tmp_path: Path, count: int) -> None:
    package, reader = package_and_reader(count)
    resolver = OperationResolver(CreativeVersionStore(tmp_path / "owners"),
        ProductionLedger(tmp_path / "ledger.sqlite"), VideoRoutePolicy())
    unit = await resolver.select_unit(package, reader)
    assert len(unit.fact_refs) == count
    assert len({f.reference for f in unit.fact_refs}) == count
    sound = [f.reference for f in unit.fact_refs if f.domain == SourceDomain.SOUND]
    assert sum(r.path == ("content", "speechRelations") for r in sound) == 1
    assert not any(r.path[:2] == ("content", "speechRelations") and len(r.path) > 2 for r in sound)
    for fact in unit.fact_refs:
        assert "beat-other" not in str(await reader.resolver.resolve(fact.reference))


def test_duplicate_package_refs_remain_rejected() -> None:
    package, _ = package_and_reader(66)
    body = package.model_dump(exclude={"package_id", "fingerprint"})
    body["sources"] = (*body["sources"], body["sources"][0])
    with pytest.raises(ValidationError, match="Duplicate domain/reference selection"):
        PackageContent.model_validate(body)
