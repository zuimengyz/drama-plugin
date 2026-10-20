from types import SimpleNamespace as NS
from copy import deepcopy
import pytest
from drama_plugin.professional_design.reference_roles import reference_role,read_selection,selection_subject,retain_selection
from drama_plugin.professional_design.asset_sequence import SpecializedAssetSequence
from drama_plugin.contracts.base import dump_contract
from drama_plugin.persistence.review import UserDecisionRecord
from test_native_asset_delivery import fixture
from test_native_character_delivery import persist_originals


def setup(tmp_path,monkeypatch):
    _,_,asset,_,proof=fixture(monkeypatch,'PROP')
    ledger,objects=persist_originals(tmp_path,asset,proof)
    async def get_asset(aid):
        assert aid==asset.id
        return asset
    seq=NS(objects=objects,assets=NS(get_asset=get_asset),film_storage=None,
        reference_production=NS(ledger=ledger,adopted_reference=lambda *args:None))
    s=asset.content['specializedAsset']
    packet={'schemaVersion':'asset-reference-selection-v1','workId':asset.work_id,'identity':s['stableIdentity'],
        'reason':'User restores exact baseline; originals unchanged','assets':[{'assetId':asset.id,'role':'BASELINE','designRef':s['designRef'],'adoptionRef':s['adoptionRef']}]}
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    record=ReferenceProductionRecord.model_validate(proof['referenceRecord'])
    decision=UserDecisionRecord.seal(run_id=record.run_id,scope=record.scope,decision_id=record.run_id+':correct-reference-role',category='ADOPTION',accepted=True,source_ref=selection_subject(packet))
    ledger.put_artifact('user-decision',decision.artifact_reference(),decision.scope,decision.fingerprint,decision)
    return seq,asset,packet,decision


@pytest.mark.asyncio
async def test_corrective_selection_retains_originals_and_requires_exact_decision(tmp_path,monkeypatch):
    seq,asset,packet,decision=setup(tmp_path,monkeypatch);before=deepcopy(asset.content)
    await retain_selection(seq,packet,decision.artifact_reference())
    assert reference_role(seq,asset)=='BASELINE' and asset.content==before
    assert read_selection(seq,packet['identity'])['decisionRef']==dump_contract(decision.artifact_reference())
    packet['reason']='unapproved change'
    with pytest.raises(ValueError,match='AUTHORITY'):await retain_selection(seq,packet,decision.artifact_reference())


@pytest.mark.asyncio
async def test_role_selection_rejects_changed_asset_pin(tmp_path,monkeypatch):
    seq,asset,packet,decision=setup(tmp_path,monkeypatch)
    await retain_selection(seq,packet,decision.artifact_reference())
    asset.content['specializedAsset']['designRef']['fingerprint']='0'*64
    with pytest.raises(ValueError,match='PIN_MISMATCH'):reference_role(seq,asset)


def test_supplement_newer_revision_never_wins_baseline_selection(tmp_path,monkeypatch):
    seq,asset,_,_=setup(tmp_path,monkeypatch)
    supplement=asset.model_copy(deep=True);supplement.id='supplement'
    supplement.content['specializedAsset'].update(referenceRole='SUPPLEMENT',revision=999)
    assert SpecializedAssetSequence._latest(seq,[asset,supplement],asset.content['specializedAsset']['stableIdentity'])==asset
