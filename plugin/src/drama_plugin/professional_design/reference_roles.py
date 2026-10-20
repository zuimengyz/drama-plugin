"""Asset reference duties are independent of image adoption and revision order."""
from drama_plugin.contracts.base import dump_contract, sha256_canonical, canonical_json
from drama_plugin.contracts.source_pin import SourcePin
from drama_plugin.runtime.contracts import ArtifactReference
from drama_plugin.persistence.review import UserDecisionRecord


def selection_subject(packet):
    return ArtifactReference(owner='asset-reference-selection',
        artifact_ref='asset-reference-selection:'+sha256_canonical(packet), version=1)


def read_selection(sequence, identity):
    path=sequence.objects._path('asset-reference-selection', identity)
    if not path.exists():return None
    pin=SourcePin.model_validate(sequence.objects._read(path))
    original=sequence.objects.read_ref(pin)
    decision_ref=ArtifactReference.model_validate(original['decisionRef'])
    ledger=sequence.reference_production.ledger
    raw,scope,fingerprint=ledger.get_artifact('user-decision',decision_ref)
    decision=UserDecisionRecord.model_validate(raw)
    packet=original['selection']
    if (decision.artifact_reference()!=decision_ref or decision.fingerprint!=fingerprint
            or not decision.accepted or decision.category.value!='ADOPTION'
            or decision.scope!=scope or scope.work_id!=packet['workId']
            or decision.source_ref!=selection_subject(packet) or packet['identity']!=identity):
        raise ValueError('ASSET_REFERENCE_SELECTION_AUTHORITY_MISMATCH')
    return original


def reference_role(sequence, asset):
    s=asset.content['specializedAsset']
    selected=read_selection(sequence,s['stableIdentity'])
    if selected:
        for item in selected['selection']['assets']:
            if item['assetId']==asset.id:
                if any(item[k]!=s[k] for k in ('designRef','adoptionRef')):
                    raise ValueError('ASSET_REFERENCE_SELECTION_PIN_MISMATCH')
                return item['role']
    return s.get('referenceRole','BASELINE')


async def retain_selection(sequence, packet, decision_ref):
    """Correct an exact named baseline/supplement selection, retaining all originals."""
    from drama_plugin.execution.reference_delivery import native_asset_originals
    from drama_plugin.professional_design.reference_production import ReferenceProductionRecord
    if (packet.get('schemaVersion')!='asset-reference-selection-v1' or not packet.get('reason')
            or len({x['assetId'] for x in packet['assets']})!=len(packet['assets'])
            or [x['role'] for x in packet['assets']].count('BASELINE')!=1
            or any(x['role'] not in {'BASELINE','SUPPLEMENT'} for x in packet['assets'])):
        raise ValueError('ASSET_REFERENCE_SELECTION_INVALID')
    ledger=sequence.reference_production.ledger
    raw,scope,fingerprint=ledger.get_artifact('user-decision',decision_ref)
    decision=UserDecisionRecord.model_validate(raw)
    if (decision.artifact_reference()!=decision_ref or decision.scope!=scope or decision.fingerprint!=fingerprint
            or not decision.accepted or decision.category.value!='ADOPTION'
            or scope.work_id!=packet['workId'] or decision.source_ref!=selection_subject(packet)):
        raise ValueError('ASSET_REFERENCE_SELECTION_AUTHORITY_MISMATCH')
    for item in packet['assets']:
        asset=await sequence.assets.get_asset(item['assetId']);s=asset.content['specializedAsset']
        if (asset.work_id!=packet['workId'] or s['stableIdentity']!=packet['identity']
                or any(item[k]!=s[k] for k in ('designRef','adoptionRef'))):
            raise ValueError('ASSET_REFERENCE_SELECTION_PIN_MISMATCH')
        proof=native_asset_originals(ledger,sequence.objects,asset)
        record=ReferenceProductionRecord.model_validate(proof['referenceRecord'])
        sequence.reference_production.adopted_reference(record,proof['adoptionOriginal'],tuple(asset.reference_media_ids))
    original={'selection':packet,'decisionRef':dump_contract(decision_ref)}
    pin=sequence.objects.put('asset-reference-selection:'+sha256_canonical(original),original)
    with sequence.objects._writer():
        sequence.objects._write(sequence.objects._path('asset-reference-selection',packet['identity']),dump_contract(pin))
    if sequence.film_storage is not None:
        sequence.film_storage.outbox.enqueue({'kind':'ASSET_REFERENCE_SELECTION','workId':packet['workId'],'ref':dump_contract(pin)})
    return pin


async def project_selection(store, pin, event, order):
    sequence=store.plugin.asset_sequence
    original=sequence.objects.read_ref(pin);packet=original['selection']
    if read_selection(sequence,packet['identity'])!=original:
        return  # Superseded correction event is history, never a new selection.
    baseline=next(x for x in packet['assets'] if x['role']=='BASELINE')
    rows=[]
    for item in packet['assets']:
        asset=await sequence.assets.get_asset(item['assetId']);s=asset.content['specializedAsset']
        reference_role(sequence,asset)  # exact immutable design/adoption pins
        rows.append(store.row('drama_asset',event,order,id=asset.id,state='ADOPTED',
            adoption_ref=canonical_json(s['adoptionRef'])))
        scene=packet.get('sceneId') or s.get('sceneId') or s.get('establishedSceneId')
        if scene:rows.append(store.row('drama_scene_asset',event,order,scene_id=scene,asset_id=asset.id,
            purpose='CHARACTER_IDENTITY' if item['role']=='BASELINE' else 'SUPPLEMENTAL_APPEARANCE',source_ref=str(pin.model_dump_json())))
    primary=await sequence.assets.get_asset(baseline['assetId'])
    subject=primary.content['specializedAsset'].get('subjectId')
    if subject:rows.append(store.row('drama_character',event,order,id=subject,adopted_asset_id=primary.id))
    await store.client.rows(rows)
    if subject:
        selected=await store.client.query('drama_character',{'id':subject},1)
        if len(selected)!=1 or selected[0]['adopted_asset_id']!=primary.id:
            raise ValueError('ASSET_REFERENCE_SELECTION_READBACK_MISMATCH')
    for item in packet['assets']:
        current=await store.client.query('drama_asset',{'id':item['assetId']},1)
        if len(current)!=1 or current[0]['state']!='ADOPTED':raise ValueError('ASSET_REFERENCE_SELECTION_READBACK_MISMATCH')
