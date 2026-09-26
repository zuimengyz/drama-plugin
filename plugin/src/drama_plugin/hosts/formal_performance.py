"""Read-only canonical enumeration for formal performance review.

Only Host-configured MemoryProvider IO can issue a witness. Serialized caller
inventories and proposal parsers never issue one. No new persistence or endpoint.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.dpd import DPDSnapshot, SceneDPD, BeatDPD
from drama_plugin.dpd import compose_dpd
from drama_plugin.providers.base import MemoryProvider

_ISSUER = object()

@dataclass(frozen=True)
class FormalSourceWitness:
    """Ephemeral Host value, not a serializable business contract or approval."""
    _issuer: object
    _tree_json: str

    @property
    def tree(self) -> dict[str, Any]:
        if self._issuer is not _ISSUER:
            raise ValueError('TRUSTED_FORMAL_READER_REQUIRED')
        value: dict[str, Any] = json.loads(self._tree_json)
        return value

    @property
    def fingerprint(self) -> str:
        return sha256_canonical(self.tree)

    @property
    def pins(self) -> dict[str, str]:
        return {kind+':'+obj['id']:sha256_canonical(obj) for kind, objects in self.tree.items() for obj in objects}

    def obligations(self) -> dict[str, dict[str, dict[str, Any]]]:
        tree=self.tree
        result: dict[str, dict[str, dict[str, Any]]] = {k:{} for k in ('scenes','shots','spoken','silent','characters','voice','interactions','ensemble','continuity','av_plan')}
        for scene in tree['scenes']:
            sid=scene['id'];content=scene['content']
            result['scenes'][sid]={'scene':sid,'source_ref':'scenes:'+sid}
            for line in content.get('spokenContent',[]):
                ref=sid+':spoken:'+line['id']
                result['spoken'][ref]={'scene':sid,'source_ref':'scenes:'+sid,'line':line}
            action=content.get('screenplayAction')
            if not isinstance(action,str) or not action.strip():
                raise ValueError('FORMAL_ACTION_SOURCE_REQUIRED:'+sid)
            # Conservative source anchors: every sentence is an obligation. An owner
            # may explain NO_ACTOR, never silently drop an unparsed action paragraph.
            for index, sentence in enumerate(filter(str.strip,re.split(r'(?<=[。！？!?])',action)),1):
                result['silent'][sid+':action:'+str(index)]={'scene':sid,'source_ref':'scenes:'+sid,'source_excerpt':sentence.strip()}
        for shot in tree['shots']:
            result['shots'][shot['id']]={'scene':shot['sceneId'],'source_ref':'shots:'+shot['id']}
        previous: dict[str,str]={}
        for scene in sorted(tree['scenes'],key=lambda x:(x['episodeId'],x['order'])):
            sid=scene['id'];characters=scene['content'].get('characters',[])
            for actor in characters:
                result['characters'][sid+':actor:'+actor]={'scene':sid,'source_ref':'scenes:'+sid,'actor':actor}
                if actor in previous:
                    result['continuity'][actor+':'+previous[actor]+'>'+sid]={'scene':sid,'source_ref':'scenes:'+sid}
                previous[actor]=sid
            if scene['content'].get('dramaturgy') is not None:
                from drama_plugin.scene_dramaturgy import source_dramaturgy, carrier_text
                facet = source_dramaturgy(scene)
                for edge in facet.interactions:
                    ref = sid + ':interaction:' + edge.action_ref + '>' + edge.response_ref
                    result['interactions'][ref] = {'scene': sid, 'source_ref': 'scenes:' + sid,
                        'action_ref': edge.action_ref, 'response_ref': edge.response_ref}
                for carrier in facet.carriers:
                    if carrier.important and carrier.role == 'SILENCE' and carrier.silence_function != 'ENVIRONMENTAL':
                        result['silent'][sid + ':silence:' + carrier.ref] = {'scene': sid,
                            'source_ref': 'scenes:' + sid, 'source_excerpt': carrier_text(scene, carrier.ref),
                            'carrier_ref': carrier.ref}
            elif len(characters)>1:
                # Historical inventories remain inspectable; validate() rejects
                # their use for a new formal Book without the R3B handoff.
                result['interactions'][sid+':interaction']={'scene':sid,'source_ref':'scenes:'+sid}
            if scene['content'].get('performanceGroups'):
                result['ensemble'][sid+':ensemble']={'scene':sid,'source_ref':'scenes:'+sid}
        result['voice']={k:dict(v) for k,v in result['spoken'].items()}
        for category in ('shots','spoken','silent','interactions','ensemble'):
            for ref,item in result[category].items():
                result['av_plan']['av:'+ref]={**item,'review_key':ref+'#performance','channels':['VISUAL','VOICE'] if category=='spoken' else ['VISUAL']}
        return result

    def validate(self, inventory: Mapping[str, Any], directions: Mapping[str, Any],
                 dpds: Mapping[str, DPDSnapshot | BeatDPD], scene_dpds: Mapping[str, SceneDPD],
                 current_source_hash: str, *, dramaturgy_reviews: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if current_source_hash != self.fingerprint or inventory.get('source_hash') != self.fingerprint:
            raise ValueError('STALE_FORMAL_SOURCE')
        if inventory.get('scope') != 'FORMAL_PRODUCTION_BOOK':
            raise ValueError('FORMAL_SOURCE_KIND_REQUIRED')
        tree=self.tree; scenes={s['id']:s for s in tree['scenes']}
        if set(scene_dpds)!=set(scenes):raise ValueError('FORMAL_DPD_INVENTORY_REQUIRED')
        for sid, scene_dpd in scene_dpds.items():
            if scene_dpd.scene_id!=sid or scene_dpd.source_fingerprint!=sha256_canonical(scenes[sid]):
                raise ValueError('FORMAL_DPD_SOURCE_BINDING_REQUIRED')
        expected=self.obligations()
        for category, obligations in expected.items():
            actual=inventory.get(category,[])
            if len(actual)!=len(obligations) or {x['ref'] for x in actual}!=set(obligations):
                raise ValueError('FORMAL_INVENTORY_MISMATCH:'+category)
            for item in actual:
                truth=obligations[item['ref']]
                if any(item.get(k)!=truth[k] for k in ('scene','source_ref')):
                    raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
                if category=='characters':
                    character_dpd=dpds.get(directions.get(item['ref'],{}).get('objective_ref'))
                    actual_actor=character_dpd.effective.actor if isinstance(character_dpd,DPDSnapshot) else character_dpd.actor if character_dpd else None
                    if actual_actor!=truth['actor']:raise ValueError('FORMAL_CHARACTER_DPD_REQUIRED')
                if category=='silent' and item.get('source_excerpt')!=truth['source_excerpt']:
                    raise ValueError('FORMAL_ACTION_BINDING_REQUIRED')
                if category in ('spoken', 'voice') or category == 'av_plan' and 'line' in truth:
                    from drama_plugin.screenplay_playability import validate_exact_turn
                    bound = dpds.get(directions.get(item['ref'], {}).get('objective_ref'))
                    if not isinstance(bound, DPDSnapshot):
                        raise ValueError('FORMAL_LINE_DPD_REQUIRED')
                    validate_exact_turn(scenes[truth['scene']], truth['line']['id'], bound)
                    if directions[item['ref']].get('target_ref') != truth['line'].get('target'):
                        raise ValueError('EXACT_DIALOGUE_TARGET_MISMATCH')
        valid_beats={x for category in expected.values() for x in category}
        for sid, scene in scenes.items():
            if scene['content'].get('dramaturgy'):
                from drama_plugin.scene_dramaturgy import source_dramaturgy
                valid_beats.update(sid + ':carrier:' + c.ref for c in source_dramaturgy(scene).carriers)
        for ref, dpd in dpds.items():
            beat=dpd.beat if isinstance(dpd,DPDSnapshot) else dpd
            if beat.scene_id not in scenes or beat.beat_id not in valid_beats:
                raise ValueError('FORMAL_BEAT_SOURCE_BINDING_REQUIRED')
            if isinstance(dpd,DPDSnapshot):
                line_ref=beat.scene_id+':spoken:'+dpd.line.spoken_content_id
                line=expected['spoken'].get(line_ref,{}).get('line')
                if (dpd.scene!=scene_dpds[beat.scene_id] or not line or line['speakerKey']!=dpd.line.speaker
                        or compose_dpd(dpd.scene,dpd.beat,dpd.line)!=dpd):
                    raise ValueError('FORMAL_LINE_DPD_SOURCE_BINDING_REQUIRED')
        # Legacy snapshots remain readable; new formal review requires R2 witnesses.
        from drama_plugin.screenplay_playability import validate_beat_playability, validate_line_playability
        for dpd in dpds.values():
            beat = dpd.beat if isinstance(dpd, DPDSnapshot) else dpd
            validate_beat_playability(scenes[beat.scene_id], beat)
            if isinstance(dpd, DPDSnapshot):
                validate_line_playability(scenes[beat.scene_id], dpd)
        covered_lines = {(d.scene.scene_id, d.line.spoken_content_id)
                         for d in dpds.values() if isinstance(d, DPDSnapshot)}
        if any((s['id'], line['id']) not in covered_lines
               for s in scenes.values() for line in s['content'].get('spokenContent', [])):
            raise ValueError('UNRESOLVED: screenplay dialogue performance coverage')
        for category in inventory:
            if category not in ('scenes','characters','shots','spoken','silent','interactions','ensemble','continuity','voice','av_plan'):continue
            for item in inventory[category]:
                sid=item.get('scene');d=directions.get(item['ref'],{})
                if sid not in scenes or d.get('scene')!=sid:
                    raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
                bound_dpd=dpds.get(d.get('objective_ref'))
                if not bound_dpd or (bound_dpd.scene.scene_id if isinstance(bound_dpd,DPDSnapshot) else bound_dpd.scene_id)!=sid:
                    raise ValueError('FORMAL_DPD_DIRECTION_BINDING_REQUIRED')
                if category == 'interactions' and 'action_ref' in expected[category][item['ref']]:
                    from drama_plugin.scene_dramaturgy import source_dramaturgy
                    carriers = {c.ref: c for c in source_dramaturgy(scenes[sid]).carriers}
                    truth = expected[category][item['ref']]
                    interaction = d.get('interaction', {})
                    if any(interaction.get(k) != truth[k] for k in ('action_ref', 'response_ref')):
                        raise ValueError('LISTENER_CAUSAL_COVERAGE_MISMATCH')
                    for side, carrier_ref in [('speaker', truth['action_ref']), ('listener', truth['response_ref'])]:
                        partner = dpds.get(interaction.get(side + '_dpd'))
                        partner_beat = partner.beat if isinstance(partner, DPDSnapshot) else partner
                        if (partner_beat is None or partner_beat.actor != carriers[carrier_ref].actor or not partner_beat.playability
                                or carrier_ref not in (*partner_beat.playability.action_carrier_refs, partner_beat.playability.reaction_carrier_ref)):
                            raise ValueError('LISTENER_CAUSAL_COVERAGE_MISMATCH')
                if category == 'silent' and 'carrier_ref' in expected[category][item['ref']]:
                    beat = bound_dpd.beat if isinstance(bound_dpd, DPDSnapshot) else bound_dpd
                    carrier_ref = expected[category][item['ref']]['carrier_ref']
                    if not beat.playability or carrier_ref not in (*beat.playability.action_carrier_refs, beat.playability.reaction_carrier_ref):
                        raise ValueError('SILENCE_CAUSAL_COVERAGE_MISMATCH')
        from drama_plugin.scene_dramaturgy import review_scene_dramaturgy
        if dramaturgy_reviews is None or set(dramaturgy_reviews) != set(scenes):
            raise ValueError('UNRESOLVED:scene-development:FORMAL_DRAMATURGY_REVIEW_REQUIRED')
        receipts = {}
        for sid, scene in scenes.items():
            scoped = {k: d for k, d in dpds.items() if (d.scene.scene_id if isinstance(d, DPDSnapshot) else d.scene_id) == sid}
            receipts[sid] = review_scene_dramaturgy(scene, scoped, dramaturgy_reviews[sid])
        return receipts


async def read_formal_performance_source(memory: MemoryProvider, work_id: str) -> FormalSourceWitness:
    """Enumerate from the persisted Work root; callers cannot submit a shortened tree.

    The configured provider is Host authority (tests substitute a persisted fixture
    provider). No claim is made that arbitrary Python code is a security sandbox.
    A second read detects a changing source while gathering the parent chain.
    """
    async def read() -> dict[str,list[dict[str,Any]]]:
        work=await memory.get_work(work_id)
        tree={'work':[dump_contract(work)],'scripts':[],'episodes':[],'scenes':[],'shots':[]}
        for script in await memory.list_scripts(work_id):
            if script.work_id!=work_id:raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
            tree['scripts'].append(dump_contract(script))
            for episode in await memory.list_episodes(script.id):
                if episode.script_id!=script.id:raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
                tree['episodes'].append(dump_contract(episode))
                for scene in await memory.list_scenes(episode.id):
                    if scene.episode_id!=episode.id:raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
                    tree['scenes'].append(dump_contract(scene))
                    for shot in await memory.list_shots(scene.id):
                        if shot.scene_id!=scene.id:raise ValueError('FORMAL_PARENT_CHAIN_MISMATCH')
                        tree['shots'].append(dump_contract(shot))
        for kind,objects in tree.items():
            if not objects or len({o['id'] for o in objects})!=len(objects):raise ValueError('FORMAL_TREE_INCOMPLETE:'+kind)
            objects.sort(key=lambda x:x['id'])
        return tree
    first=await read();second=await read()
    if first!=second:raise ValueError('STALE_SOURCE_DURING_FORMAL_READ')
    return FormalSourceWitness(_ISSUER,json.dumps(first,ensure_ascii=False,sort_keys=True))


async def review_formal_book(memory: MemoryProvider, packet: Any, review: Any,
                             current: Mapping[str,str], artifacts: Mapping[str,dict[str,Any]],
                             performance: Mapping[str,Any], *, score_plan: Any = None) -> dict[str,Any]:
    """Host full-book entry always re-reads; never adopts a caller's old witness."""
    from drama_plugin.preproduction import complete_production_book
    witness=await read_formal_performance_source(memory,packet.scope_id)
    return complete_production_book(packet,review,{**current,**witness.pins},artifacts,
                                    performance={**performance,'formal_source':witness},score_plan=score_plan)
