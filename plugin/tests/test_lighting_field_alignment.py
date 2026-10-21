from copy import deepcopy
import pytest
from drama_plugin.creative_engine.contracts import AuthorRequest, DesignBody, SourceBody
from drama_plugin.creative_engine.store import CreativeVersionStore
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from drama_plugin.professional_design.lighting_fields import align_lighting_fields
from drama_plugin.runtime.contracts import RuntimeScope


def test_new_persist_aligns_lighting_without_mutating_original(tmp_path):
    store=CreativeVersionStore(tmp_path/'owners')
    req=AuthorRequest(scope=RuntimeScope(work_id='w',scene_id='s',shot_id='k'),source=SourceBody(goal='Light continuity',text='Same room.',spoken_language='en'),source_refs=())
    raw=DesignBody(domain='LIGHTING',facts={'motivatedSources':['Warm practical key; weak window fill.'],'negativeConstraints':['No new key.'],'directionAndQuality':'Face readable.','intensityRatios':{'keyToFill':'Warm dominant.'}})
    before=deepcopy(raw)
    ref=ProfessionalDesignResolver(None).persist(store,req,raw,operation='lighting-alignment')
    actual=store.resolve(ref).body.facts
    assert actual['sources']==raw.facts['motivatedSources'] and actual['constraints']==raw.facts['negativeConstraints']
    assert not {'motivatedSources','negativeConstraints'} & actual.keys()
    assert raw==before and actual['intensityRatios']==raw.facts['intensityRatios']
    reopened=CreativeVersionStore(tmp_path/'owners').resolve(ref)
    assert reopened.ref()==ref


def test_conflicting_alias_is_not_silently_overwritten():
    with pytest.raises(ValueError,match='LIGHTING_FIELD_CONFLICT'):
        align_lighting_fields(DesignBody(domain='LIGHTING',facts={'sources':'Warm key','motivatedSources':'Cold key'}))


@pytest.mark.parametrize('domain,facts',[('CAMERA',{'motivatedSources':'Retained unrelated content'}),('LIGHTING',{'sources':'Warm key','constraints':['No added light']})])
def test_other_domains_and_aligned_lighting_unchanged(domain,facts):
    body=DesignBody(domain=domain,facts=facts)
    assert align_lighting_fields(body) is body


def test_direct_new_owner_write_also_aligns_fields(tmp_path):
    from drama_plugin.creative_engine.contracts import Authority, Kind
    store = CreativeVersionStore(tmp_path/'owners')
    body = DesignBody(domain='LIGHTING', facts={'motivatedSources':['Warm practical key.'], 'negativeConstraints':['No spotlight.']})
    ref = store.write(writer=Authority.PROFESSIONAL, kind=Kind.PROFESSIONAL,
        scope=RuntimeScope(work_id='w', scene_id='s', shot_id='k'), body=body,
        sources=(), operation='direct-lighting-candidate')
    facts = store.resolve(ref).body.facts
    assert facts['sources'] == body.facts['motivatedSources']
    assert facts['constraints'] == body.facts['negativeConstraints']
    assert 'motivatedSources' not in facts and 'negativeConstraints' not in facts
