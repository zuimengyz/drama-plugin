"""Formal image-index/text-original handoff; no database or Provider calls."""
from types import SimpleNamespace

import pytest

from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.media import Media
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.creative_engine.contracts import AuthorRequest, CanonDraft, CanonSubject, DesignBody, SceneBody
from drama_plugin.film.contracts import CanonScene, FilmCanon
from drama_plugin.professional_design.asset_sequence import AssetChoice, AssetPreparationPending, SceneAssetDraft
from drama_plugin.production.contracts import SourceDomain as D
from drama_plugin.runtime.contracts import ArtifactReference, RuntimeScope
from test_asset_sequence import film, plugin
from test_formal_author_backends import source


class FourCharactersAndText:
    async def design_assets(self, request):
        rows = request.professional_context['assetPreparation']['subjectCandidates']
        return SceneAssetDraft(assets=(
            *(AssetChoice(asset_type='CHARACTER', name=row['name'], subject_selection=row['selection'],
                design={'face': 'Retained face ' + row['name']}) for row in rows),
            AssetChoice(asset_type='LOCATION', name='Room', reference_required=False,
                design={'architecture': 'One worn room'}),
            AssetChoice(asset_type='PROP', name='Coffin', reference_required=False,
                design={'geometry': 'One small open body and one matching flat lid'})),
            rationale='Four first appearances; room and object need text originals only')

    async def design(self, request):
        rows = request.professional_context['assetSequence']['currentTextDesigns']
        by_type = {row['assetType']: row['design'] for row in rows}
        # Actual professional authorship consumes the originals; the resolver
        # adds provenance only and cannot invent this receiving creative content.
        return (DesignBody(domain=D.WORLD, facts={'setting': by_type['LOCATION']['architecture'],
                    'objectGeometry': by_type['PROP']['geometry']}),
                DesignBody(domain=D.ACTION, facts={'physicalState': by_type['PROP']['geometry']}))


class AssetIndex:
    def __init__(self, p):
        self.p = p

    async def query(self, table, filters, limit):
        assert table == 'drama_asset'
        return [{'id': row.id} for row in self.p.providers.asset.data.assets
            if row.work_id == filters['work_id'] and row.asset_type == filters['asset_type']
            and row.content['specializedAsset']['state'] == filters['state']][:limit]


async def prepared(tmp_path, monkeypatch):
    author = FourCharactersAndText()
    p = plugin(tmp_path, monkeypatch, author)
    base = film()
    scene = SceneBody(scene_text='Selected scene containing four people.',
        subjects=tuple(CanonSubject(id=name, name=name, meaning='Current first appearance') for name in 'ABCD'))
    canon = FilmCanon(work=base.work, script=base.script,
        scenes=(CanonScene(scene_id='scene', scene=scene),))
    p.asset_sequence.bind_film('work', canon,
        source_ref=ArtifactReference(owner='source-owner', artifact_ref='selected-film'))
    request = AuthorRequest(scope=RuntimeScope(work_id='work', scene_id='scene', shot_id='shot'),
        source=source(), source_refs=(), canon=CanonDraft(work=canon.work, script=canon.script, scene=scene))
    with pytest.raises(AssetPreparationPending) as waiting:
        await p.professional_design.prepare_assets(request)
    pin = waiting.value.ref
    packet = p.asset_sequence.objects.read_ref(pin)
    return p, request, pin, packet


async def accept_item(p, pin, item):
    mid = 'reference-' + item['requirementKey'][:16]
    p.providers.media.data.media.append(Media(id=mid, work_id='work', media_type='IMAGE',
        source_ref='OFFLINE_METADATA_FIXTURE', content_hash=sha256_canonical(mid)))
    review = p.asset_sequence.objects.put('exact-adoption:' + item['requirementKey'],
        {'decision': 'ADOPT', 'workId': 'work', 'subjectFingerprint': item['designRef']['fingerprint'],
            'referenceMediaIds': [mid]})
    return await p.asset_sequence.accept(pin, item['requirementKey'], adoption_ref=review, reference_media_ids=(mid,))


def formal(p):
    p.asset_sequence.film_storage = SimpleNamespace(client=AssetIndex(p))


@pytest.mark.asyncio
async def test_four_visual_assets_two_complete_text_originals_and_receiving_provenance(tmp_path, monkeypatch):
    p, request, pin, packet = await prepared(tmp_path, monkeypatch)
    visual = [row for row in packet['requirements'] if row['referenceRequired']]
    accepted = [await accept_item(p, pin, row) for row in visual]
    formal(p)
    text = [row for row in packet['requirements'] if not row['referenceRequired']]
    receipt_pins = []
    for row in text:
        domains = (D.WORLD,) if row['assetType'] == 'LOCATION' else (D.WORLD, D.ACTION)
        receipt_pins.append(await p.asset_sequence.retain_text_handoff(pin, row['requirementKey'],
            domains=domains, rationale='Keep this unchanged text original with its Professional owner'))
    ready = await p.professional_design.prepare_assets(request)
    sequence = ready.professional_context['assetSequence']
    assert {row['id'] for row in sequence['currentAssets']} == {row.id for row in accepted}
    assert len(sequence['currentAssets']) == len(p.providers.asset.data.assets) == 4
    assert len(sequence['currentTextDesigns']) == 2
    assert sequence['preparedScenes'][0]['textDesigns'] == sequence['currentTextDesigns']
    assert p.asset_sequence.objects.read_ref(pin) == packet
    for row, original, handoff_pin in zip(sequence['currentTextDesigns'], text, receipt_pins, strict=True):
        assert row['design'] == original['design']
        assert row['designRef'] == original['designRef']
        assert row['handoffRef'] == dump_contract(handoff_pin)
        assert 'id' not in row and 'assetId' not in row
        assert p.asset_sequence.objects.read_ref(SourcePin.model_validate(row['designRef']))['design'] == row['design']
    designs = await p.professional_design.design(ready)
    assert designs[0].facts['setting'] == text[0]['design']['architecture']
    refs = [p.professional_design.persist(p.creative_versions, ready, design,
        operation='real-text-consumption:' + design.domain.value) for design in designs]
    retained = [p.creative_versions.resolve(ref).body for ref in refs]
    assert len(retained[0].facts['assetTextDesignRefs']) == 2
    assert len(retained[1].facts['assetTextDesignRefs']) == 1
    assert p.professional_design.asset_inheritance_current(ready, retained)
    assert not p.professional_design.asset_inheritance_current(ready, designs)
    assert await p.asset_sequence.retain_text_handoff(pin, text[0]['requirementKey'],
        domains=(D.WORLD,), rationale='Keep this unchanged text original with its Professional owner') == receipt_pins[0]


@pytest.mark.asyncio
async def test_mock_text_adoption_unchanged_and_formal_only_handoff(tmp_path, monkeypatch):
    p, request, pin, packet = await prepared(tmp_path, monkeypatch)
    text = next(row for row in packet['requirements'] if not row['referenceRequired'])
    with pytest.raises(ValueError, match='REQUIRES_FILM_STORAGE'):
        await p.asset_sequence.retain_text_handoff(pin, text['requirementKey'], domains=(D.WORLD,), rationale='Text')
    review = p.asset_sequence.objects.put('old-text-adoption', {'decision': 'ADOPT', 'workId': 'work',
        'subjectFingerprint': text['designRef']['fingerprint'], 'referenceMediaIds': []})
    adopted = await p.asset_sequence.accept(pin, text['requirementKey'], adoption_ref=review)
    assert adopted.reference_media_ids == [] and p.asset_sequence._proof(adopted)
    formal(p)
    with pytest.raises(ValueError, match='ALREADY_REGISTERED'):
        await p.asset_sequence.retain_text_handoff(pin, text['requirementKey'], domains=(D.WORLD,), rationale='Text')


@pytest.mark.asyncio
async def test_visual_requirements_scope_original_hash_and_target_cannot_be_bypassed(tmp_path, monkeypatch):
    p, request, pin, packet = await prepared(tmp_path, monkeypatch)
    formal(p)
    character = packet['requirements'][0]
    with pytest.raises(ValueError, match='REQUIRES_UNREGISTERED_TEXT'):
        await p.asset_sequence.retain_text_handoff(pin, character['requirementKey'], domains=(D.SUBJECTS,), rationale='Text')
    text = next(row for row in packet['requirements'] if not row['referenceRequired'])
    with pytest.raises(ValueError, match='NOT_SELECTED'):
        await p.asset_sequence.retain_text_handoff(pin.model_copy(update={'key': 'wrong'}),
            text['requirementKey'], domains=(D.WORLD,), rationale='Text')
    with pytest.raises(ValueError, match='REQUIREMENT_MISMATCH'):
        await p.asset_sequence.retain_text_handoff(pin, '0' * 64, domains=(D.WORLD,), rationale='Text')
    with pytest.raises(ValueError, match='TARGET_REQUIRED'):
        await p.asset_sequence.retain_text_handoff(pin, text['requirementKey'], domains=(), rationale='Text')
    image_packet = {**packet, 'requirements': [{**row, 'referenceRequired': True}
        if row['requirementKey'] == text['requirementKey'] else row for row in packet['requirements']]}
    image_pin = p.asset_sequence.objects.put('required-location-image', image_packet)
    selected = p.asset_sequence.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], 'scene'])
    with p.asset_sequence.objects._writer():
        p.asset_sequence.objects._write(selected, dump_contract(image_pin))
    with pytest.raises(ValueError, match='REQUIRES_UNREGISTERED_TEXT'):
        await p.asset_sequence.retain_text_handoff(image_pin, text['requirementKey'], domains=(D.WORLD,), rationale='Text')
    with p.asset_sequence.objects._writer():
        p.asset_sequence.objects._write(selected, dump_contract(pin))
    # A retained immutable original with a manipulated scene cannot be selected
    # as a text handoff merely by presenting a fresh hash.
    changed = {**packet, 'sceneId': 'other-scene'}
    changed_pin = p.asset_sequence.objects.put('invalid-scope', changed)
    selected = p.asset_sequence.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], 'other-scene'])
    with p.asset_sequence.objects._writer():
        p.asset_sequence.objects._write(selected, dump_contract(changed_pin))
    with pytest.raises(ValueError, match='SCOPE_MISMATCH'):
        await p.asset_sequence.retain_text_handoff(changed_pin, text['requirementKey'], domains=(D.WORLD,), rationale='Text')
    changed = {**packet, 'requirements': [{**row, 'design': {'architecture': 'invented'}}
        if row['requirementKey'] == text['requirementKey'] else row for row in packet['requirements']]}
    changed_pin = p.asset_sequence.objects.put('invalid-design', changed)
    selected = p.asset_sequence.objects._path('asset-scene-design', [packet['narrativeRef']['fingerprint'], 'scene'])
    with p.asset_sequence.objects._writer():
        p.asset_sequence.objects._write(selected, dump_contract(changed_pin))
    with pytest.raises(ValueError, match='DESIGN_IDENTITY_MISMATCH'):
        await p.asset_sequence.retain_text_handoff(changed_pin, text['requirementKey'], domains=(D.WORLD,), rationale='Text')
