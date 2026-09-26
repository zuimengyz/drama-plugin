"""Source metadata -> work policy -> localized text -> speech/subtitle boundaries.

No translation model, provider, subtitle timing or visual prompt authorship here.
"""
from typing import Any, Sequence
from drama_plugin.config.models import DramaPluginConfig
from drama_plugin.config.language import language_tag
from drama_plugin.contracts.base import dump_contract,sha256_canonical
from drama_plugin.contracts.creative_source import SourceArtifact
from drama_plugin.contracts.production_language import (
    SourceLanguageMetadata, ProductionLanguageProfile, SubtitlePolicy,
    SemanticDialogueIntent, ProductionDialogueLine, SubtitleTrack,
    SpeechLanguageAuthorization,
)


def resolve_source_language(artifacts: Sequence[SourceArtifact], metadata: Sequence[SourceLanguageMetadata], designated: str) -> tuple[str | None,SourceLanguageMetadata]:
    sources={a.id:a for a in artifacts};records={m.artifact_id:m for m in metadata}
    if len(records)!=len(metadata):raise ValueError('DUPLICATE_SOURCE_LANGUAGE_METADATA')
    if designated not in sources:raise ValueError('SOURCE_ARTIFACT_REQUIRED')
    current=sources[designated];visited=set()
    while current.kind!='ORIGINAL_TEXT':
        if current.id in visited:raise ValueError('SOURCE_DERIVATION_CYCLE')
        visited.add(current.id)
        if not current.derived_from or current.derived_from not in sources:raise ValueError('ORIGINAL_SOURCE_ARTIFACT_REQUIRED')
        current=sources[current.derived_from]
    m=records.get(current.id)
    if m is None:raise ValueError('SOURCE_ORIGINAL_LANGUAGE_REQUIRED')
    for r in records.values():
        if r.artifact_id not in sources or sha256_canonical(sources[r.artifact_id])!=r.artifact_hash:
            raise ValueError('SOURCE_LANGUAGE_METADATA_STALE')
        if r.original_artifact_id!=current.id or r.original_work_languages!=m.original_work_languages:
            raise ValueError('TRANSLATION_CANNOT_REDEFINE_ORIGINAL_LANGUAGE')
    if len(m.original_work_languages)>1:raise ValueError('MULTILINGUAL_SOURCE_REQUIRES_LANGUAGE_PLAN')
    original=m.original_work_languages[0] if m.original_work_languages else None
    if original and m.artifact_language!=original:raise ValueError('ORIGINAL_ARTIFACT_LANGUAGE_CONFLICT')
    return original,m


def resolve_profile(work_id: str, config: DramaPluginConfig, artifacts: Sequence[SourceArtifact], metadata: Sequence[SourceLanguageMetadata], designated: str) -> ProductionLanguageProfile:
    original,m=resolve_source_language(artifacts,metadata,designated)
    if config.spoken_language_policy=='source_original' and not original:raise ValueError('SOURCE_ORIGINAL_LANGUAGE_REQUIRED')
    spoken=original if config.spoken_language_policy=='source_original' else config.spoken_language
    if not spoken:raise ValueError('EXPLICIT_SPOKEN_LANGUAGE_REQUIRED')
    warnings=[]
    if not config.subtitles_enabled and config.subtitle_languages:warnings.append('SUBTITLE_LANGUAGES_IGNORED_WHILE_DISABLED')
    if config.spoken_language_policy=='source_original' and config.spoken_language:warnings.append('EXPLICIT_SPOKEN_LANGUAGE_IGNORED_BY_SOURCE_ORIGINAL_POLICY')
    return ProductionLanguageProfile(work_id=work_id,source_original_language=original,source_language_metadata=m,
        spoken_language_policy=config.spoken_language_policy,resolved_production_language=spoken,
        creative_review_language=config.creative_review_language,
        subtitles=SubtitlePolicy(enabled=config.subtitles_enabled,languages=config.subtitle_languages if config.subtitles_enabled else ()),
        configuration_sources=config.language_sources,warnings=tuple(warnings))


def validate_profile(profile: ProductionLanguageProfile) -> None:
    p=ProductionLanguageProfile.model_validate(dump_contract(profile))
    languages=p.source_language_metadata.original_work_languages
    if len(languages)>1:raise ValueError('MULTILINGUAL_SOURCE_REQUIRES_LANGUAGE_PLAN')
    if p.source_original_language!=(languages[0] if languages else None):raise ValueError('SOURCE_LANGUAGE_PROFILE_CONFLICT')
    if p.spoken_language_policy=='source_original' and (not p.source_original_language or p.resolved_production_language!=p.source_original_language):raise ValueError('SOURCE_ORIGINAL_LANGUAGE_REQUIRED_OR_MISMATCH')
    if p.subtitles.enabled!=bool(p.subtitles.languages) or len(set(p.subtitles.languages))!=len(p.subtitles.languages):raise ValueError('INVALID_BOUND_SUBTITLE_POLICY')


def localization_tasks(profile: ProductionLanguageProfile, narration_mode: str) -> dict[str,Any]:
    validate_profile(profile)
    if narration_mode not in {'NONE','AUTHORIAL_NARRATION','CHARACTER_VOICE_OVER','INTERNAL_MONOLOGUE','EXPOSITORY_NARRATION'}:raise ValueError('INVALID_NARRATION_MODE')
    return {'dialogueLanguage':profile.resolved_production_language,
        'narrationLanguage':None if narration_mode=='NONE' else profile.resolved_production_language,
        'narrationTasks':[] if narration_mode=='NONE' else [{'kind':'LOCALIZE_ADOPTED_NARRATION','language':profile.resolved_production_language,'requires':'APPROVED_NARRATION_CUES'}],
        'subtitleTrackRequests':[{'language':lang,'timingStatus':'UNTIMED','requires':'APPROVED_PRODUCTION_TEXT'} for lang in profile.subtitles.languages] if profile.subtitles.enabled else [],
        'productionAuthorized':False}


def dialogue_review_subject(line: ProductionDialogueLine) -> str:
    return sha256_canonical(dump_contract(line,exclude={'review_status','review_subject_hash','reviewer','approval_ref'}))


def validate_localization(line: ProductionDialogueLine, intent: SemanticDialogueIntent, profile: ProductionLanguageProfile, *, for_speech: bool=False) -> None:
    line=ProductionDialogueLine.model_validate(dump_contract(line));intent=SemanticDialogueIntent.model_validate(dump_contract(intent));validate_profile(profile)
    if line.language_profile_hash!=sha256_canonical(profile) or line.semantic_intent_hash!=sha256_canonical(intent):raise ValueError('STALE_LOCALIZATION_BINDING')
    if line.production_language!=profile.resolved_production_language or line.source_language!=profile.source_original_language:raise ValueError('PRODUCTION_LANGUAGE_MISMATCH')
    for field in ('line_id','character_id','scene_id','beat_id','review_text','semantic_intent','language_register','relationship_context','source_refs','adaptation_refs'):
        if getattr(line,field)!=getattr(intent,field):raise ValueError('UPSTREAM_LOCALIZATION_CONFLICT:'+field)
    if line.original_dialogue_consulted!=intent.original_dialogue:raise ValueError('ORIGINAL_DIALOGUE_REFERENCE_REQUIRED')
    if line.review_subject_hash!=dialogue_review_subject(line):raise ValueError('STALE_LOCALIZATION_REVIEW')
    if line.review_status=='UPSTREAM_LOCALIZATION_CONFLICT' or intent.review_status=='UPSTREAM_LOCALIZATION_CONFLICT':raise ValueError('UPSTREAM_LOCALIZATION_CONFLICT')
    if for_speech:
        if line.purpose!='PRODUCTION':raise ValueError('TECHNICAL_FIXTURE_NOT_PRODUCTION')
        if (line.review_status!='APPROVED' or intent.review_status!='APPROVED' or not line.reviewer or not line.approval_ref or not intent.approval_ref):raise ValueError('APPROVED_PRODUCTION_DIALOGUE_REQUIRED')


def compile_localization(line: ProductionDialogueLine, intent: SemanticDialogueIntent, profile: ProductionLanguageProfile, context: Any) -> dict[str,Any]:
    from drama_plugin.narration import validate_context
    c,_=validate_context(context)
    validate_localization(line,intent,profile)
    resolve_source_language(c.package.artifacts,[profile.source_language_metadata],c.package.source_artifact_id)
    if intent.screenplay_hash!=sha256_canonical(c.screenplay) or intent.character_dramaturgy_hash!=sha256_canonical(c.character_dramaturgy):raise ValueError('STALE_LOCALIZATION_UPSTREAM')
    beats={b['id']:b for b in c.screenplay['beats']}
    beat=beats.get(intent.beat_id)
    if not beat or intent.review_text not in beat['text'] or not any(s.split(':')[0]==intent.character_id for s in beat['characterStates']):raise ValueError('DIALOGUE_INTENT_SCREENPLAY_MISMATCH')
    anchors={a.id:a for a in c.package.anchors};decisions={d.id:d for d in c.package.adaptation.decisions};units={u.id:u for u in c.package.analysis.units}
    aids=[r.removeprefix('anchor:') for r in intent.source_refs]
    if any(r!='anchor:'+a for r,a in zip(intent.source_refs,aids)) or not set(aids)<=anchors.keys():raise ValueError('LOCALIZATION_SOURCE_ANCHOR_REQUIRED')
    permitted: set[str]=set()
    for ref in intent.adaptation_refs:
        d=decisions.get(ref.removeprefix('decision:'))
        if not d or ref!='decision:'+d.id or not any(e.decision_id==d.id and e.destination_id==intent.beat_id for e in c.package.cinema.expressions):raise ValueError('LOCALIZATION_ADAPTATION_MISMATCH')
        permitted.update(a for u in d.source_unit_ids for a in units[u].anchor_ids)
    if not set(aids)<=permitted or any(not any(q in anchors[a].quote for a in aids) for q in intent.original_dialogue):raise ValueError('ORIGINAL_DIALOGUE_SOURCE_MISMATCH')
    return {'status':'USER_REVIEW_PENDING','productionLine':dump_contract(line),'sourceMap':{
        'lineId':line.line_id,'semanticIntentRef':line.semantic_intent_hash,'screenplayRef':intent.screenplay_hash,
        'characterDramaturgyRef':intent.character_dramaturgy_hash,'sourceRefs':list(line.source_refs),'adaptationRefs':list(line.adaptation_refs),
        'languagePolicy':profile.spoken_language_policy,'sourceOriginalLanguage':profile.source_original_language,'resolvedProductionLanguage':profile.resolved_production_language},'artisticQualityJudged':False}


def compile_subtitle_track(track: SubtitleTrack, lines: Sequence[ProductionDialogueLine], intents: Sequence[SemanticDialogueIntent], profile: ProductionLanguageProfile, context: Any) -> dict[str,Any]:
    track=SubtitleTrack.model_validate(dump_contract(track));validate_profile(profile)
    if not profile.subtitles.enabled:raise ValueError('SUBTITLES_DISABLED')
    if track.work_id!=profile.work_id or track.track_language not in profile.subtitles.languages or track.language_profile_hash!=sha256_canonical(profile):raise ValueError('SUBTITLE_PROFILE_MISMATCH')
    by_id={x.line_id:x for x in lines};meanings={x.line_id:x for x in intents};rows=[]
    if len({q.cue_id for q in track.cues})!=len(track.cues):raise ValueError('DUPLICATE_SUBTITLE_CUE')
    for q in track.cues:
        if q.localization_status=='UPSTREAM_LOCALIZATION_CONFLICT':raise ValueError('UPSTREAM_LOCALIZATION_CONFLICT')
        if bool(q.dialogue_line_id)==bool(q.narration_cue_id):raise ValueError('ONE_SUBTITLE_SOURCE_REQUIRED')
        if q.narration_cue_id:raise ValueError('ADOPTED_NARRATION_LOCALIZATION_REQUIRED')
        line=by_id.get(q.dialogue_line_id or '')
        if not line or line.line_id not in meanings:raise ValueError('SUBTITLE_PRODUCTION_LINE_REQUIRED')
        compile_localization(line,meanings[line.line_id],profile,context)
        validate_localization(line,meanings[line.line_id],profile,for_speech=track.purpose=='PRODUCTION')
        if track.purpose!=line.purpose:raise ValueError('SUBTITLE_FIXTURE_SCOPE_MISMATCH')
        if (q.target_language!=track.track_language or q.source_text_language!=line.production_language or q.production_line_hash!=sha256_canonical(line) or q.semantic_intent_ref!=line.semantic_intent_hash or q.speaker_ref!=line.character_id or q.scene_id!=line.scene_id):raise ValueError('SUBTITLE_SOURCE_BINDING_MISMATCH')
        rows.append({'cueId':q.cue_id,'productionDialogue':line.line_id,'productionLineHash':q.production_line_hash,'semanticIntentRef':q.semantic_intent_ref})
    return {'track':dump_contract(track),'sourceMap':rows,'delivery':'POST_PRODUCTION_OR_PLAYER','timing':'UNTIMED','renderAuthorized':False}


def require_subtitle_export(track: SubtitleTrack) -> None:
    raise ValueError('FINAL_SUBTITLE_TIMING_REQUIRES_APPROVED_SPEECH_AND_FINAL_EDIT')


def speech_rendition(auth: SpeechLanguageAuthorization) -> dict[str,Any]:
    validate_localization(auth.line,auth.intent,auth.profile,for_speech=True)
    import hashlib
    return {'sourceLineId':auth.line.line_id,'speakerKey':auth.line.character_id,
        'sourceTextHash':hashlib.sha256(auth.line.review_text.encode()).hexdigest(),
        'performanceLanguage':auth.line.production_language,'performanceText':auth.line.production_text,
        'renditionVersion':auth.line.review_subject_hash,'reviewStatus':'PASS'}


def validate_speech_authorization(auth: SpeechLanguageAuthorization, *, work_id: str, scene_id: str, line_id: str, speaker: str, exact_text: str, voice_language: str) -> None:
    validate_localization(auth.line,auth.intent,auth.profile,for_speech=True)
    if (work_id,scene_id,line_id,speaker,exact_text,language_tag(voice_language))!=(auth.profile.work_id,auth.line.scene_id,auth.line.line_id,auth.line.character_id,auth.line.production_text,auth.profile.resolved_production_language):raise ValueError('REVIEW_TEXT_OR_LANGUAGE_CANNOT_ENTER_SPEECH')


def require_work_speech_language(work: Any, request: Any) -> None:
    """Called at the existing real speech entry before Voice or HTTP side effects."""
    if work.content.get('creativeSourceType','HISTORICAL')!='LITERARY':return
    auth=request.production_language_authorization
    require_work_language_authorization(work, auth)
    validate_speech_authorization(auth,work_id=work.id,scene_id=request.scene_id,line_id=request.spoken_content_id,speaker=request.speaker_key,exact_text=request.exact_text,voice_language=request.voice_profile.creative_profile.language)


def require_work_language_authorization(work: Any, auth: SpeechLanguageAuthorization | None) -> None:
    """Shared exact-text authority for TTS and video-native speech."""
    raw=work.content.get('productionLanguageProfile')
    if not raw or auth is None:raise ValueError('APPROVED_PRODUCTION_DIALOGUE_REQUIRED')
    profile=ProductionLanguageProfile.model_validate(raw)
    if dump_contract(profile)!=dump_contract(auth.profile):raise ValueError('WORK_LANGUAGE_BINDING_MISMATCH')
    from drama_plugin.contracts.creative_source import LiteraryPackage
    package=LiteraryPackage.model_validate(work.content['literaryPackage'])
    resolve_source_language(package.artifacts,[profile.source_language_metadata],package.source_artifact_id)
    approved=work.content.get('productionDialogueApprovals',{})
    if approved.get(auth.line.line_id)!=sha256_canonical(auth.line):raise ValueError('CURRENT_WORK_DIALOGUE_APPROVAL_REQUIRED')
    if profile.work_id != work.id:
        raise ValueError('WORK_LANGUAGE_BINDING_MISMATCH')
    validate_localization(auth.line, auth.intent, profile, for_speech=True)


def native_dialogue_spec(spec: Any, authorizations: Sequence[SpeechLanguageAuthorization], *, required: bool = False) -> Any:
    """Project approved production text without changing frozen review/canon text.

    Unbound legacy specs remain readable for offline diagnostics only. The live
    submission gate always uses required=True. Character offsets in review text
    cannot be reused as offsets in a translation.
    """
    if not authorizations and not required:
        return spec
    by_id = {a.line.line_id: a for a in authorizations}
    if len(by_id) != len(authorizations) or set(by_id) != {d.spoken_content_id for d in spec.dialogue}:
        raise ValueError('APPROVED_PRODUCTION_DIALOGUE_REQUIRED')
    languages = {a.profile.resolved_production_language for a in authorizations}
    if len(languages) > 1:
        raise ValueError('NATIVE_VIDEO_LANGUAGE_BINDING_MISMATCH')
    projected = []
    for d in spec.dialogue:
        a = by_id[d.spoken_content_id]
        validate_localization(a.line, a.intent, a.profile, for_speech=True)
        if (a.profile.work_id != spec.work_id or a.line.scene_id != spec.scene_id
                or a.line.character_id != d.speaker_key or a.line.review_text != d.text):
            raise ValueError('NATIVE_VIDEO_DIALOGUE_SOURCE_MISMATCH')
        if d.text_range is not None:
            raise ValueError('LOCALIZED_DIALOGUE_COVERAGE_REQUIRED')
        projected.append(d.model_copy(update={'text': a.line.production_text}))
    return spec.model_copy(update={'dialogue': tuple(projected)})


def prepare_native_video_language(work: Any, requirements: Any,
                                  authorizations: Sequence[SpeechLanguageAuthorization]) -> Any:
    """Existing language owner prepares binding before provider/IR projection.

    resolve_profile / bind_work owns source_original -> ru. This consumes that
    immutable Work decision and reviewed ProductionDialogueLine, never translates.
    """
    from drama_plugin.visual.cinematic import verify_frozen
    spec = verify_frozen(requirements.frozen_creative['cinematic_direction'])
    native_dialogue_spec(spec, authorizations, required=True)
    for auth in authorizations:
        require_work_language_authorization(work, auth)
        require_native_runtime_language(work, auth.profile)
    if not authorizations:
        return requirements
    language = authorizations[0].profile.resolved_production_language
    changes: dict[str, Any] = {'language': language, 'production_dialogue': tuple(authorizations)}
    if requirements.video_request is not None:
        changes['video_request'] = requirements.video_request.model_copy(update={'production_dialogue': tuple(authorizations)})
    return requirements.model_copy(update=changes)


def require_video_request_language(request: Any) -> None:
    """Adapter-side exact IR audio binding, before URLs or HTTP submission."""
    bindings = [b for b in request.prompt_projection.audio if b.kind == 'DIALOGUE'] if request.prompt_projection else []
    auths = request.production_dialogue
    facts = (request.prompt_ir or {}).get('video_temporal', {}).get('audio_requirements', [])
    annotated = {b.path for b in request.prompt_projection.audio} if request.prompt_projection else set()
    if any(f'video.audio_requirements[{i}]' not in annotated for i in range(len(facts))):
        raise ValueError('NATIVE_VIDEO_AUDIO_CLASSIFICATION_REQUIRED')
    if not bindings and not auths:
        return
    if not request.native_audio or len(bindings) != len(auths):
        raise ValueError('APPROVED_PRODUCTION_DIALOGUE_REQUIRED')
    remaining = list(bindings)
    for a in auths:
        validate_localization(a.line, a.intent, a.profile, for_speech=True)
        if a.profile.work_id != request.continuity.work_id:
            raise ValueError('WORK_LANGUAGE_BINDING_MISMATCH')
        matches = [b for b in remaining if b.speaker == a.line.character_id
                   and b.language == a.profile.resolved_production_language
                   and b.text_hash == sha256_canonical(a.line.production_text)
                   and any(b.path == f'video.audio_requirements[{i}]' and f['text'] == a.line.production_text
                           for i, f in enumerate(facts))]
        if len(matches) != 1:
            raise ValueError('NATIVE_VIDEO_PRODUCTION_TEXT_REQUIRED')
        remaining.remove(matches[0])


def require_native_runtime_language(work: Any, profile: ProductionLanguageProfile) -> None:
    from drama_plugin.config.loader import load_config
    from drama_plugin.contracts.creative_source import LiteraryPackage
    package = LiteraryPackage.model_validate(work.content['literaryPackage'])
    current = resolve_profile(work.id, load_config(), package.artifacts,
                              [profile.source_language_metadata], package.source_artifact_id)
    if current.resolved_production_language != profile.resolved_production_language:
        raise ValueError('RUNTIME_SPOKEN_LANGUAGE_CONFLICT')


def require_native_video_submission(work: Any, decision: dict[str, Any]) -> None:
    """Live Work gate shared by formal HTTP and MCP begin-submission."""
    from drama_plugin.visual.video_selection import Requirements
    from drama_plugin.visual.cinematic import verify_frozen
    r = Requirements.model_validate(decision['requirements'])
    frozen = r.frozen_creative.get('cinematic_direction')
    if frozen:
        spec = verify_frozen(frozen)
        if spec.dialogue:
            native_dialogue_spec(spec, r.production_dialogue, required=True)
            if r.sound == 'SILENT':
                raise ValueError('CANONICAL_DIALOGUE_CANNOT_BE_SILENCED')
    elif r.sound != 'SILENT' and work.content.get('creativeSourceType') == 'LITERARY':
        raise ValueError('NATIVE_VIDEO_DIALOGUE_SCOPE_REQUIRED')
    for a in r.production_dialogue:
        require_work_language_authorization(work, a)
        require_native_runtime_language(work, a.profile)
        if r.language != a.profile.resolved_production_language:
            raise ValueError('NATIVE_VIDEO_LANGUAGE_BINDING_MISMATCH')
    if r.video_request:
        if r.video_request.production_dialogue != r.production_dialogue:
            raise ValueError('NATIVE_VIDEO_LANGUAGE_BINDING_MISMATCH')
        require_video_request_language(r.video_request)


def validate_work_language(content: dict[str,Any], previous: dict[str,Any] | None=None) -> None:
    raw=content.get('productionLanguageProfile')
    old=(previous or {}).get('productionLanguageProfile')
    if old is not None and old!=raw:raise ValueError('WORK_LANGUAGE_PROFILE_IMMUTABLE')
    if raw is not None:
        if content.get('creativeSourceType')!='LITERARY':raise ValueError('HISTORICAL_LANGUAGE_ADAPTER_NOT_IMPLEMENTED')
        profile=ProductionLanguageProfile.model_validate(raw);validate_profile(profile)
        from drama_plugin.contracts.creative_source import LiteraryPackage
        p=LiteraryPackage.model_validate(content['literaryPackage'])
        resolve_source_language(p.artifacts,[profile.source_language_metadata],p.source_artifact_id)
