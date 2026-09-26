"""Offline plumbing fixture: not current-work creative authorship or user approval.

Prove that SpecializedAssetHost cannot forward trusted interpretation context.
No runtime mutation, monkeypatch, provider call, or bypass is used.
"""
from __future__ import annotations
import inspect
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO/'plugin/tests'))
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.professional import CreativeBible
from drama_plugin.contracts.specialized_asset import SpecializedAssetBible
from drama_plugin.professional import validate_bible, approval_subject
from drama_plugin.specialized_asset import upstream, validate_assets
from drama_plugin.hosts.specialized_asset import SpecializedAssetHost
from r3d_helpers import case, approval, use
from test_specialized_asset import fixture


def capture(fn: Any) -> dict[str, Any]:
    try:
        result=fn()
        return {'status':'PASS','result':dump_contract(result) if hasattr(result,'model_dump') else str(result)}
    except (ValueError,TypeError) as exc:
        return {'status':'FAIL','type':type(exc).__name__,'error':str(exc)}


def main() -> None:
    with TemporaryDirectory(prefix='r3c-r-approval-preflight-') as temporary:
        host,bible,_,current=fixture(Path(temporary))
        originals,resolved=host._inputs(bible,current)
        control=capture(lambda:validate_assets(bible,originals,resolved))
        assert control['status']=='PASS'
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
        originals,resolved=host._inputs(candidate,current)
        direct=capture(lambda:validate_bible(character,originals,resolved,approved_interpretation_refs=(trusted_ref,)))
        blocked=capture(lambda:host.submit(candidate,current=current))
        cannot_supply=capture(lambda:host.submit(candidate,current=current,approved_interpretation_refs=(trusted_ref,)))
        assert direct['status']=='PASS',direct
        assert blocked.get('error')=='USER_INTERPRETATION_APPROVAL_REQUIRED',blocked
        assert cannot_supply['type']=='TypeError' and 'unexpected keyword' in cannot_supply['error']
        result={'classification':'R3C_R_BLOCKED_BY_RUNTIME','blockerId':'R3CR-RT01',
            'fixtureOnly':True,'currentWorkCreativeDesignCreated':False,'runtimeChanges':0,'paidCalls':0,
            'controlBeforeOptIn':control,'directApprovedProfessionalValidation':direct,
            'actualSpecializedAssetHostSubmit':blocked,'passingTrustedContextToHost':cannot_supply,
            'signatures':{'SpecializedAssetHost.submit':str(inspect.signature(SpecializedAssetHost.submit)),
                          'validate_assets':str(inspect.signature(validate_assets)),
                          'upstream':str(inspect.signature(upstream)),
                          'validate_bible':str(inspect.signature(validate_bible))},
            'cause':'SpecializedAssetHost.submit -> validate_assets -> upstream invokes validate_bible without approved_interpretation_refs; no public parameter transports trusted refs.',
            'repairOwner':'Runtime integration owner: Specialized Asset / professional approval-context propagation',
            'noBypass':'Did not strip interpretationUses, forge currentness, reinterpret approval JSON as trust, or change screenplay/Runtime.'}
        (HERE/'runtime-blocker-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('signatures','controlBeforeOptIn')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
