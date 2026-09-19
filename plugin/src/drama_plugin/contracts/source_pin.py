"""Shared source pin; sequence retains its public re-export."""
from typing import Literal
from drama_plugin.contracts.base import ContractModel
from drama_plugin.contracts.creative_asset import Text, Hash

class SourcePin(ContractModel):
    key: Text
    kind: Literal['CANON', 'ASSET', 'DESIGN', 'DIRECTION', 'MEDIA']
    fingerprint: Hash


