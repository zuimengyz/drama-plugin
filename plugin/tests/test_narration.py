from copy import deepcopy
import hashlib
import pytest
from pydantic import ValidationError
from literary_fixture import fixture, reviewed
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.narration import NarrationContext,NarrationPlan,FullDirectorScreenplay
from drama_plugin.creative_source import compile_source
from drama_plugin.narration import compile_narration,narration_review_subject,compile_director_screenplay,director_review_subject


def context(grant=False):
    p=fixture()
    p['analysis']['absentCategories'].pop('NARRATOR')
    p['analysis']['units'].append(dict(id='narrator',kind='NARRATOR',origin='SOURCE_FACT',statement='第三人称描述人物动作的叙述者',anchorIds=['a']))
    p['adaptation']['decisions'][0]['sourceUnitIds'].append('narrator')
    if grant:
        p['cinema']['expressions'][0]['channels'].append('VOICE_OVER')
        p['cinema']['expressions'][0]['explicitnessException']=dict(basis='SOURCE_CONTAINS',reason='synthetic source function grant',sourceUnitIds=['narrator','internal'],directorDecision='test only')
    p=reviewed(p)
    compiled=compile_source(dict(source=p,jurisdiction='TEST',intendedUse='ADAPTATION'))
    text='林停手，然后摆碗。'
    beat=dict(id='beat:test',cinemaExpressionId='x',adaptationDecisionId='d',textStart=0,textEnd=len(text),text=text,textSha256=hashlib.sha256(text.encode()).hexdigest(),characterStates=['c:early'])
    return NarrationContext(package=p,screenplay=dict(text=text,textSha256=beat['textSha256'],screenplayInput=dump_contract(compiled),beats=[beat]),characterDramaturgy=dict(characterArc=p['characterArc'],profiles=[{'characterId':'c','meaning':'hesitation'}]))


def plan(c,narrated=False):
    bible=dict(narrationMode='AUTHORIAL_NARRATION' if narrated else 'NONE',narratorIdentity='external observer',narrativeDistance='slight distance',knowledgeScope='source only',temporalPosition='present',tone='restrained',ironyLevel='low',languageDensity='sparse',rhythm='unhurried',allowedFunctions=['source distance'],forbiddenFunctions=['theme answer'],relationshipToCharacterPov='separate',silencePolicy='silence unless justified',themeExplicitnessBoundary='not a theme explanation',sourcePolicy='designated artifact only')
    cues=[]
    if narrated:
        cues=[dict(cueId='N1',sceneId='S1',beatId='beat:test',narrationType='AUTHORIAL_NARRATION',text='两只碗。',sourceLayer='ADAPTED_SOURCE_NARRATOR',sourceAnchorIds=['a'],sourceUnitIds=['narrator'],literaryFunction='source observer distance',cinematicFunction='preserve language distance',whyNarrationIsNeeded='test authored function',whyActionOrSilenceIsInsufficient='test source language contrast',placement='before speech',relationshipToDialogue='yield',relationshipToPerformance='do not explain acting',themeExplicitnessReview=dict(disposition='FUNCTION_ONLY',reason='test review; not literary proof',reviewer='test'),sourceMapRefs=['analysis:narrator'],adaptationDecisionId='d',directorReason='test function',performanceIntent=dict(narrativeDistance='external',deliveryRestraint='quiet',irony='minimal',certainty='source only',tempo='natural',pauseBehavior='yield',emotionalTemperature='neutral'))]
    p=NarrationPlan(id='test',bible=bible,cues=cues,scenes=[dict(sceneId='S1',beatIds=['beat:test'],policy='NARRATION' if narrated else 'SILENCE',reason='source function' if narrated else 'action sufficient',cueIds=['N1'] if narrated else [])],review=dict(subjectHash='0'*64,reviewer='test',evidence='structural fixture only',status='REVIEWED_CANDIDATE'))
    p.review.subject_hash=narration_review_subject(p,c)
    return p


def repin(p,c):
    p.review.subject_hash=narration_review_subject(p,c)
    return p


def full(c,p):
    scene=dict(sceneId='S1',title='Test',beatIds=['beat:test'],characterStates=[dict(characterId='c',arcStage='early')],narrationPolicy='SILENCE',narrationCueIds=[],mustPreserve=['action'],mustNot=['new fact'],musicPolicy='MUSIC_AVOID',sourceMapRefs=['beat:test:x'])
    for key in ('dramaticPurpose','audienceKnowledge','audienceMisunderstandingRisk','relationshipState','performanceIntent','blockingIntent','spatialDramaturgy','visualAttention','soundIntent','silenceIntent','rhythmTempo','humorAbsurdityFunction','transitionIn','transitionOut','continuityRequirement','specializedAssetHandoff','performanceHandoff','cinematographyHandoff','soundHandoff','musicHandoff','shotDesignHandoff'):
        scene[key]='Synthetic intent; no execution parameters.'
    f=FullDirectorScreenplay(id='test',narrationPlanHash=sha256_canonical(p),screenplayHash=sha256_canonical(c.screenplay),characterDramaturgyHash=sha256_canonical(c.character_dramaturgy),scenes=[scene],review=dict(subjectHash='0'*64,reviewer='test',evidence='test only',status='REVIEWED_CANDIDATE'))
    f.review.subject_hash=director_review_subject(f)
    return f


def test_none_is_complete_with_zero_cues():
    c=context();p=plan(c)
    r=compile_narration(p,c)
    assert r['status']=='CANDIDATE_READY' and r['sourceMap']==[] and r['audioFutureHandoff']==[]
    assert r['humanApproval'] is None and not r['p2Authorized']


def test_authorial_valid_source_grant_and_real_consumer():
    c=context(True);p=plan(c,True);r=compile_narration(p,c)
    assert r['status']=='CANDIDATE_READY'
    assert r['sourceMap'][0]['sourceLayer']=='ADAPTED_SOURCE_NARRATOR'
    assert r['audioFutureHandoff'][0]['cueId']=='N1'


@pytest.mark.parametrize('field',['literaryFunction','whyNarrationIsNeeded','whyActionOrSilenceIsInsufficient'])
def test_unjustified_cue_blocked(field):
    c=context(True);d=dump_contract(plan(c,True));d['cues'][0][field]=' '
    with pytest.raises(ValidationError):NarrationPlan.model_validate(d)


@pytest.mark.parametrize('layer,kind,unit,ref',[('CHARACTER_THOUGHT_SOURCE','AUTHORIAL_NARRATION','internal','analysis:internal'),('ADAPTED_SOURCE_NARRATOR','INTERNAL_MONOLOGUE','narrator','analysis:narrator'),('ADAPTED_SOURCE_NARRATOR','AUTHORIAL_NARRATION','internal','analysis:internal')])
def test_source_narrator_cannot_be_character_mind(layer,kind,unit,ref):
    c=context(True);p=plan(c,True);p.bible.narration_mode=kind;p.cues[0].narration_type=kind;p.cues[0].source_layer=layer;p.cues[0].source_unit_ids=(unit,);p.cues[0].source_map_refs=(ref,)
    with pytest.raises(ValueError,match='SOURCE_NARRATOR|CHARACTER_THOUGHT'):compile_narration(repin(p,c),c)


def test_legitimate_character_thought_keeps_own_layer():
    c=context(True);p=plan(c,True);p.bible.narration_mode='INTERNAL_MONOLOGUE';q=p.cues[0];q.narration_type='INTERNAL_MONOLOGUE';q.source_layer='CHARACTER_THOUGHT_SOURCE';q.source_unit_ids=('internal',);q.source_map_refs=('analysis:internal',)
    assert compile_narration(repin(p,c),c)['sourceMap'][0]['sourceLayer']=='CHARACTER_THOUGHT_SOURCE'


def test_invented_theme_cannot_self_approve():
    c=context(True);p=plan(c,True);q=p.cues[0];q.text='真正杀死他的不是将军，而是他心里的权力。';q.source_layer='ADAPTATION_NARRATION_INVENTION'
    r=compile_narration(repin(p,c),c)
    assert r['status']=='HUMAN_CONFLICT' and any('INVENTED' in x for x in r['reasons'])


@pytest.mark.parametrize('target',['anchor','sourceUnit','decision','beat'])
def test_source_reference_tampering_blocked(target):
    c=context(True);p=plan(c,True);q=p.cues[0]
    if target=='anchor':q.source_anchor_ids=('forged',)
    if target=='sourceUnit':q.source_unit_ids=('forged',)
    if target=='decision':q.adaptation_decision_id='forged'
    if target=='beat':q.beat_id='forged'
    with pytest.raises(ValueError):compile_narration(repin(p,c),c)


def test_anchor_content_tampering_blocked_by_p0():
    c=context(True);p=plan(c,True);c.package.anchors[0].quote='false source'
    with pytest.raises(ValueError,match='SOURCE_ANCHOR_QUOTE_MISMATCH'):compile_narration(repin(p,c),c)


def test_ungranted_narration_requires_request_and_blocks_director():
    c=context();p=plan(c,True)
    with pytest.raises(ValueError,match='UPSTREAM_CHANGE_REQUEST'):compile_narration(p,c)
    d=dump_contract(p);d['cues'][0]['upstreamChangeRequestId']='r';d['upstreamChangeRequests']=[dict(id='r',targetAuthority='literary-adaptation',currentValue='no VO',problem='cue needs new grant',sourceEvidence=['a'],proposedChange='consider VO',downstreamImpact='recompile source')]
    p=repin(NarrationPlan.model_validate(d),c)
    assert compile_narration(p,c)['status']=='UPSTREAM_CHANGE_REQUIRED'
    with pytest.raises(ValueError,match='DIRECTOR_UPSTREAM_NARRATION_UNRESOLVED'):compile_director_screenplay(full(c,p),p,c)


@pytest.mark.parametrize('target',['bible','screenplay','dramaturgy'])
def test_current_upstream_change_invalidates_old_director_review(target):
    c=context();p=plan(c);f=full(c,p)
    assert compile_director_screenplay(f,p,c)['status']=='CANDIDATE_READY'
    if target=='bible':p.bible.tone='changed'
    if target=='screenplay':c.screenplay['revisionNote']='changed'
    if target=='dramaturgy':c.character_dramaturgy['profiles'][0]['meaning']='changed'
    with pytest.raises(ValueError,match='STALE_NARRATION_REVIEW'):compile_director_screenplay(f,p,c)
    repin(p,c)
    with pytest.raises(ValueError,match='STALE_DIRECTOR_BINDING_OR_REVIEW'):compile_director_screenplay(f,p,c)


@pytest.mark.parametrize('field',['provider','voiceId','ttsModel','speakerId'])
def test_audio_provider_fields_forbidden(field):
    c=context(True);d=dump_contract(plan(c,True));d['cues'][0]['performanceIntent'][field]='forbidden'
    with pytest.raises(ValidationError):NarrationPlan.model_validate(d)


def test_director_cannot_use_other_character_stage():
    c=context();p=plan(c);f=full(c,p);f.scenes[0].character_states[0].arc_stage='late';f.review.subject_hash=director_review_subject(f)
    with pytest.raises(ValueError,match='CHARACTER_STATE_SCOPE'):compile_director_screenplay(f,p,c)


def test_silence_cannot_hide_narration():
    c=context(True);p=plan(c,True);p.scenes[0].policy='SILENCE'
    with pytest.raises(ValueError,match='SCENE_NARRATION_POLICY'):compile_narration(repin(p,c),c)
