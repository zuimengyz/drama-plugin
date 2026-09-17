"""Full-film coverage and semantic isolation over source-derived artifacts.

No business entities, persistence, IO, provider execution or second DPD authority.
Natural-language review is an attestation; lexical checks are not semantic AI.
"""
from __future__ import annotations
import re
from typing import Any, Mapping, Sequence
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, BeatDPD
from drama_plugin.dpd import compose_dpd
from drama_plugin.contracts.sequence import FilmReview, SourcePin

CATEGORIES = ('scenes', 'characters', 'shots', 'spoken', 'silent', 'interactions', 'ensemble', 'continuity', 'voice', 'av_plan')
STANDARD = frozenset({'core','objective_ref','target_ref','expression','physical','partner','continuity_in','continuity_out','do_not'})
CONTINUITY_FIELDS = frozenset({'physical_load','fatigue','injury','breath_load','voice_load','expression_baseline','release_residue','attention','interaction_residue','return_condition'})


def parse_proposal(text: str) -> list[dict[str, Any]]:
    """Read numbered local proposal scenes and exact lexical items, never old totals."""
    chunks = re.split(r'^## (P\d+)\s+([^\n]+)\n', text, flags=re.M)
    result: list[dict[str, Any]] = []
    for i in range(1, len(chunks), 3):
        key, title, body = chunks[i:i+3]
        body = body.split('\n## ', 1)[0]
        purpose = re.search(r'\*\*Scene Purpose：\*\*(.*)', body)
        if not purpose: raise ValueError('SOURCE_PURPOSE_MISSING: '+key)
        lines: list[dict[str, str]] = []
        for m in re.finditer(r'\*\*([^\n〔]+)〔([^〕]+)〕：\*\*\s*(?:“([^”]+)”|> ([^\n]+))', body):
            lines.append({'ref':m[2].split('·')[0], 'scene':key, 'speaker':m[1], 'text':m[3] or m[4]})
        action = body.split('**Action**',1)[1].split('**Silence',1)[0]
        paragraphs=[x.strip() for x in action.split('\n\n') if x.strip() and not x.lstrip().startswith(('**','>'))]
        # Include the final silent aftermath, not editorial/reading commentary.
        if '**Silence**' in body:
            tail=body.split('**Silence**',1)[1].split('**Ending',1)[0]
            paragraphs += [x.strip() for x in tail.split('\n\n') if x.strip()]
        result.append({'ref':key,'title':title,'purpose':purpose[1].strip(),'body':body,'spoken':lines,'action_paragraphs':paragraphs})
    refs=[x['ref'] for s in result for x in s['spoken']]
    if not result or len(refs)!=len(set(refs)):raise ValueError('SOURCE_SCENES_OR_UNIQUE_SPOKEN_REQUIRED')
    return result


def validate_performance_context_isolation(*, context: Mapping[str, Any], refs: Sequence[str],
                                            text: str, foreign_contexts: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    entities=context.get('entities',{})
    findings: list[dict[str, str]]=[]
    for ref in refs:
        entity=entities.get(ref)
        if not entity or entity.get('scope')!=context.get('scope') or not entity.get('source_ref') or not entity.get('evidence'):
            findings.append({'code':'FOREIGN_OR_UNBOUND_CONTEXT_REF','evidence':ref,'sourceContext':str(context.get('scope'))})
    allowed={str(e['display']) for e in entities.values()} | {str(a) for e in entities.values() for a in e.get('aliases',[])}
    for foreign in foreign_contexts:
        if foreign.get('scope')==context.get('scope'):continue
        for ref,entity in foreign.get('entities',{}).items():
            for token in [entity['display'],*entity.get('aliases',[])]:
                if token and token not in allowed and not any(token in str(e['display']) for e in entities.values() if e['kind'] != 'action') and token in text:
                    findings.append({'code':'FOREIGN_'+entity['kind'].upper()+'_LEAKAGE','evidence':token,'foreignRef':ref,'sourceContext':str(context.get('scope'))})
    return {'status':'FAIL' if findings else 'PASS','findings':findings,'contextFingerprint':sha256_canonical(context),
            'limit':'Refs and known foreign lexemes checked; professional semantic review remains required.'}


def render_bound_direction(template: str, context: Mapping[str, Any], *, foreign_contexts: Sequence[Mapping[str, Any]] = ()) -> str:
    refs: list[str]=[]
    def resolve(match: re.Match[str]) -> str:
        name=match[1]
        if name not in context.get('entities',{}):raise ValueError('UNBOUND_TEMPLATE_CONTEXT_REF')
        refs.append(name)
        return str(context['entities'][name]['display'])
    text=re.sub(r'\{([^{}]+)\}',resolve,template)
    result=validate_performance_context_isolation(context=context,refs=refs,text=text,foreign_contexts=foreign_contexts)
    if result['status']!='PASS':raise ValueError('PERFORMANCE_CONTEXT_LEAKAGE: '+str(result['findings']))
    return text


def validate_interaction(direction: Mapping[str, Any], dpds: Mapping[str, DPDSnapshot | BeatDPD]) -> None:
    required=('speaker_ref','listener_ref','speaker_action','listener_action','speaker_target','listener_attention','gaze_handoff','voice_handoff','physical_handoff','partner_cue','response_timing','next_beat_owner')
    if any(not direction.get(k) for k in required):raise ValueError('INTERACTION_DIRECTION_INCOMPLETE')
    for side in ('speaker','listener'):
        ref=direction.get(side+'_dpd');dpd=dpds.get(str(ref))
        if dpd is None:raise ValueError('PARTNER_DPD_REQUIRED: '+side)
        if isinstance(dpd,DPDSnapshot):
            if compose_dpd(dpd.scene,dpd.beat,dpd.line)!=dpd:raise ValueError('DPD_AUTHORITY_MISMATCH')
            actor=dpd.effective.actor
        else:actor=dpd.actor
        if actor!=direction[side+'_ref']:raise ValueError('PARTNER_DPD_SCOPE_MISMATCH')
    if direction['next_beat_owner'] not in (direction['speaker_ref'],direction['listener_ref']):raise ValueError('UNBOUND_NEXT_BEAT_OWNER')


def validate_ensemble(direction: Mapping[str, Any], dpds: Mapping[str, DPDSnapshot | BeatDPD]) -> None:
    if any(k in direction for k in ('psychology','subtext','knowledge','objective')):raise ValueError('NO_CROWD_PSYCHOLOGY')
    groups=direction.get('groups',[])
    if not groups:raise ValueError('ENSEMBLE_DIRECTION_MISSING')
    for g in groups:
        dpd=dpds.get(g.get('dpd_ref'))
        actor=dpd.effective.actor if isinstance(dpd,DPDSnapshot) else dpd.actor if isinstance(dpd,BeatDPD) else None
        if actor!=g.get('group_ref'):raise ValueError('GROUP_DPD_REQUIRED')
        if any(not g.get(k) for k in ('attention','trigger','response','task_persistence','variation')) or not isinstance(g.get('latency_order'),int):raise ValueError('ENSEMBLE_LAYER_INCOMPLETE')
    if len(groups)>1 and len({g['latency_order'] for g in groups})==1 and not direction.get('script_sync_reason'):
        raise ValueError('NPC_SYNCHRONIZATION_FORBIDDEN')
    if direction.get('added_spoken_content'):raise ValueError('SCRIPT_SOUND_AUTHORITY_VIOLATION')


def validate_continuity_edge(edge: Mapping[str, Any]) -> None:
    previous=edge.get('previous_exit',{});entry=edge.get('next_entry',{})
    if set(previous)!=CONTINUITY_FIELDS or set(entry)!=CONTINUITY_FIELDS:raise ValueError('CONTINUITY_STATE_INCOMPLETE_OR_SECOND_PSYCHOLOGY')
    if any(not str(v).strip() for v in (*previous.values(),*entry.values())):raise ValueError('CONTINUITY_STATE_EMPTY')
    changed={k for k in CONTINUITY_FIELDS if previous[k]!=entry[k]}
    transitions=edge.get('transitions',{})
    if changed!=set(transitions) or any(not v.get('reason') or not v.get('source_ref') for v in transitions.values()):
        raise ValueError('PERFORMANCE_CONTINUITY_CONFLICT')
    ranks={'LOW':0,'MEDIUM':1,'HIGH':2,'EXTREME':3}
    if entry['physical_load'] in ranks and entry['voice_load'] in ranks and ranks[entry['physical_load']]-ranks[entry['voice_load']]>1:
        raise ValueError('BODY_VOICE_LOAD_CONFLICT')
    if previous['release_residue'].startswith('TEMPORARY:') and entry['release_residue'].startswith('PERMANENT:'):
        raise ValueError('RELEASE_CANNOT_OVERWRITE_BASELINE')


def full_performance_coverage_gate(inventory: Mapping[str, Any], directions: Mapping[str, Any], *, current_source_hash: str,
                                    contexts: Mapping[str, Any], dpds: Mapping[str, DPDSnapshot | BeatDPD], source_text: str | None = None) -> dict[str, Any]:
    if inventory.get('source_hash')!=current_source_hash:raise ValueError('STALE_SOURCE')
    if inventory.get('scope') == 'PROPOSAL_ONLY':
        import hashlib
        if source_text is None or hashlib.sha256(source_text.encode()).hexdigest() != current_source_hash:
            raise ValueError('CURRENT_PROPOSAL_TEXT_REQUIRED')
        actual = parse_proposal(source_text)
        expected_sets = {
            'scenes': {s['ref'] for s in actual},
            'spoken': {s['ref']+':spoken:'+line['ref'] for s in actual for line in s['spoken']},
            'silent': {s['ref']+':silent:'+str(i).zfill(2) for s in actual for i in range(1, len(s['action_paragraphs'])+1)},
        }
        if any({x['ref'] for x in inventory.get(k, [])} != refs for k, refs in expected_sets.items()):
            raise ValueError('SOURCE_COVERAGE_INVENTORY_MISMATCH')
    rows: dict[str, Any]={};missing: list[dict[str,str]]=[]
    for category in CATEGORIES:
        expected=inventory.get(category)
        if expected is None:raise ValueError('COVERAGE_INVENTORY_MISSING: '+category)
        ids=[x['ref'] for x in expected]
        if len(set(ids))!=len(ids):raise ValueError('DUPLICATE_COVERAGE_REF')
        covered=0;na=0
        for item in expected:
            d=directions.get(item['ref'])
            reason=''
            if not d:reason='DIRECTION_MISSING'
            elif d.get('status')=='NOT_APPLICABLE_WITH_REASON':
                if item.get('performance_bearing',True) or not d.get('reason') or any(item.get(x) for x in ('actors','vocal','ensemble')):reason='INVALID_NO_ACTOR_EXEMPTION'
                else:na+=1;continue
            else:
                if d.get('status') != 'COVERED':reason='DIRECTION_STATUS_NOT_COVERED'
                elif d.get('source_ref')!=item.get('source_ref') or d.get('scene')!=item.get('scene'):reason='DIRECTION_SOURCE_SCOPE_MISMATCH'
                elif any(not d.get(k) for k in STANDARD):reason='STANDARD_DIRECTION_INCOMPLETE'
                elif d.get('detail') not in ('STANDARD','EXPANDED'):reason='DIRECTION_DETAIL_REQUIRED'
                elif d.get('objective_ref') not in dpds:reason='DPD_REQUIRED'
                elif item.get('vocal') and any(not d.get(k) for k in ('voice','speech_action','vocal_mode','handoff','closure')):reason='VOICE_DIRECTION_INCOMPLETE'
                else:
                    context=contexts.get(item['scene'],{})
                    isolation=validate_performance_context_isolation(context=context,refs=d.get('context_refs',[]),text=' '.join(str(d.get(k,'')) for k in (*STANDARD,'voice','speech_action','handoff','closure')),foreign_contexts=list(contexts.values()))
                    if not d.get('context_refs') or d.get('context_fingerprint')!=sha256_canonical(context) or isolation['status']!='PASS':reason='PERFORMANCE_CONTEXT_LEAKAGE'
                    elif d['target_ref'] not in context.get('entities',{}):reason='UNBOUND_INTERACTION_TARGET'
                    elif not d.get('semantic_review',{}).get('evidence') or d['semantic_review'].get('status')!='PASS':reason='PROFESSIONAL_SEMANTIC_REVIEW_REQUIRED'
                if not reason:
                    try:
                        if category=='interactions':validate_interaction(d['interaction'],dpds)
                        if category=='ensemble':validate_ensemble(d['ensemble'],dpds)
                        if category=='continuity':validate_continuity_edge(d['edge'])
                    except (ValueError,KeyError) as exc:reason=str(exc)
            if reason:missing.append({'category':category,'ref':item['ref'],'reason':reason})
            else:covered+=1
        empty_reason=inventory.get('not_applicable',{}).get(category)
        if not expected and not empty_reason:missing.append({'category':category,'ref':'scope','reason':'EMPTY_INVENTORY_WITHOUT_REASON'})
        if category=='shots' and inventory.get('scope')=='FORMAL_PRODUCTION_BOOK' and not expected:missing.append({'category':category,'ref':'scope','reason':'FORMAL_SHOT_INVENTORY_REQUIRED'})
        rows[category]={'required':len(expected),'covered':covered,'notApplicable':na,'status':'MISSING' if any(x['category']==category for x in missing) else 'COVERED' if expected else 'NOT_APPLICABLE_WITH_REASON','reason':empty_reason}
    return {'status':'FULL_PERFORMANCE_COVERAGE_INCOMPLETE' if missing else 'FULL_PERFORMANCE_COVERAGE_READY','coverage':rows,'findings':missing,'inventoryFingerprint':sha256_canonical(inventory),'derivedArtifactOnly':True,'productionAuthorized':False}


def bind_full_performance_review(review: FilmReview, inventory: Mapping[str, Any]) -> FilmReview:
    """All performance-bearing fragments, not just a selected set of hero Beats."""
    expected=tuple(x['review_key'] for x in inventory['av_plan'] if x.get('performance_bearing',True))
    if len(expected)!=len(set(expected)):raise ValueError('DUPLICATE_AV_COVERAGE_KEY')
    if not expected:raise ValueError('AV_PERFORMANCE_INVENTORY_REQUIRED')
    payload=dump_contract(review)
    payload.update(performanceRequiredBeats=list(expected),performanceCoverageFingerprint=sha256_canonical(inventory),performanceCoverageChannels={x['review_key']:x['channels'] for x in inventory['av_plan'] if x.get('performance_bearing',True)})
    return FilmReview.model_validate(payload)


def full_av_coverage(review: FilmReview) -> dict[str, Any]:
    missing=[]
    for key in review.performance_required_beats:
        row=review.performance_beats.get(key,{})
        evidence=[o for o in review.performance_observations if o.beat_id+'#'+o.spoken_content_id==key]
        required_channels=set(review.performance_coverage_channels.get(key, ('VISUAL','VOICE')))
        from drama_plugin.performance_direction import ALIGNMENT_DIMENSIONS
        essential = ALIGNMENT_DIMENSIONS if 'VOICE' in required_channels else {'emotional_amplitude','external_control','interaction_target','timing','continuity','release_point','story_meaning'}
        unknown = any(o.external_expression == 'UNKNOWN' or o.external_control == 'UNKNOWN' or o.body_load == 'UNKNOWN' or o.meaning_preserved != 'PASS' or not o.interaction_target or not o.breath or not o.continuity_in or not o.continuity_out for o in evidence)
        if not essential <= set(row) or any(v!='PASS' for v in row.values()) or {o.channel for o in evidence} != required_channels or unknown or any(o.method=='DESIGN_FIXTURE' for o in evidence):missing.append(key)
    return {'status':'AV_PERFORMANCE_COVERAGE_INCOMPLETE' if missing or not review.performance_required_beats else 'COVERED','missing':missing,'adopted':False}
