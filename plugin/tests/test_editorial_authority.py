from copy import deepcopy
import pytest
from pydantic import ValidationError
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.editorial_authority import EditorialAuthority, EditorialUsability, CompressionCandidate
from drama_plugin.contracts.sequence import FilmReview
from drama_plugin.editorial import editorial_handoff, cut_verdict, usability_handoff, compression_verdict

CASES=[('court','The recipient reads the seal before answering','sender—recipient table axis','receiver puts the letter down'),
       ('civilian','Two neighbors exchange a basket without dropping its load','door—stall walking axis','receiver takes the weight'),
       ('different-battle','Defenders withdraw behind an opened gate before it closes','gate—courtyard axis','last defender clears the threshold')]
def fixture(case):
    name,action,axis,event=case;p=dict(key=name,kind='DIRECTION',fingerprint='a'*64)
    q=dict(key=name+'-requirement',intent=dict(scene_id=name,director_intent_id=name+'-intent',source_authority=[p],protected_priority_ids=['fact','choice'],may_compress='Only already redundant duration',may_omit='Secondary decoration',cannot_reorder=[action,event]),required_coverage=[name+'-view'],redundant_coverage=['Individual reverse views when both receivers are readable'],forbidden_substitute=['A decorative insert replacing the receiver'],protected_action=action,protected_reaction=event,reaction_class='REQUIRED_REACTION',spatial_requirement=axis,audio_requirement='Preserve the source action sound',coverage_risk='MEDIUM',risk_reason='Shared timing must be visible',minimum_coverage_count=1,cut=dict(key=name+'-cut',cut_allowed_when=[event],cut_prohibited_when=['Receiver has not completed the action'],hold=dict(key=name+'-hold',event_sequence=[action,event],hold_until=event,premature_exit_risk='Relation change becomes invisible'),reaction_required_before_exit=event,spatial_reset_required='Re-establish the same landmarks after a motivated crossing',audio_continuity_required='Same space ambience'),music_policy='BLOCKED',music_entry='No score',music_exit='Before the protected exchange',performance_source_refs=[name+'-performance'])
    return dict(work_id=name,scene_order=[name],source_authority=[p],coverage_units=[dict(key=name+'-view',scene_id=name,necessity='REQUIRED',evidence_function=action,simultaneous_duties=[action,event],missing_consequence='No evidence of receipt',source_authority=[p])],requirements=[q])

@pytest.mark.parametrize('case',CASES)
def test_cross_work_minimum_and_order(case):
    a=EditorialAuthority(**fixture(case));q=a.requirements[0]
    h=editorial_handoff(a,{case[0]:'a'*64},{case[0]+'-intent':{'fact':'P0','choice':'P1','framing':'P2'}})
    assert h['requiredCoverageUnits']==1 and not h['mediaExecutable'] and h['removalWitnesses']
    assert cut_verdict(q,q.cut.hold.event_sequence[:-1],reaction_complete=True,spatial_ready=True,audio_ready=True)=='CUT_PROHIBITED'
    assert cut_verdict(q,q.cut.hold.event_sequence,reaction_complete=True,spatial_ready=True,audio_ready=True)=='CUT_ALLOWED_BY_DECLARED_EVIDENCE'
    assert cut_verdict(q,tuple(reversed(q.cut.hold.event_sequence)),reaction_complete=True,spatial_ready=True,audio_ready=True)=='CUT_PROHIBITED'
    for state in ['P0','P1','P2']:
        assert cut_verdict(q,q.cut.hold.event_sequence,reaction_complete=True,spatial_ready=True,audio_ready=True,priority_impact=state)=='UPSTREAM_AUTHORITY_REQUIRED'
    assert cut_verdict(q,q.cut.hold.event_sequence,reaction_complete=None,spatial_ready=True,audio_ready=True)=='CUT_PROHIBITED'

@pytest.mark.parametrize('defect',['unknown-unit','extra-unit','count','orphan-scene','optional-no-condition','duplicate-intent','wrong-priority','stale-source'])
def test_malformed_or_inflated_plan_fails(defect):
    raw=fixture(CASES[0]);q=raw['requirements'][0]
    if defect=='unknown-unit':q['required_coverage']=['absent']
    if defect=='extra-unit':raw['coverage_units'].append({**raw['coverage_units'][0],'key':'unused'})
    if defect=='count':q['minimum_coverage_count']=2
    if defect=='orphan-scene':q['intent']['scene_id']='another'
    if defect=='optional-no-condition':raw['coverage_units'][0]['necessity']='OPTIONAL'
    if defect=='duplicate-intent':raw['requirements'].append(deepcopy(q))
    if defect=='wrong-priority':q['intent']['protected_priority_ids']=['fact']
    with pytest.raises(ValueError):
        a=EditorialAuthority(**raw);editorial_handoff(a,{'court':'b'*64 if defect=='stale-source' else 'a'*64},{'court-intent':{'fact':'P0','choice':'P1'}})

def usability():
    return dict(asset_ref='fixture-media',media_hash='a'*64,scene_id='court',director_intent_ids=['court-intent'],usable_ranges=[dict(start=0,end=2,functions=['receiver'])],covered_requirements=['court-requirement'],continuity_status='PASS',axis_status='PASS',performance_status='PASS',audio_status='PASS',editorial_usability='USABLE_FULL',evidence_refs=['fixture-observation'],basis='SYNTHETIC_FIXTURE')

@pytest.mark.parametrize('defect',['unknown','missing','ranges','covered','pickup','repair','retake','range-order'])
def test_usability_is_not_a_label_only(defect):
    r=usability()
    if defect=='unknown':r['audio_status']='UNKNOWN'
    if defect=='missing':r['missing_requirements']=['exit']
    if defect=='ranges':r['usable_ranges']=[]
    if defect=='covered':r['covered_requirements']=[]
    if defect=='pickup':r['editorial_usability']='NEEDS_PICKUP'
    if defect=='repair':r['editorial_usability']='EDITORIAL_REPAIRABLE'
    if defect=='retake':r.update(editorial_usability='UNUSABLE',repair_options=[dict(kind='RETAKE_REQUIRED_UPSTREAM',scope='source',preserves=['other material'],evidence_ref='e')])
    if defect=='range-order':r['usable_ranges'][0]['end']=0
    with pytest.raises(ValidationError):EditorialUsability(**r)

def test_outside_intent_never_adopts_and_changed_hash_fails():
    r=EditorialUsability(**{**usability(),'outside_approved_intent':True})
    assert usability_handoff(r,'a'*64)=={'status':'OUTSIDE_APPROVED_INTENT','next':'REQUIRES_ADAPTIVE_DIRECTOR_REVIEW','adopt':False}
    with pytest.raises(ValueError):usability_handoff(r,'b'*64)

def test_observed_claim_requires_matching_av_ranges_and_legacy_unchanged():
    r={**usability(),'basis':'OBSERVED_MEDIA'}
    with pytest.raises(ValueError):FilmReview(media_hash='a'*64,duration=2,editorial_usability=[r])
    with pytest.raises(ValueError):FilmReview(media_hash='a'*64,duration=2,observations=[dict(start=0,end=1,mode='NORMAL_AV',observer='fixture',evidence_ref='e')],editorial_usability=[r])
    assert 'editorialUsability' not in dump_contract(FilmReview(media_hash='a'*64,duration=2))

def test_compression_is_candidate_not_deletion():
    assert compression_verdict(what_is_removed='duplicate gesture',why_redundant='same information already complete',surviving_intent_ids=('intent',),priority_impact='NONE')=='COMPRESSION_CANDIDATE'
    assert compression_verdict(what_is_removed='reaction',why_redundant='claimed slow',surviving_intent_ids=('intent',),priority_impact='P1')=='UPSTREAM_AUTHORITY_REQUIRED'
    with pytest.raises(ValueError):CompressionCandidate(what_is_removed='reaction',why_redundant='slow',surviving_director_intent_ids=['intent'],priority_impact='P1',disposition='COMPRESSION_CANDIDATE')

def test_measured_plan_bridge_preserves_existing_owner_and_blocks_premature_cut():
    from drama_plugin.contracts.dramatic_editorial import PictureEditPlan
    from drama_plugin.editorial import editorial_picture_handoff
    a=EditorialAuthority(**fixture(CASES[0]));q=a.requirements[0]
    plan=PictureEditPlan(revision='fixture',source_canon_fingerprint='c'*64,status='REVIEWED',audio_review='PASS',protected_dialogue_review='Synthetic only',sources=[dict(media_id='m',content_hash='b'*64,duration=2,performance_review='Fixture only')],picture_edit=[dict(source_media='m',source_in=0,source_out=2,cut_reason='Receiver completed',audio_carry='native',pace_function='complete receipt')])
    d=dict(edit_index=0,scene_id=q.intent.scene_id,director_intent_id=q.intent.director_intent_id,coverage_requirement_id=q.key,cut_condition_id=q.cut.key,source_authority=[dump_contract(p) for p in q.intent.source_authority],completed_events=q.cut.hold.event_sequence,reaction_complete=True,spatial_ready=True,audio_ready=True,evidence_refs=['fixture'])
    args=dict(current_sources={'court':'a'*64},approved_priorities={'court-intent':{'fact':'P0','choice':'P1'}},current_media_hashes={'m':'b'*64},canon_fingerprint='c'*64)
    h=editorial_picture_handoff(a,plan,(d,),**args)
    assert h['assemblyReady'] and h['plan']==dump_contract(plan) and not h['missingEditorialRequirements']
    for changes in [dict(completed_events=()),dict(priority_impact='P1'),dict(scene_id='other'),dict(edit_index=1)]:
        with pytest.raises(ValueError):editorial_picture_handoff(a,plan,({**d,**changes},),**args)

def test_new_facet_is_consumed_by_existing_review_verdict():
    from drama_plugin.sequence import film_review_verdict
    r=FilmReview(media_hash='a'*64,duration=2,technical='PASS',story_rhythm='PASS',visual_continuity='PASS',sound='PASS',persistence_verified=True,observations=[dict(start=0,end=2,mode='NORMAL_AV',observer='fixture',evidence_ref='e')],editorial_usability=[usability()])
    assert film_review_verdict(r,'a'*64)['status']=='REVIEW_INCOMPLETE'
    r.editorial_usability[0].outside_approved_intent=True
    assert film_review_verdict(r,'a'*64)['status']=='REQUIRES_ADAPTIVE_DIRECTOR_REVIEW'
