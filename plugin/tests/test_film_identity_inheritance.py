"""Selected world/look inheritance; synthetic contracts, not model creativity."""
from copy import deepcopy
import json

import pytest

from drama_plugin.contracts.base import dump_contract
from drama_plugin.creative_engine.screenplay import ContextOriginal
from drama_plugin.creative_engine.direction_narrative import native_director_narrative
from drama_plugin.creative_engine.author_projection import author_payload
from drama_plugin.creative_engine.film_identity import identity_view, resolve_identity
from drama_plugin.professional_design.resolver import ProfessionalDesignResolver
from test_director_narrative_handoff import workshop, selected_writer, generic_request, TextOnlyAuthor, isolated
from test_formal_author_backends import request
from test_professional_continuity import look


def original(w, label, text, work='fixture'):
    return w.retain_context(ContextOriginal(work_id=work, label=label, status='AUTHOR_CONCEPT', text=text))


def selected(w, pin, *, look_text='Limited chroma; readable skin; daylight may brighten.'):
    return w.bind_professional_context(pin, work_id='fixture', scene_id=None, design_refs=(),
        world_ref=original(w,'world','Era inferred; exact year and town unresolved. One street-facing room.'),
        look_ref=original(w,'look',look_text),
        analysis_ref=original(w,'analysis','Publication year does not establish story year.'),
        scene_state_refs={'one':original(w,'night','Autumn before dawn; oil lamp east of actor.'),
                          'two':original(w,'day','Same autumn day after sunrise; unchanged east window.'),
                          'three':original(w,'spring','Next spring morning at graves; deliberate red flower exception.')},
        reason='Host selects this experimental basis, not formal adoption.')


async def test_selected_prose_reaches_film_scene_shot_and_professional(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w); before=w.objects.read_ref(pin)
    bound=selected(w,pin); context=w.objects.read_ref(bound)
    unused=original(w,'unselected','UNSELECTED_SATURATED_NOON')
    req=generic_request(context); author=TextOnlyAuthor()
    result=await native_director_narrative(w,author,req,operation='identity')
    film=author.calls[0][1]
    assert film['filmIdentity']['world']['text'].startswith('Era inferred')
    assert film['filmIdentity']['sourceAnalysis']['text'].startswith('Publication')
    assert set(film['filmIdentity']['scenes'])=={'one','two','three'}
    for _, packet in author.calls[1:]:
        assert len(packet['filmIdentity']['scenes'])==1
        assert packet['filmIdentity']['look']['text'].startswith('Limited chroma')
    pro=request('professional').model_copy(update={'scope':request().scope.model_copy(update={'work_id':'fixture','scene_id':'one'}),
        'screenplay_context':result,'professional_context':w.professional_context(result,work_id='fixture',scene_id='one')})
    wire=author_payload(pro)
    assert wire['hostScreenplay']['filmIdentity']['scenes']==identity_view(result,'one')['scenes']
    assert 'UNSELECTED_SATURATED_NOON' not in json.dumps(wire)
    assert 'Next spring' not in json.dumps(wire['hostScreenplay']['filmIdentity'])
    assert ProfessionalDesignResolver.continuity_design_refs(pro)==[context['filmIdentity']['ref']]
    assert w.objects.read_ref(pin)==before
    assert result['directorNarrative']['film']['basis']['filmIdentityFingerprint']==context['filmIdentity']['ref']['fingerprint']
    assert context['filmIdentity']['ref'] in result['directorNarrative']['film']['sourceRefs']
    assert w.objects.read_ref(unused)['text']=='UNSELECTED_SATURATED_NOON'


async def test_new_look_requires_new_selection_not_mixed_history(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w); old=selected(w,pin)
    old_context=w.objects.read_ref(old)
    r=generic_request(old_context);a=TextOnlyAuthor()
    retained=await native_director_narrative(w,a,r,operation='old')
    handoff=w.objects.put('old-narrative',retained)
    new=selected(w,handoff,look_text='Expressionist scarlet sky; deliberate unreal light.')
    changed=w.objects.read_ref(new);r.screenplay_context=changed
    with pytest.raises(ValueError,match='basis changed'):
        await native_director_narrative(w,a,r,operation='new')
    # Explicit Host selection can retain the same prose under the new basis.
    reselected=w.bind_director_narrative(new,work_id='fixture',scene_id=None,
        film_text='Host adopts this expressive visual candidate for experiment.',reason='Explicit re-selection')
    r.screenplay_context=w.objects.read_ref(reselected)
    new_context=await native_director_narrative(w,a,r,operation='new-selected')
    assert identity_view(new_context)['look']['text'].startswith('Expressionist')
    assert 'Limited chroma' not in json.dumps(identity_view(new_context))
    assert w.objects.read_ref(old)==old_context
    assert ProfessionalDesignResolver.creative_input_fingerprint(request('professional').model_copy(update={
        'professional_context':w.professional_context(old_context,work_id='fixture',scene_id='one')})) != ProfessionalDesignResolver.creative_input_fingerprint(request('professional').model_copy(update={
        'professional_context':w.professional_context(changed,work_id='fixture',scene_id='one')}))


@pytest.mark.parametrize('bad', ['body','scope','original','other-work'])
def test_fingerprints_and_work_scope(tmp_path,bad):
    w=workshop(tmp_path);pin=selected_writer(w);bound=selected(w,pin);c=deepcopy(w.objects.read_ref(bound))
    if bad=='body': c['filmIdentity']['selectionReason']='Forged'
    elif bad=='original': c['filmIdentity']['originals']['world']['original']['text']='Forged'
    if bad=='other-work':
        with pytest.raises(ValueError,match='work mismatch'):
            w.bind_professional_context(pin,work_id='fixture',scene_id=None,design_refs=(),
                world_ref=original(w,'foreign','Other work','other'),reason='No')
    else:
        with pytest.raises(ValueError,match='mismatch'):
            resolve_identity(w,c,work_id='other' if bad=='scope' else 'fixture',scene_id='one')


async def test_structured_look_reaches_treatment_and_cannot_mix(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w)
    look_ref=w.objects.put('structured',dump_contract(look('fixture')))
    bound=w.bind_professional_context(pin,work_id='fixture',scene_id=None,design_refs=(look_ref,))
    a=TextOnlyAuthor()
    await native_director_narrative(w,a,generic_request(w.objects.read_ref(bound)),operation='typed-look')
    assert a.calls[0][1]['filmLook'][0]['grammarRules'][0]['execution']=='Warm dominant space, neutral skin'
    with pytest.raises(ValueError,match='one Film Look'):
        w.bind_professional_context(bound,work_id='fixture',scene_id=None,design_refs=(look_ref,),
            look_ref=original(w,'prose','Another baseline'),reason='Conflicting')


def test_old_inputs_and_explicit_scene_exception(tmp_path):
    w=workshop(tmp_path);pin=selected_writer(w);before=w.objects.read_ref(pin)
    assert resolve_identity(w,before,work_id='fixture',scene_id=None) is None
    assert identity_view(before)=={}
    assert 'filmIdentity' not in w.professional_context(before,work_id='fixture',scene_id=None)
    bound=selected(w,pin);c=w.objects.read_ref(bound)
    assert 'deliberate red flower exception' in identity_view(c,'three')['scenes']['three']['text']
    assert 'red flower' not in json.dumps(identity_view(c,'one'))
    assert w.objects.read_ref(pin)==before


def test_complete_snapshot_receipt_is_visible_but_not_author_input(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w); first=selected(w,pin)
    old=w.objects.read_ref(first); refs=old['filmIdentity']['originals']
    from drama_plugin.contracts.source_pin import SourcePin
    world=SourcePin.model_validate(refs['world']['ref'])
    replacement=original(w,'replacement-look','Violet shadows only where scene explicitly selects them.')
    updated=w.bind_professional_context(first,work_id='fixture',scene_id=None,design_refs=(),
        world_ref=world,look_ref=replacement,scene_state_refs={},reason='Retain world, replace look, remove states and analysis.')
    body=w.objects.read_ref(updated);changes=body['filmIdentityChanges']['references']
    assert changes['world']['change']=='RETAINED'
    assert changes['look']=={'change':'REPLACED','before':refs['look']['ref'],'after':dump_contract(replacement)}
    assert changes['sourceAnalysis']['change']=='REMOVED'
    assert changes['scene:one']['after'] is None
    from drama_plugin.creative_engine.author_projection import screenplay_view
    assert 'filmIdentityChanges' not in screenplay_view(body)
    assert refs['look']['ref']['fingerprint'] not in json.dumps(screenplay_view(body))
    # Complete empty selection is explicit, legacy design-only rebinding is not a cancellation.
    cleared=w.bind_professional_context(updated,work_id='fixture',scene_id=None,design_refs=(),
        scene_state_refs={},reason='Host explicitly clears the experimental baseline.')
    assert set(v['change'] for v in w.objects.read_ref(cleared)['filmIdentityChanges']['references'].values())=={'REMOVED'}
    unchanged=w.bind_professional_context(updated,work_id='fixture',scene_id=None,design_refs=())
    assert 'filmIdentityChanges' not in w.objects.read_ref(unchanged)
    assert w.objects.read_ref(unchanged)['filmIdentity']==body['filmIdentity']
    assert w.objects.read_ref(first)==old


async def test_cold_director_candidate_requires_explicit_world_selection(tmp_path):
    w=workshop(tmp_path); pin=selected_writer(w); original_packet=w.objects.read_ref(pin)
    class Candidate(TextOnlyAuthor):
        async def film_treatment(self, request, packet):
            from drama_plugin.creative_engine.backends import HostSceneOriginal
            self.calls.append(('film',deepcopy(packet)))
            return HostSceneOriginal(text='WORLD CANDIDATE: unnamed town, year unresolved. LOOK CANDIDATE: shared space, limited chroma.')
    a=Candidate();first=await native_director_narrative(w,a,generic_request(original_packet),operation='cold')
    assert 'filmIdentity' not in a.calls[0][1] and 'filmLook' not in a.calls[0][1]
    assert 'filmIdentity' not in first
    assert first['directorNarrative']['film']['selectedBy']=='DIRECTOR_AUTHOR_CANDIDATE'
    assert first['directorNarrative']['film']['formalAdoption'] is False
    retained=w.objects.put('candidate-handoff',first)
    bound=selected(w,retained)
    bound=w.bind_director_narrative(bound,work_id='fixture',scene_id=None,
        film_text=first['directorNarrative']['film']['text'],reason='Host selects candidate as experimental basis.')
    second=await native_director_narrative(w,a,generic_request(w.objects.read_ref(bound)),operation='selected')
    assert second['directorNarrative']['film']['selectedBy']=='HOST'
    assert second['directorNarrative']['film']['formalAdoption'] is False
    assert 'filmIdentity' in a.calls[-1][1]
    assert second['screenplay']==original_packet['screenplay']
    assert w.objects.read_ref(retained)==first


async def test_existing_binding_tool_exposes_optional_receipt_without_breaking_pin(tmp_path):
    from drama_plugin.creative_engine.screenplay import register_screenplay_tools
    from drama_plugin.tools.registry import ToolRegistry
    from drama_plugin.contracts.source_pin import SourcePin
    w=workshop(tmp_path);registry=ToolRegistry();register_screenplay_tools(registry,w)
    first=selected(w,selected_writer(w))
    before=w.objects.read_ref(first)
    retained=SourcePin.model_validate(before['filmIdentity']['originals']['world']['ref'])
    result=await registry.invoke('screenplay.bind_professional_context',handoff_ref=first,
        work_id='fixture',scene_id=None,design_refs=(),world_ref=retained,
        reason='Keep world; deliberately omit look.',include_selection_changes=True)
    rows=result['filmIdentityChanges']['references']
    assert rows['look']['change']=='REMOVED' and rows['world']['change']=='RETAINED'
    pin=SourcePin.model_validate(result['handoffRef'])
    assert w.objects.read_ref(pin)['filmIdentityChanges']==result['filmIdentityChanges']
    old_style=await registry.invoke('screenplay.bind_professional_context',handoff_ref=pin,
        work_id='fixture',scene_id=None,design_refs=())
    assert isinstance(old_style,SourcePin)
    unchanged=await registry.invoke('screenplay.bind_professional_context',handoff_ref=old_style,
        work_id='fixture',scene_id=None,design_refs=(),include_selection_changes=True)
    assert unchanged['filmIdentityChanges'] is None
    assert all(r['change']=='ADDED' for r in before['filmIdentityChanges']['references'].values())
