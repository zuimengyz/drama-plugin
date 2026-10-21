"""Frozen asset-use proof only; fixtures do not attest media quality."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from drama_plugin.contracts.base import dump_contract
from drama_plugin.generation.operation import OperationResolver
from test_native_asset_delivery import fixture, DUTIES

@pytest.mark.parametrize('kind', DUTIES)
@pytest.mark.parametrize('change',[None,'hash','media','review','subject','role','semantics','source','unadopted','design','adoption'])
def test_exact_nonperson_asset_use_requires_matching_originals(monkeypatch,kind,change):
    _,media,asset,binding,proof=fixture(monkeypatch,kind)
    raw=dump_contract(asset)
    raw['resolvedMedia']=[dict(mediaId=media.id,mediaType='IMAGE',contentHash=media.content_hash,version='1',width=1280,height=720)]
    binding.media.version='1';binding.media.kind='image';binding.media.duration=None
    binding.duties[0].purpose='Current authored use'
    objects={raw['content']['specializedAsset'][n+'Ref']['fingerprint']:proof[n+'Original'] for n in ('design','adoption')}
    op=OperationResolver(NS(objects=NS(read_ref=lambda pin:objects[pin.fingerprint])),None,None)
    if change=='hash':binding.media.content_hash='f'*64
    if change=='media':binding.media.media_id='other'
    if change=='review':binding.media.review_ref='unknown'
    if change=='subject':binding.duties[0].subject='other'
    if change=='role':binding.duties[0].role='CHARACTER'
    if change=='semantics':binding.media.semantics=('identity',)
    if change=='source':binding.source_scope=binding.scope
    if change=='unadopted':raw['content']['specializedAsset']['state']='REJECTED'
    if change=='design':objects[raw['content']['specializedAsset']['designRef']['fingerprint']]['design']['architecture']='unapproved'
    if change=='adoption':objects[raw['content']['specializedAsset']['adoptionRef']['fingerprint']]['decision']='REJECT'
    if change:
        with pytest.raises(ValueError):op.asset_reference_use(binding,raw)
    else:op.asset_reference_use(binding,raw)


def test_character_use_requires_exact_selected_professional_purpose(monkeypatch):
    from test_native_character_delivery import fixture as character_fixture
    _,media,asset,binding,proof=character_fixture(monkeypatch)
    raw=dump_contract(asset)
    raw['resolvedMedia']=[dict(mediaId=media.id,mediaType='IMAGE',contentHash=media.content_hash,
        version='1',width=binding.media.width,height=binding.media.height)]
    binding.media.version='1';binding.media.kind='image';binding.media.duration=None
    binding.source_scope=NS()  # Use actual established-scene scope below.
    from drama_plugin.runtime.contracts import RuntimeScope
    binding.source_scope=RuntimeScope(work_id=asset.work_id,scene_id='S')
    binding.duties[0].purpose='Exact selected identity purpose'
    objects={raw['content']['specializedAsset'][n+'Ref']['fingerprint']:proof[n+'Original']
        for n in ('design','adoption')}
    op=OperationResolver(NS(objects=NS(read_ref=lambda pin:objects[pin.fingerprint])),None,None)
    with pytest.raises(ValueError):op.asset_reference_use(binding,raw)
    op.asset_reference_use(binding,raw,authored_purposes=('Exact selected identity purpose',))
    with pytest.raises(ValueError):op.asset_reference_use(binding,raw,authored_purposes=('Unrelated purpose',))
