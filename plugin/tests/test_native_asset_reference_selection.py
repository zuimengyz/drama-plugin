"""Pure producer selection: exact existing uses, no new proof or live IO."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest

from drama_plugin.film import media_references as module
from drama_plugin.production.contracts import SourceReference
from drama_plugin.runtime.contracts import RuntimeScope
from drama_plugin.contracts.base import sha256_canonical
from drama_plugin.production.references import ReferenceExecutionBinding


def fixture(monkeypatch):
    import drama_plugin.creative_engine.sources as sources
    scope = RuntimeScope(work_id='W', scene_id='S01', shot_id='C01')
    def asset(name, kind, subject=None):
        return dict(id=name, assetType=kind, content={'specializedAsset':dict(
            subjectId=subject, stableIdentity='stable-'+name, establishedSceneId='S01', state='ADOPTED',
            adoptionRef=dict(key='native-reference-adoption:'+name, fingerprint='a'*64))},
            resolvedMedia=[dict(mediaId=name+'-media', version='1', contentHash='b'*64,
                mediaType='IMAGE', width=2048, height=2048)])
    # A Scene library contains many valid assets.  Existence is not permission
    # to bind all of them to the current selected action.
    assets = [asset('Y','CHARACTER','yakov'), asset('Y-clothes','COSTUME','yakov'),
              asset('M','CHARACTER','marfa'), asset('M-clothes','COSTUME','marfa'),
              asset('plane','PROP'), asset('board','PROP')]
    assets += [asset('later-'+str(i),'PROP') for i in range(13)]
    subjects = NS(scope=scope, body=NS(facts={
        'presentSubjects':[dict(id='yakov'),dict(id='marfa')], 'assetBindings':assets}))
    world = NS(scope=scope, body=NS(facts={'locationAssetId':'room', 'assetBindings':[asset('room','LOCATION')]}))
    class Native:
        def __init__(self,*args): pass
        def project(self, original):
            key = 'subjects' if original is subjects else 'world'
            return NS(reference=lambda *path:SourceReference(owner='professional',artifact_ref=key,
                version=1,fingerprint=('c' if key=='subjects' else 'd')*64,path=path))
    monkeypatch.setattr(sources,'NativeCreativeSources',Native)
    monkeypatch.setattr(module,'professional',lambda p,u,d:subjects if d=='SUBJECTS' else world)
    native=Native()
    start=SourceReference(owner='professional',artifact_ref='current-action',version=1,
                          fingerprint='e'*64,path=('content','actionPhases','0','entryState'))
    selected=NS(start_ref=start,fact_refs=(NS(domain='SUBJECTS',reference=NS(path=('content','presentSubjects','0','role'))),))
    p=NS(creative_versions=None,execution_references=None)
    unit=NS(refs=())
    use=lambda i:native.project(subjects).reference('content','assetBindings',str(i))
    return p,unit,selected,subjects,world,use


def test_existing_defaults_do_not_select_costumes_or_thirteen_later_props(monkeypatch):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    result=module.asset_reference_candidates(p,u,s)
    assert [b.media.media_id for b in result]==['Y-media','room-media']
    assert result[1].media.review_ref=='asset-adoption:room:'+'a'*64


def test_exact_c01_uses_select_only_current_clothing_plane_and_board(monkeypatch):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    result=module.asset_reference_candidates(p,u,s,asset_use_refs=(use(1),use(4),use(5)))
    assert [b.media.media_id for b in result]==['Y-media','Y-clothes-media','plane-media','board-media','room-media']
    for binding,kind,role,semantics in [(result[1],'Y-clothes','COSTUME',('costume',)),
                                      (result[2],'plane','CONTINUITY',('prop','continuity')),
                                      (result[3],'board','CONTINUITY',('prop','continuity'))]:
        assert binding.media.review_ref=='asset-adoption:'+kind+':'+'a'*64
        assert binding.media.semantics==semantics and binding.subject_ids==()
        assert binding.duties[0].role==role and binding.duties[0].subject=='stable-'+kind
        assert binding.use_ref in binding.authority_refs and binding.state_ref==s.start_ref
        assert binding.source_scope==RuntimeScope(work_id='W',scene_id='S01')
        assert binding.role=='REFERENCE' and not binding.duties[0].establishes_opening_state
    assert module.asset_reference_candidates(p,u,s,asset_use_refs=(use(1),use(4),use(5)))==result


@pytest.mark.parametrize('change',['duplicate','foreign-fingerprint','wrong-version','not-leaf','non-numeric',
                                  'other-actor-costume','outside-library','wrong-owner'])
def test_unselected_or_forged_existing_use_is_rejected(monkeypatch,change):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    chosen=use(1)
    if change=='foreign-fingerprint':chosen=chosen.model_copy(update={'fingerprint':'f'*64})
    if change=='wrong-version':chosen=chosen.model_copy(update={'version':2})
    if change=='not-leaf':chosen=chosen.model_copy(update={'path':('content','assetBindings')})
    if change=='non-numeric':chosen=chosen.model_copy(update={'path':('content','assetBindings','name')})
    if change=='other-actor-costume':chosen=use(3)
    if change=='outside-library':chosen=use(99)
    if change=='wrong-owner':chosen=chosen.model_copy(update={'owner':'work'})
    with pytest.raises(ValueError,match='EXACT_CURRENT_ASSET_USE_REQUIRED'):
        module.asset_reference_candidates(p,u,s,asset_use_refs=(chosen,chosen) if change=='duplicate' else (chosen,))


@pytest.mark.parametrize('state',['CANDIDATE','REVIEWED','REJECTED',None])
def test_failed_or_unadopted_room_cannot_become_a_reference(monkeypatch,state):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    world.body.facts['assetBindings'][0]['content']['specializedAsset']['state']=state
    with pytest.raises(ValueError,match='ASSET_REFERENCE_ADOPTION_REQUIRED'):
        module.asset_reference_candidates(p,u,s,asset_use_refs=(use(1),use(4),use(5)))


@pytest.mark.parametrize('change',['empty','missing','video','unprobed'])
def test_explicit_required_asset_use_cannot_disappear_without_an_image(monkeypatch,change):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    asset=subjects.body.facts['assetBindings'][4]
    if change=='empty':asset['resolvedMedia']=[]
    if change=='missing':asset.pop('resolvedMedia')
    if change=='video':asset['resolvedMedia'][0]['mediaType']='VIDEO'
    if change=='unprobed':
        asset['resolvedMedia'][0]['width']=None
        def absent_probe(*args):raise ValueError('ASSET_REFERENCE_PROBE_REQUIRED')
        monkeypatch.setattr(module,'native_reference_dimensions',absent_probe)
    with pytest.raises(ValueError,match='ASSET_REFERENCE_(PROBE|IMAGE)_REQUIRED'):
        module.asset_reference_candidates(p,u,s,asset_use_refs=(use(4),))


def test_new_location_pointer_does_not_rewrite_existing_immutable_binding(monkeypatch):
    p,u,s,subjects,world,use=fixture(monkeypatch)
    binding=module.asset_reference_candidates(p,u,s)[1]
    old_pointer='native-reference-adoption:room:'+'a'*64
    old_identity='asset-'+sha256_canonical([binding.scope.model_dump(mode='json',by_alias=True),
        'room','room-media',binding.use_ref.model_dump(mode='json',by_alias=True),
        s.start_ref.model_dump(mode='json',by_alias=True)])
    legacy=ReferenceExecutionBinding.model_validate({**binding.model_dump(), 'binding_id':old_identity,
        'media':{**binding.media.model_dump(),'review_ref':old_pointer}})
    assert legacy.binding_id!=binding.binding_id
    assert legacy.media.review_ref==old_pointer and binding.media.review_ref.startswith('asset-adoption:room:')
    assert legacy.media.media_id==binding.media.media_id and legacy.media.content_hash==binding.media.content_hash
