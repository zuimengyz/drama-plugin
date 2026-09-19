"""NON_NORMATIVE_EXAMPLE: fabricated bytes test guards, not semantic runtime."""
from copy import deepcopy
import json
import pytest

from drama_plugin.hosts.temporal_observer import reconcile, file_hash
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.contracts.adaptive_direction import ObservedMaterialEvidence

@pytest.fixture
def receipt(tmp_path):
    media = tmp_path/'media'; media.write_bytes(b'isolated test media bytes')
    frame = tmp_path/'frame'; frame.write_bytes(b'isolated test frame bytes')
    audio = tmp_path/'audio'; audio.write_bytes(b'isolated test audio bytes')
    samples = [dict(id=f'F{i}', timestamp=i*.5, file=str(frame), sha256=file_hash(str(frame))) for i in range(5)]
    m = dict(mediaId='test-only',mediaPath=str(media),sourceHash=file_hash(str(media)),duration=2.,timebase='seconds',windows=[dict(order=1,samples=samples)],inputFields=['media','orderedSamples','neutralObservationSchema'],neutralInstruction='Visible facts only')
    f = lambda key, domain, text, start, end, refs: dict(id=key,domain=domain,text=text,start=start,end=end,visualEvidenceRefs=refs,confidence=.95)
    v = dict(sourceHash=m['sourceHash'],version='fixture',method={'observer':'structured test, no real observation'},inputManifestHash='a'*64,windows=[dict(start=0,end=2,facts=[f('s','visible_subjects','Two people',0,0,['F0']),f('a','actions','First hand rises',0,.5,['F0','F1']),f('b','action_order','Second hand lowers',1,1.5,['F2','F3']),f('p','spatial_relations','One person left of other',0,0,['F0'])])],uncertainObservations=[f('u','gaze','UNKNOWN: exact eye target',0,0,['F0'])])
    a = dict(sourceHash=m['sourceHash'],audioRef=str(audio),audioHash=file_hash(str(audio)),method='TEMPORAL_AUDIO_SEMANTIC',decodedDuration=2.,timebase={'offsetSeconds':0},semanticEvents=[dict(id='sound',start=.2,end=.4,layer='OTHER_SOUND_EVENT',text='Fixture stipulated sound',audioEvidenceRefs=[file_hash(str(audio))],confidence='MEDIUM')])
    r = dict(sourceHash=m['sourceHash'],visualFingerprint=sha256_canonical(v),audioFingerprint=sha256_canonical(a),confirmedVisualIds=['s','a','b','p'],confirmedAudioIds=['sound'],audioTimebaseVerified=True,inputContextAudited=True,observerIsIndependent=True,providedUpstreamAnswers=[])
    return m,v,a,r

def run(parts):
    return reconcile(*parts,manifest_file_hash='a'*64)

@pytest.mark.parametrize('description',[
    ('Two seated people and letter','Recipient raises letter','Recipient lowers letter'),
    ('Two people beside basket','Carrier raises handle','Receiver lowers basket'),
    ('People moving beside a wall','Front group enters gap','Rear group follows')])
def test_cross_work_ordered_fusion(receipt,description):
    m,v,a,r=receipt
    for fact,text in zip(v['windows'][0]['facts'][:3],description):fact['text']=text
    r['visualFingerprint']=sha256_canonical(v)
    out=run(receipt)
    assert out['LV0']=='PASS' and out['fullAVSemanticFusion']
    assert out['events'][1]['audio'][0]['id']=='sound'
    assert out['events'][2]['audio']=='UNRESOLVED'
    assert not out['formalMediaAuthorized'] and out['writes']==0

@pytest.mark.parametrize('method',['VAD_ONLY_NOT_FULL_AUDIO_SEMANTICS','ASR_ONLY','TECHNICAL'])
def test_narrow_audio_cannot_pass(receipt,method):
    receipt[2]['method']=method
    out=run(receipt)
    assert out['gates']['AUDIO']=='FAIL' and out['LV0']=='PARTIAL_CAPABILITY'
    assert not out['fullAVSemanticFusion']

def test_missing_audio(receipt):
    m,v,a,r=receipt
    assert run((m,v,None,r))['gates']['AUDIO']=='FAIL'

@pytest.mark.parametrize('defect',['no-visual','unordered','source','frame-hash','visual-ref','audio-ref','confidence','nan','window-gap','intent-field','context-leak','stale-review','manifest','audio-time','single-action-frame','reversed-fact-refs'])
def test_negative_provenance(receipt,defect):
    m,v,a,r=receipt
    if defect=='no-visual':v['windows']=[]
    if defect=='unordered':m['windows'][0]['samples'].reverse()
    if defect=='source':m['sourceHash']='f'*64
    if defect=='frame-hash':m['windows'][0]['samples'][0]['sha256']='f'*64
    if defect=='visual-ref':v['windows'][0]['facts'][0]['visualEvidenceRefs']=[]
    if defect=='audio-ref':a['semanticEvents'][0]['audioEvidenceRefs']=[]
    if defect=='confidence':v['windows'][0]['facts'][0]['confidence']=2
    if defect=='nan':v['windows'][0]['facts'][0]['start']=float('nan')
    if defect=='window-gap':v['windows'][0]['start']=.5
    if defect=='intent-field':m['expectedAction']='Answer supplied'
    if defect=='context-leak':r['providedUpstreamAnswers']=['old judgment']
    if defect=='manifest':v['inputManifestHash']='b'*64
    if defect=='audio-time':a['semanticEvents'][0]['end']=3
    if defect=='single-action-frame':v['windows'][0]['facts'][1]['visualEvidenceRefs']=['F0']
    if defect=='reversed-fact-refs':v['windows'][0]['facts'][1]['visualEvidenceRefs'].reverse()
    if defect not in ('stale-review','nan'):r['visualFingerprint']=sha256_canonical(v)
    if defect=='stale-review':v['windows'][0]['facts'][0]['text']='tampered'
    r['audioFingerprint']=sha256_canonical(a)
    with pytest.raises(ValueError):run(receipt)

def test_unsupported_event_becomes_unknown(receipt):
    receipt[3]['confirmedVisualIds'].remove('a')
    out=run(receipt)
    assert out['gates']['VISUAL']=='FAIL'
    assert any(f['id']=='a' and f['status']=='UNKNOWN' for f in out['unknown'])

def test_silent_temporal_contract_not_av(receipt):
    raw=dict(key='fact',basis='OBSERVED_MEDIA',mediaRef='noncanonical',mediaHash='a'*64,shotRef='NON_CANONICAL:NO_SHOT',sceneId='NON_CANONICAL:NO_SCENE',coverageRefs=['NON_CANONICAL:NONE'],directorIntentRefs=['NON_CANONICAL:NONE'],start=0,end=2,facts={'action_order':['[0–1.5] first then second; F0,F1,F2,F3']},observationConfidence='HIGH',observerType='VERIFIED_MULTIMODAL_RUNTIME',method='TEMPORAL_VISUAL',evidenceRefs=[dict(key='reviewed-temporal-evidence',kind='MEDIA',fingerprint='a'*64)],factReviewRef=dict(key='independent-factual-review',kind='DIRECTION',fingerprint='b'*64))
    assert ObservedMaterialEvidence(**raw).method=='TEMPORAL_VISUAL'
    raw['facts']['audio_events']=['inferred words']
    with pytest.raises(ValueError):ObservedMaterialEvidence(**raw)
