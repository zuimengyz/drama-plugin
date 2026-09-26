import hashlib
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import pytest
from pydantic import ValidationError
from drama_plugin.config import load_config
from drama_plugin.exceptions import ConfigurationError
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.creative_source import LiteraryPackage
from drama_plugin.contracts.narration import NarrationContext
from drama_plugin.contracts.production_language import *
from drama_plugin.creative_source import compile_source,review_hashes
from drama_plugin.production_language import *
from drama_plugin.hosts.production_language import ProductionLanguageHost


def fixture():
    # Wholly original tiny technical source; not Chekhov, not final localization.
    text='Ира сказала: «Простите». Сосед кивнул.'
    kinds=[('c','CHARACTER','Ира'),('e','EVENT','Ира извинилась'),('relation','RELATIONSHIP','соседи')]
    units=[dict(id=i,kind=k,origin='SOURCE_FACT',statement=t,anchorIds=['a'],characterIds=['c']) for i,k,t in kinds]
    present={k for _,k,_ in kinds};categories={'CHARACTER','RELATIONSHIP','EVENT','POV','CHRONOLOGY','NARRATOR','SETTING','OBJECT','MOTIF','IMAGE','INTERNAL_STATE','ARC','CONFLICT','SCENE','STRUCTURE'}
    p=dict(sourceType='LITERARY',id='language-technical-fixture',sourceArtifactId='original',artifacts=[dict(id='original',title='Original localization technical fixture',kind='ORIGINAL_TEXT',role='SOURCE_OF_TRUTH',text=text,textSha256=hashlib.sha256(text.encode()).hexdigest(),provenance='New synthetic technical fixture; not an external work',rights=dict(status='USER_OWNED',jurisdictions=['TEST'],permittedUses=['ADAPTATION'],evidence=['original technical fixture'],assertedBy='fixture-author',basis='PROVENANCE_RECORD'))],anchors=[dict(id='a',artifactId='original',start=0,end=len(text),quote=text)],analysis=dict(units=units,eventOrder=['e'],chronology='同一刻',narrativePov='第三人称',narrator='未具名',narrativeStructure='道歉及回应',absentCategories={k:'Tiny technical text supplies no separate support' for k in categories-present}),philosophicalCore=dict(sourceUnitIds=['e'],question='道歉是否被接住？',conflict='表达与回应',valuePoles=['表达','保留'],characterChoice='道歉',consequence='邻居点头',ambiguity='不指定起因'),adaptation=dict(preserved=dict(mustKeep=['e'],coreRelationships=['relation'],coreEvents=['e'],characterArc='一次修复动作',themeConflict='表达与回应',narrativeIdentity='极小测试'),permittedChanges=['ADAPT_DIALOGUE'],decisions=[dict(id='d',operation='ADAPT_DIALOGUE',sourceUnitIds=['c','e','relation'],reason='技术语言通路',narrativeEffect='保留道歉',expression='道歉并点头')]),compression=dict(mappings=[dict(decisionId='d',destinationIds=['b'])]),cinema=dict(expressions=[dict(id='x',decisionId='d',destinationId='b',channels=['DIALOGUE'],shootableExpression='说话并点头',choiceActionConsequence='道歉得到回应',nonverbalAlternative='目光与点头')]),characterArc=dict(states=[dict(characterId='c',arcStage='ordinary',sourceUnitIds=['e'],origin='INTERPRETATION',narrativeState='交谈',emotionalState='平常',beliefState='未知',behavioralState='道歉',relationshipState='邻居',performanceImplication='普通礼貌',visualContinuityBoundary='不设计外貌')]),reviews=[dict(authority=a,subjectHash='0'*64,status='APPROVED',reviewer='technical-fixture-only',evidence='synthetic structure, not user/artistic approval') for a in ('literary-source-analysis','philosophical-core','literary-adaptation','literature-to-cinema','character-dramaturgy')])
    model=LiteraryPackage.model_validate(p)
    for r in p['reviews']:r['subjectHash']=review_hashes(model)[r['authority']]
    adaptation_review=next(r for r in p['reviews'] if r['authority']=='literary-adaptation')
    adaptation_review['preservationChecks']={key:dict(status='PRESERVED',sourceUnitIds=[key] if key in ('e','relation') else ['e','relation'],
        destinationIds=['b'],evidence='Synthetic localization fixture retains the apology, neighbor response and unspecified cause.')
        for key in ('e','relation','character_arc','theme_conflict','narrative_identity')}
    model=LiteraryPackage.model_validate(p);compiled=compile_source(dict(source=p,jurisdiction='TEST',intendedUse='ADAPTATION'))
    review='对不起。';script=dict(text=review,textSha256=hashlib.sha256(review.encode()).hexdigest(),screenplayInput=dump_contract(compiled),beats=[dict(id='b',text=review,textStart=0,textEnd=len(review),textSha256=hashlib.sha256(review.encode()).hexdigest(),characterStates=['c:ordinary'],cinemaExpressionId='x',adaptationDecisionId='d')])
    c=NarrationContext(package=model,screenplay=script,characterDramaturgy={'characterArc':dump_contract(model.character_arc)})
    m=SourceLanguageMetadata(artifactId='original',artifactHash=sha256_canonical(model.artifacts[0]),artifactLanguage='ru',originalArtifactId='original',originalWorkLanguages=['ru'],evidenceRef='fixture-author-language-declaration',evidenceHash=hashlib.sha256(text.encode()).hexdigest(),evidenceSelector='Original author metadata language=ru',assertionBasis='SOURCE_METADATA',assertedBy='technical-fixture-author')
    cfg=load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,en'})
    profile=resolve_profile('work-test',cfg,model.artifacts,[m],'original')
    intent=SemanticDialogueIntent(lineId='line-test',characterId='c',sceneId='s',beatId='b',reviewText=review,semanticIntent='一次普通道歉；不指定原因',register='礼貌日常',relationshipContext='邻居',period='原创微型当代测试；无19世纪措辞质量主张',screenplayHash=sha256_canonical(script),characterDramaturgyHash=sha256_canonical(c.character_dramaturgy),sourceRefs=['anchor:a'],adaptationRefs=['decision:d'],originalDialogue=['Простите'],reviewStatus='CANDIDATE')
    line=ProductionDialogueLine(purpose='TECHNICAL_FIXTURE',lineId=intent.line_id,characterId='c',sceneId='s',beatId='b',sourceLanguage='ru',productionLanguage='ru',reviewText=review,productionText='Простите.',semanticIntent=intent.semantic_intent,register=intent.language_register,relationshipContext=intent.relationship_context,sourceRefs=intent.source_refs,adaptationRefs=intent.adaptation_refs,semanticIntentHash=sha256_canonical(intent),languageProfileHash=sha256_canonical(profile),originalDialogueConsulted=intent.original_dialogue,localizationReason='直接参考原创俄文句，而非从中文回译；仅测试',reviewStatus='CANDIDATE',reviewSubjectHash='0'*64)
    line.review_subject_hash=dialogue_review_subject(line)
    return c,m,profile,intent,line


def test_source_original_and_review_are_separate():
    c,m,p,i,line=fixture();out=compile_localization(line,i,p,c)
    assert p.source_original_language==p.resolved_production_language=='ru' and p.creative_review_language=='zh'
    assert out['productionLine']['productionText']=='Простите.'
    assert p.subtitles.languages==('zh','en')


def test_explicit_does_not_rewrite_source():
    c,m,_,_,_=fixture();cfg=load_config(environment={'DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY':'explicit','DRAMA_PLUGIN_SPOKEN_LANGUAGE':'zh'})
    p=resolve_profile('w',cfg,c.package.artifacts,[m],'original')
    assert p.source_original_language=='ru' and p.resolved_production_language=='zh'


@pytest.mark.parametrize('env',[{'DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY':'explicit'},{'DRAMA_PLUGIN_SPOKEN_LANGUAGE':'Russian'},{'DRAMA_PLUGIN_CREATIVE_REVIEW_LANGUAGE':'en_US'},{'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true'},{'DRAMA_PLUGIN_SUBTITLES_ENABLED':'yes'},{'DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,not a language'}])
def test_invalid_configuration(env):
    with pytest.raises(ConfigurationError):load_config(environment=env)


@pytest.mark.parametrize('value,expected',[('ru','ru'),('zh','zh'),('en','en'),('de','de'),('fr','fr'),('zh-hans','zh-Hans'),('zh-Hant','zh-Hant'),('en-us','en-US'),('en-GB','en-GB')])
def test_tags(value,expected):assert language_tag(value)==expected


def test_missing_or_multilingual_source():
    c,m,_,_,_=fixture();m.original_work_languages=()
    with pytest.raises(ValueError,match='SOURCE_ORIGINAL_LANGUAGE_REQUIRED'):resolve_profile('w',load_config(environment={}),c.package.artifacts,[m],'original')
    m.original_work_languages=('ru','en')
    with pytest.raises(ValueError,match='MULTILINGUAL_SOURCE_REQUIRES_LANGUAGE_PLAN'):resolve_profile('w',load_config(environment={}),c.package.artifacts,[m],'original')


def test_env_overrides_internal_config(tmp_path):
    p=tmp_path/'config.yml';p.write_text('spoken_language_policy: explicit\nspoken_language: en\ncreative_review_language: fr\n')
    c=load_config(p,environment={'DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY':'source_original','DRAMA_PLUGIN_CREATIVE_REVIEW_LANGUAGE':'zh'})
    assert c.spoken_language_policy=='source_original' and c.creative_review_language=='zh'


def test_work_binding_survives_runtime_change(tmp_path):
    c,m,_,_,_=fixture();host=ProductionLanguageHost(tmp_path)
    first=host.bind_work('a',load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,en'}),c.package.artifacts,[m],'original')
    new=load_config(environment={'DRAMA_PLUGIN_SPOKEN_LANGUAGE_POLICY':'explicit','DRAMA_PLUGIN_SPOKEN_LANGUAGE':'zh'})
    assert host.bind_work('a',new,c.package.artifacts,[m],'original')==first
    other=host.bind_work('b',new,c.package.artifacts,[m],'original')
    assert other.resolved_production_language=='zh' and not other.subtitles.enabled


def test_disabled_duplicate_same_language_subtitles():
    c,m,_,_,_=fixture()
    cfg=load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'false','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,en'})
    p=resolve_profile('w',cfg,c.package.artifacts,[m],'original');out=localization_tasks(p,'NONE')
    assert out['subtitleTrackRequests']==[] and out['narrationTasks']==[] and p.warnings
    cfg=load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'ru,RU,en-US,en-us'})
    p=resolve_profile('w',cfg,c.package.artifacts,[m],'original')
    assert p.subtitles.languages==('ru','en-US')


def test_translation_does_not_replace_original_or_inherit_rights():
    c,m,_,_,_=fixture();a=c.package.artifacts[0].model_copy(deep=True);a.id='translation';a.kind='TRANSLATION';a.derived_from='original';a.rights.status='UNKNOWN'
    tr=m.model_copy(deep=True);tr.artifact_id=a.id;tr.artifact_hash=sha256_canonical(a);tr.artifact_language='zh'
    assert resolve_source_language([*c.package.artifacts,a],[m,tr],'translation')[0]=='ru'
    assert a.rights.status=='UNKNOWN'
    tr.original_work_languages=('zh',)
    with pytest.raises(ValueError,match='TRANSLATION_CANNOT'):resolve_source_language([*c.package.artifacts,a],[m,tr],'translation')


def test_subtitle_localization_independent_track_and_untimed():
    c,m,p,i,line=fixture()
    tracks=[]
    for lang,text in [('zh','抱歉。'),('en','Excuse me.')]:
        q=SubtitleCue(cueId='sub-'+lang,sceneId='s',dialogueLineId=line.line_id,sourceTextLanguage='ru',targetLanguage=lang,subtitleText=text,semanticIntentRef=sha256_canonical(i),speakerRef='c',productionLineHash=sha256_canonical(line),localizationReason='新写短字幕表达，不复制reviewText或外部译本')
        t=SubtitleTrack(trackId='track-'+lang,workId=p.work_id,trackLanguage=lang,languageProfileHash=sha256_canonical(p),cues=[q],purpose='TECHNICAL_FIXTURE')
        result=compile_subtitle_track(t,[line],[i],p,c);tracks.append(result)
        assert result['timing']=='UNTIMED' and not result['renderAuthorized']
        with pytest.raises(ValueError,match='FINAL_SUBTITLE_TIMING'):require_subtitle_export(t)
    assert len(tracks)==2 and line.production_text=='Простите.'


def approved_for_unit_test():
    c,m,p,i,line=fixture();i.review_status='APPROVED';i.approval_ref='test-only-semantic-approval'
    line.purpose='PRODUCTION';line.semantic_intent_hash=sha256_canonical(i);line.review_status='APPROVED';line.reviewer='test-reviewer';line.approval_ref='test-only-language-review';line.review_subject_hash=dialogue_review_subject(line)
    return c,SpeechLanguageAuthorization(profile=p,intent=i,line=line)


def test_speech_rejects_review_text_wrong_language_and_fixture():
    c,m,p,i,line=fixture()
    with pytest.raises(ValueError,match='TECHNICAL_FIXTURE'):speech_rendition(SpeechLanguageAuthorization(profile=p,intent=i,line=line))
    c,a=approved_for_unit_test()
    assert speech_rendition(a)['performanceText']=='Простите.'
    args=dict(work_id=a.profile.work_id,scene_id='s',line_id=a.line.line_id,speaker='c',exact_text=a.line.production_text,voice_language='ru')
    validate_speech_authorization(a,**args)
    for change in [{'exact_text':'对不起。'},{'voice_language':'zh'}]:
        with pytest.raises(ValueError,match='REVIEW_TEXT_OR_LANGUAGE'):validate_speech_authorization(a,**{**args,**change})


def test_existing_speech_contract_consumes_authorization():
    from test_audio_foundation import request
    from drama_plugin.contracts.audio import SpeechGenerationRequest
    c,a=approved_for_unit_test();raw=dump_contract(request());raw.update(workId=a.profile.work_id,sceneId='s',spokenContentId=a.line.line_id,speakerKey='c',exactText=a.line.production_text,productionLanguageAuthorization=dump_contract(a),performanceRendition=speech_rendition(a))
    raw['voiceProfile']['speakerKey']='c';raw['voiceProfile']['creativeProfile']['language']='ru'
    req=SpeechGenerationRequest.model_validate(raw)
    assert req.exact_text=='Простите.'
    raw['exactText']='对不起。'
    with pytest.raises(ValueError,match='REVIEW_TEXT_OR_LANGUAGE'):SpeechGenerationRequest.model_validate(raw)


def test_work_gate_cannot_bypass_by_omitting_request_metadata():
    from test_audio_foundation import request
    c,a=approved_for_unit_test();work=SimpleNamespace(id=a.profile.work_id,content={'creativeSourceType':'LITERARY','literaryPackage':dump_contract(c.package),'productionLanguageProfile':dump_contract(a.profile)})
    with pytest.raises(ValueError,match='APPROVED_PRODUCTION_DIALOGUE_REQUIRED'):require_work_speech_language(work,request())
    req=SimpleNamespace(production_language_authorization=a,scene_id='s',spoken_content_id=a.line.line_id,speaker_key='c',exact_text=a.line.production_text,voice_profile=SimpleNamespace(creative_profile=SimpleNamespace(language='ru')))
    with pytest.raises(ValueError,match='CURRENT_WORK_DIALOGUE_APPROVAL'):require_work_speech_language(work,req)
    work.content['productionDialogueApprovals']={a.line.line_id:sha256_canonical(a.line)}
    require_work_speech_language(work,req)


def test_localization_conflict_and_source_tampering():
    c,m,p,i,line=fixture();line.semantic_intent='偷改动机';line.review_subject_hash=dialogue_review_subject(line)
    with pytest.raises(ValueError,match='UPSTREAM_LOCALIZATION_CONFLICT'):compile_localization(line,i,p,c)
    c,m,p,i,line=fixture();i.original_dialogue=('不存在的原文',);line.original_dialogue_consulted=i.original_dialogue;line.semantic_intent_hash=sha256_canonical(i);line.review_subject_hash=dialogue_review_subject(line)
    with pytest.raises(ValueError,match='ORIGINAL_DIALOGUE_SOURCE'):compile_localization(line,i,p,c)


def test_profile_cannot_be_changed_or_removed_by_work_save():
    c,m,p,i,line=fixture();content={'creativeSourceType':'LITERARY','literaryPackage':dump_contract(c.package),'productionLanguageProfile':dump_contract(p)}
    validate_work_language(content)
    changed=deepcopy(content);changed.pop('productionLanguageProfile')
    with pytest.raises(ValueError,match='IMMUTABLE'):validate_work_language(changed,content)


def test_image_and_video_prompt_isolation(tmp_path):
    # Existing real asset compiler is run with identical visual inputs under two
    # language settings. No provider call and no new visual asset design task.
    from test_specialized_asset import fixture as visual_fixture
    host,bible,ref,current=visual_fixture(tmp_path)
    before=host.compile(ref,'char',current=current)['projection']
    host.config=load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,en','DRAMA_PLUGIN_VISUAL_AUTHORITY_ROOT':str(tmp_path),'DRAMA_PLUGIN_VISUAL_MEDIUM':'live_action'})
    after=host.compile(ref,'char',current=current)['projection']
    assert before==after
    from drama_plugin.contracts.video import VideoRequest
    assert 'subtitle_languages' not in VideoRequest.model_fields

    from test_cinematic_direction import frozen_example, video_fixture, selection_handoff
    from drama_plugin.visual.video_selection import Requirements
    from drama_plugin.hosts.cinematic_projection import project
    from drama_plugin.hosts.comfy_video import inspect_graph
    from seedance_helpers import add_director_inputs
    req,candidate,graph,selection,adapter=video_fixture(tmp_path)
    frozen=frozen_example()
    req=Requirements.model_validate({**req.model_dump(),'frozen_creative':selection_handoff(frozen)})
    req=add_director_inputs(req,adapter,frozen)
    before_video=project(req,candidate,inspect_graph(graph,selection))
    load_config(environment={'DRAMA_PLUGIN_SUBTITLES_ENABLED':'true','DRAMA_PLUGIN_SUBTITLE_LANGUAGES':'zh,en'})
    after_video=project(req,candidate,inspect_graph(graph,selection))
    assert before_video==after_video
    assert all(x not in after_video['prompt'] for x in ('Chinese subtitle','English subtitle','字幕','caption text'))


@pytest.mark.asyncio
async def test_real_role_dubbing_entry_blocks_review_text_before_side_effects(tmp_path):
    from test_role_dubbing import (MockDramaData,MockMemoryProvider,FakeVoiceProvider,FakeMediaProvider,FakeFish,FishRoleDubbingProvider,request,probe)
    data=MockDramaData();data.work=data.work.model_copy(update={'content':{'creativeSourceType':'LITERARY'}})
    voices=FakeVoiceProvider(tmp_path);fish=FakeFish('请给我三十骑')
    provider=FishRoleDubbingProvider(memory=MockMemoryProvider(data),voices=voices,media=FakeMediaProvider(),fish=fish,output_directory=tmp_path/'attempts',probe=probe)
    with pytest.raises(ValueError,match='APPROVED_PRODUCTION_DIALOGUE_REQUIRED'):
        await provider.generate_role_dubbing(request('请给我三十骑'))
    assert fish.design_calls==0 and voices.values=={} and not (tmp_path/'attempts').exists()
