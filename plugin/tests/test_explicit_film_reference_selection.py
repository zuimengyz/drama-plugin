"""An exact Host selection survives Film discovery; no qualification is invented."""
from types import SimpleNamespace as NS
import pytest
from drama_plugin.film import media_references as m
from drama_plugin.production.contracts import SourceReference
from drama_plugin.production.references import ReferenceExecutionBinding,ReferenceExecutionStore
from drama_plugin.runtime.contracts import RuntimeScope


def setup(monkeypatch):
    import drama_plugin.creative_engine.sources as sources
    scope=RuntimeScope(work_id='W',scene_id='S',shot_id='K06')
    def ref(name,*path):
        return SourceReference(owner='professional',artifact_ref=name,version=1,fingerprint='a'*64,path=path)
    start=ref('action','content','actionPhases','0','entryState')
    subjects=NS(body=NS(facts={'presentSubjects':[{'id':'actor'}]}))
    world=NS(body=NS(facts={'setting':'same room','time':'dusk'}))
    scene=NS(kind='SCENE',body=NS(dialogue=[]))
    class Native:
        def __init__(self,*a):pass
        def project(self,value):return NS(reference=lambda *p:ref('subjects' if value is subjects else 'world',*p))
    monkeypatch.setattr(sources,'NativeCreativeSources',Native)
    monkeypatch.setattr(m,'professional',lambda p,u,d:subjects if d=='SUBJECTS' else world)
    monkeypatch.setattr(m,'location_context',lambda *a: {'status':'DESIGN_ONLY','locationId':None})
    # Discovery would encounter this incomplete row. Explicit selection must not read it.
    monkeypatch.setattr(m,'production_progress',lambda *a: {'mediaIndex':[{'unselected':'newer flawed media'}]})
    def forbidden(*a,**k):raise AssertionError('EXPLICIT_SELECTION_MUST_NOT_DISCOVER_ASSETS')
    monkeypatch.setattr(m,'asset_reference_candidates',forbidden)
    store=ReferenceExecutionStore()
    p=NS(execution_references=store,creative_versions=NS(resolve=lambda _:scene),
        production_packages=NS(get=lambda _:NS(scope=NS(work=NS(artifact_ref='W')))))
    u=NS(package_ref=None,scene_id='S',shot_id='K06',refs=('scene',))
    selection=NS(start_ref=start,fact_refs=(NS(domain='SUBJECTS',reference=ref('subjects','content','presentSubjects','0','role')),),execution_context=None,spoken_ids=())
    bindings=[]
    for i in range(2):
        use=ref('references','content','references',str(i),'inputDuty')
        b=ReferenceExecutionBinding(binding_id='chosen-'+str(i),version=1,scope=scope,
            source_scope=scope.model_copy(update={'shot_id':'K02' if i==0 else 'K05'}),
            use_ref=use,state_ref=start,authority_refs=(use,),role='REFERENCE',authorization_scope='REVIEWED_TRIAL_INPUT',
            media=dict(media_id='media-'+str(i),version='1',content_hash=str(i+1)*64,kind='image' if i==0 else 'video',
                semantics=('style',) if i==0 else ('prop','continuity'),width=1280,height=720,duration=None if i==0 else 12,review_ref='retained-review'),
            duties=(dict(role='LOOK' if i==0 else 'CONTINUITY',necessity='REQUIRED',subject='room' if i==0 else 'case',purpose='Light baseline' if i==0 else 'Closed case at 9.5 seconds'),))
        bindings.append(store.register(b))
    return p,u,selection,tuple(bindings)


def test_selected_order_hash_and_scoped_duties_survive_without_discovery(monkeypatch):
    p,u,s,refs=setup(monkeypatch)
    refs=refs[::-1]
    result=m.select_references(p,'run',u,s,reference_refs=refs,register=True)
    assert result['bindings']==refs
    assert result['selectionAuthority']=='EXPLICIT_EXECUTION_SELECTION'
    assert [b.media.media_id for b in result['candidates']]==['media-1','media-0']
    assert [b.media.semantics for b in result['candidates']]==[('prop','continuity'),('style',)]
    assert [x['purposes'] for x in result['selected']]==[['CONTINUITY'],['LOOK']]
    assert all(x['endpointFrameRef'] is None for x in result['selected'])
    assert len(p.execution_references._current)==2


def test_another_entry_state_cannot_reuse_old_state_binding(monkeypatch):
    p,u,s,refs=setup(monkeypatch)
    s.start_ref=s.start_ref.model_copy(update={'path':('content','actionPhases','1','entryState')})
    with pytest.raises(ValueError,match='REFERENCE_USE_OUTSIDE_CURRENT_UNIT'):
        m.select_references(p,'run',u,s,reference_refs=refs)


def test_exact_version_not_latest_and_wrong_shot_remains_invalid(monkeypatch):
    p,u,s,refs=setup(monkeypatch)
    from drama_plugin.production.sources import SourceReadError
    with pytest.raises(SourceReadError):
        m.select_references(p,'run',u,s,reference_refs=(refs[0].model_copy(update={'fingerprint':'f'*64}),))
    u.shot_id='K07'
    with pytest.raises(ValueError,match='REFERENCE_BINDING_SCOPE_MISMATCH'):
        m.select_references(p,'run',u,s,reference_refs=refs)
