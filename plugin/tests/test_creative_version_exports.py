"""Complete evidence exports never replace canonical creative owner originals."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from drama_plugin.contracts.base import canonical_json, sha256_canonical
from drama_plugin.creative_engine.contracts import Authority, Kind, WorkBody
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.director import DirectorError
from drama_plugin.runtime.contracts import RuntimeScope


def retained(tmp_path):
    store = CreativeVersionStore(tmp_path / "creative")
    ref = store.write(writer=Authority.CANON, kind=Kind.WORK,
        scope=RuntimeScope(work_id="film"), sources=(), operation="original",
        body=WorkBody(interpretation="A refusal tests responsibility",
            dramatic_intent="Observe a refusal", character_meaning="Indifference has consequences"))
    version = store.resolve(ref)
    export = version.model_dump(mode="json", by_alias=True)
    export_ref = store.objects.put("department-evidence", export)
    return store, ref, version, export, export_ref


def test_complete_export_deduplicates_exact_ref_without_changing_bytes(tmp_path):
    store, ref, version, _, _ = retained(tmp_path)
    before = {p: p.read_bytes() for p in (store.root / "objects").glob("*.json")}
    assert store.versions() == (version,)
    assert {p: p.read_bytes() for p in before} == before
    store._path("head", ref.identity).unlink()
    assert store.head(ref.identity) == ref


def test_complete_export_requires_canonical_owner_original(tmp_path):
    store, ref, _, _, _ = retained(tmp_path)
    store.objects._path("objects", ref.fingerprint).unlink()
    with pytest.raises(DirectorError, match="Missing or unreadable artifact"):
        store.versions()


def test_complete_export_verifies_outer_content_address(tmp_path):
    store, _, _, export, export_ref = retained(tmp_path)
    export["body"]["dramaticIntent"] = "Tampered evidence"
    store.objects._path("objects", export_ref.fingerprint).write_text(canonical_json(export))
    with pytest.raises(DirectorError, match="Missing or unreadable artifact"):
        store.versions()


def test_complete_export_verifies_embedded_seal(tmp_path):
    store, _, _, export, _ = retained(tmp_path)
    export["body"]["dramaticIntent"] = "Another interpretation with the old seal"
    store.objects.put("forged-department-evidence", export)
    with pytest.raises(ValidationError, match="Creative version hash mismatch"):
        store.versions()


def test_export_dedup_does_not_hide_conflicting_version_seals(tmp_path):
    store, ref, version, _, _ = retained(tmp_path)
    owner = version.model_dump(mode="json", by_alias=True, exclude={"fingerprint"})
    owner["body"]["dramaticIntent"] = "Conflicting version with a valid different seal"
    alternate = store.objects.put("conflicting-owner", owner)
    assert alternate.fingerprint == sha256_canonical(owner)
    versions = store.versions()
    assert len(versions) == 2
    assert {v.fingerprint for v in versions} == {ref.fingerprint, alternate.fingerprint}
    store._path("head", ref.identity).unlink()
    with pytest.raises(ValueError, match="Creative owner history is ambiguous or incomplete"):
        store.head(ref.identity)
