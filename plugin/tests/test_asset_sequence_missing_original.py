"""A proven identity is not a substitute for a selected scene asset design.

These are explicit metadata fixtures. They do not adopt real Scene3 assets,
create predecessor proofs, invoke an external author, or generate media.
"""
from copy import deepcopy
import socket
import subprocess

import pytest

from drama_plugin.contracts.asset import Asset
from drama_plugin.contracts.base import dump_contract
from drama_plugin.film.contracts import CanonScene, FilmCanon
from drama_plugin.runtime.contracts import ArtifactReference
from test_asset_sequence import Author, plugin, request_for, resolve


class MissingSceneOriginal(Exception):
    pass


class CaptureExistingAuthorBoundary:
    def __init__(self):
        self.requests = []

    async def design_assets(self, request):
        self.requests.append(request)
        raise MissingSceneOriginal("No retained scene draft; no author execution")


@pytest.fixture(autouse=True)
def text_only(monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("This regression permits isolated text/metadata only")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(subprocess, "Popen", deny)


@pytest.mark.parametrize("target,expected_revision", [("s-1", 1), ("s-3", 2)])
async def test_existing_versions_without_scene_original_request_author_without_mutation(
    tmp_path, monkeypatch, target, expected_revision
):
    author = Author(variant=True)
    p = plugin(tmp_path, monkeypatch, author)
    try:
        _, request = request_for(p, "s-3")
        await resolve(p, request, author)
        # Represent legacy adopted identities with their exact design/adoption
        # proof, but no recoverable scene preparation. Never fill that gap with
        # an empty draft or manufacture a successful author response.
        legacy = []
        for asset in p.providers.asset.data.assets:
            content = deepcopy(asset.content)
            content["specializedAsset"].pop("scenePreparationOriginal", None)
            content["specializedAsset"].pop("scenePreparationRef", None)
            legacy.append(asset.model_copy(update={"content": content}))
        # A storage-only costume row is not an alternative character authority.
        legacy.append(Asset(id="offline-costume-compatibility-row", work_id="offline-sequence",
            asset_type="COSTUME", name="Retained costume link",
            content={"filmStorage": {"qualification": "OFFLINE_METADATA_FIXTURE"}}))
        _, request = request_for(p, target)
        await p.aclose()
        # A separate restored consumer has no selected narrative/preparation
        # index. Do not rewrite the bootstrap fixture's selected film.
        p = plugin(tmp_path / "restored", monkeypatch, author)
        p.providers.asset.data.assets = legacy
        selected = FilmCanon(work=request.canon.work, script=request.canon.script,
            scenes=(CanonScene(scene_id=target, scene=request.canon.scene),))
        p.asset_sequence.bind_film(request.scope.work_id, selected,
            source_ref=ArtifactReference(owner="offline-fixture", artifact_ref="selected-scoped-canon"))
        boundary = CaptureExistingAuthorBoundary()
        p.professional_design.author = boundary
        before = [dump_contract(a) for a in legacy]
        existing_preparations = set(p.asset_sequence.objects.root.glob("asset-scene-design/*"))
        for _ in range(2):
            with pytest.raises(MissingSceneOriginal):
                await p.professional_design.prepare_assets(request)
        assert len(boundary.requests) == 2
        context = boundary.requests[0].professional_context["assetPreparation"]
        candidates = context["assetCandidates"]
        expected = next(a for a in legacy if a.asset_type == "CHARACTER"
            and a.content["specializedAsset"]["subjectId"] == "A"
            and a.content["specializedAsset"]["revision"] == expected_revision)
        subject = next(s for s in context["subjectCandidates"] if s["name"] == "A")
        assert subject["inherited"]["id"] == expected.id
        assert subject["inherited"]["content"]["specializedAsset"]["design"] == expected.content["specializedAsset"]["design"]
        assert expected.id in {row["asset"]["id"] for row in candidates}
        assert "offline-costume-compatibility-row" not in {row["asset"]["id"] for row in candidates}
        if target == "s-1":
            assert all(row["asset"]["content"]["specializedAsset"]["revision"] == 1 for row in candidates)
        assert before == [dump_contract(a) for a in p.providers.asset.data.assets]
        assert set(p.asset_sequence.objects.root.glob("asset-scene-design/*")) == existing_preparations
        with p.ledger.transaction() as db:
            assert db.execute("SELECT count(*) FROM production_operation").fetchone()[0] == 0
    finally:
        await p.aclose()
