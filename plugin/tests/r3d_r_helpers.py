"""Exact R3CR-RT01 offline fixture; no current-work creative authorship."""
from pathlib import Path
from typing import Any
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.specialized_asset import SpecializedAssetBible
from drama_plugin.professional import approval_subject
from drama_plugin.specialized_asset import validate_assets
from r3d_helpers import case, approval, use
from test_specialized_asset import fixture

def blocker_case(tmp_path: Path, *, medium: str = 'live_action') -> dict[str, Any]:
    host,bible,_,current=fixture(tmp_path, medium=medium)  # type: ignore[no-untyped-call]
    originals,resolved=host._inputs(bible,current)
    validate_assets(bible,originals,resolved)
    c=case(department='character-dramaturgy');trusted_ref=approval(c)
    for key,value in c['artifacts'].items():host.store.put(key,value)
    current.update(c['current'])
    old=bible.assets[0].dramaturgy.bible_ref
    character=CreativeBible.model_validate(host.store.read_ref(old))
    existing=character.content[0]
    record=existing.model_copy(update={'source_refs':(*existing.source_refs,c['ref'],trusted_ref),'interpretation_uses':(use(c,existing.values),)})
    character=character.model_copy(update={'content':(record,)})
    professional_review=host.store.put('approval:character-dramaturgy',dict(kind='PROFESSIONAL_CREATIVE_APPROVAL',
        subjectId=character.id,workRef=character.work_ref,decision='APPROVE',subjectFingerprint=approval_subject(character),approvedBy=list(character.approved_by)))
    character=character.model_copy(update={'approval_refs':(professional_review,)})
    new=host.store.put(old.key,dump_contract(character))
    current.update({new.key:new.fingerprint,professional_review.key:professional_review.fingerprint})
    # Rebind only the actual consumers, including their existing design receipt.
    raw=dump_contract(bible)
    for asset in raw['assets']:
        if asset['dramaturgy']['bibleRef']==dump_contract(old):
            asset['dramaturgy']['bibleRef']=dump_contract(new)
            for decision in asset['decisions'].values():
                decision['sourceRefs']=[dump_contract(new) if r==dump_contract(old) else r for r in decision['sourceRefs']]
    raw['approvalRef']=None
    candidate=SpecializedAssetBible.model_validate(raw)
    return dict(host=host, candidate=candidate, current=current, character=character, c=c, trusted=trusted_ref)
