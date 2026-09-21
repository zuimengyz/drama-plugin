"""Concrete, traceable compilation of existing HEROIC_CINEMATIC_CG intent.

No new style levels, provider policy, identity inference or event authoring.
"""
from typing import Any
import re
from drama_plugin.contracts.base import dump_contract, sha256_canonical
from drama_plugin.contracts.expression import CharacterExpressionProfiles, CastingArchetypeProfile, ApprovedVisualTargetRange
from drama_plugin.expression import PHYSICAL_BOUNDARY, select_expression

DIMENSIONS = ('bodyProportion', 'facialIntensity', 'silhouette', 'pose', 'camera',
              'costumeIconicity', 'environmentEnergy', 'kineticPotential', 'weapon')
FIELD_DIMENSIONS = {
    'heroicExaggeration': ('bodyProportion', 'silhouette'),
    'physicalPresence': ('bodyProportion', 'pose'),
    'martialAura': ('facialIntensity', 'pose', 'weapon'),
    'silhouetteStrength': ('silhouette',), 'facialIntensity': ('facialIntensity',),
    'costumeIconicity': ('costumeIconicity', 'silhouette'),
    'kineticPotential': ('kineticPotential', 'pose'),
    'cinematicScale': ('camera', 'environmentEnergy'),
    'imperialPresence': ('pose', 'camera', 'facialIntensity'),
}
# These describe visible emphasis on owner-authored structures, not generic anatomy.
FIELD_LANGUAGE = {
    'physicalPresence': ('quietly legible body volume', 'clear authored scale and weight relationships', 'emphatic authored body volume and load-bearing relationships', 'physically commanding scale through the instance-authored body design; clothing cannot substitute for anatomy'),
    'martialAura': ('attentive composure; no invented combat role', 'clear purposeful attention and support', 'emphasize the instance-authored readiness through attention and balance', 'strong readiness through the authored gaze, balance and task; add no weapon or military identity absent from the instance'),
    'silhouetteStrength': ('readable authored contour', 'clear separation of authored contours', 'strong character-specific contour and negative-space relationships', 'bold authored contour and internal separation that remain individually readable, without adding costume components'),
    'facialIntensity': ('subtle authored facial planes', 'clear authored facial planes and eye focus', 'stronger authored facial planes and role-specific eye focus without generic beautification', 'emphatic authored facial geometry and expressive focus; never impose a universal jaw, age, gender or fixed emotion'),
    'costumeIconicity': ('readable functional clothing', 'clear authored construction rhythm', 'distinctive authored clothing silhouette, layering and construction rhythm', 'unmistakable authored costume relationships with functional construction; invent no palette, equipment or motif'),
    'kineticPotential': ('settled supported posture', 'readable authored weight transfer', 'visible stored motion in the authored stance and relevant secondary elements', 'strong authored readiness through tension, support and causal secondary motion; no compulsory wind, prop, garment or attack'),
    'cinematicScale': ('readable subject scale', 'clear depth and subject separation', 'emphatic authored perspective and foreground-to-subject hierarchy', 'the complete character dominates visual mass through authored camera and depth; preserve design readability without prescribing a location or angle'),
    'imperialPresence': ('self-possessed spacing without invented rank', 'clear authored composure and spatial relation', 'emphasize the authored social position through attention and spatial rights', 'strong authored decision-making presence and compositional hierarchy; invent no rank, title or symbol'),
}
EXAGGERATION_LANGUAGE = {
    'restrained': 'Keep the authored CG structural relationships close to their specified baseline.',
    'elevated': 'Clearly emphasize the authored structural relationships with cinematic design.',
    'heroic': 'Make the instance-authored proportion and silhouette visibly designed beyond a photographed performer, retaining articulating anatomy, weight and individual character structure. Do not substitute a universal heroic body type.',
    'legendary': 'Intensify only the instance-authored structural contrasts to their declared upper range while retaining articulating anatomy, weight and functional construction; never escalate beyond an approved target range.',
}
# Generic medium conflicts only. Role-specific attenuation belongs to authored review.
CONFLICTS = (r'realistic actor', r'neutral studio', r'studio portrait', r'live.action (?:photo|casting)',
             r'真人定妆照', r'真人演员海报')


def audit_hero_prompt(segments: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Narrow conflict gate, not a claim to prove arbitrary prose consistency."""
    findings = []
    for row in segments:
        if row.get('kind') in ('boundary', 'negative', 'core'):
            continue
        for pattern in CONFLICTS:
            if re.search(pattern, row['text'], re.I):
                findings.append({'segment': row['id'], 'conflict': pattern})
    return findings


def compile_heroic_visual_intent(bundle: CharacterExpressionProfiles, route: str, mode: str,
                                intent: dict[str, str], style: dict[str, Any], *,
                                archetype: CastingArchetypeProfile | None = None,
                                target_range: ApprovedVisualTargetRange | None = None) -> dict[str, Any]:
    profile = select_expression(bundle, route)
    if profile.route != 'stylized_cinematic_cg' or profile.visual_language != 'HEROIC_CINEMATIC_CG':
        raise ValueError('HEROIC_VISUAL_COMPILER_ROUTE_FORBIDDEN')
    if mode not in ('HERO_CASTING', 'DESIGN_NEUTRAL'):
        raise ValueError('CASTING_MODE_REQUIRED')
    if mode == 'HERO_CASTING' and profile.heroic_exaggeration not in ('heroic', 'legendary'):
        raise ValueError('HERO_CASTING_REQUIRES_EXPLICIT_CG_HEROIC_PROFILE')
    if set(intent) != set(DIMENSIONS) or any(not isinstance(v,str) or not v.strip() for v in intent.values()):
        raise ValueError('COMPLETE_MODE_VISUAL_INTENT_REQUIRED')
    if style['visualRoute'] != route or style['visualLanguage'] != profile.visual_language:
        raise ValueError('CASTING_STYLE_EXPRESSION_LANGUAGE_MISMATCH')
    rows: list[dict[str, Any]] = []
    def emit(key: str, text: str, sources: list[str], kind: str = 'visual') -> None:
        rows.append({'id':key,'kind':kind,'text':text,'sources':sources, 'sourceLayer': ('archetype' if key=='archetype' else 'approved_target_range' if key.startswith('target.') else 'instance' if key=='core' or key.startswith('intent.') else 'historical_boundary' if key=='historicalBoundary' else 'route_style' if key in ('rendering','materials','negative') else 'generic_capability')})
        row = rows[-1]
        row['sourceLayers'] = list(dict.fromkeys([row['sourceLayer'], *(['instance'] if key.startswith('expression.') else [])]))
        row['topic'] = ('camera_composition' if key in ('framing','intent.camera') else 'anti_drift' if kind in ('negative','boundary') else 'character_expression')
    core=bundle.character_core_profile
    emit('mode', ('HEROIC_CINEMATIC_CG / HERO_CASTING. Sculpted feature-film CG character design; heroic composition and character-specific screen presence.' if mode=='HERO_CASTING' else
         'HEROIC_CINEMATIC_CG / DESIGN_NEUTRAL. Proportion and costume inspection plate with even visibility; baseline presentation without hero-staging amplification.'), ['spec.castingMode','route.style.visualLanguage'])
    emit('framing','FULL BODY, single person: entire head, both feet, both hands, body and clothing design, plus any instance-authored props inside the frame with margin. One character selection image.', ['spec.framing'])
    emit('core',f'Identity: {core.identity}; {core.archetype}. Personality: '+ '; '.join(core.personality_core)+ '. Historical position: '+core.historical_position+'. Fixed narrative facts (not extra events to illustrate): '+'; '.join(core.story_facts),['expressionProfiles.characterCoreProfile'],'core')
    if archetype is not None:
        archetype = CastingArchetypeProfile.model_validate(dump_contract(archetype))
        if archetype.key != core.archetype:
            raise ValueError('CASTING_ARCHETYPE_CORE_MISMATCH')
        emit('archetype','Dramatic archetype: '+'; '.join(archetype.traits),['spec.archetypeProfile'],'core')
    if target_range is not None:
        target_range = ApprovedVisualTargetRange.model_validate(dump_contract(target_range))
        if target_range.character != core.identity or target_range.visual_route != route or target_range.visual_language != profile.visual_language:
            raise ValueError('APPROVED_RANGE_INSTANCE_OR_ROUTE_MISMATCH')
        if mode == 'HERO_CASTING':
            emit('target.positive','Approved amplitude range (upper and lower bound, not a copying target): '+'; '.join(target_range.positive_traits),['spec.approvedTargetRange.positiveTraits'])
            emit('target.negative','Avoid drift: '+'; '.join(target_range.negative_traits),['spec.approvedTargetRange.negativeTraits'],'negative')
        emit('target.use','The approved reference establishes expression amplitude only. Do not copy exact face, clothing motifs, equipment shape, pose, cloth direction, scene placement or color layout. No canonical identity adoption.', ['spec.approvedTargetRange.referenceUse','spec.approvedTargetRange.identityAdoption'],'boundary')
    data=dump_contract(profile)
    if mode=='HERO_CASTING':
        for field, dimensions in FIELD_DIMENSIONS.items():
            value=data[field]
            words=EXAGGERATION_LANGUAGE[value] if field=='heroicExaggeration' else FIELD_LANGUAGE[field][('low','medium','high','dominant').index(value)]
            emit('expression.'+field,words,['expressionProfiles.cgExpressionProfile.'+field, *['spec.modeVisualIntents.HERO_CASTING.'+x for x in dimensions]])
    for dimension in DIMENSIONS:
        emit('intent.'+dimension,dimension+': '+intent[dimension],['spec.modeVisualIntents.'+mode+'.'+dimension])
    emit('rendering',style['rendering'],['route.style.rendering'])
    emit('materials',style['materialPalette'],['route.style.materialPalette'])
    emit('historicalBoundary',style['historicalBoundary']+' '+PHYSICAL_BOUNDARY,['route.style.historicalBoundary','expressionProfiles.cgExpressionProfile.realismBase'],'boundary')
    emit('negative','Forbidden: homogenized character appearance, copied recognizable game-IP designs, supernatural effects, physically impossible anatomy, cropped feet, text or watermark. '+ '; '.join(style['forbiddenDrifts']),['castingMode.policy','route.style.forbiddenDrifts'],'negative')
    emit('review','Unapproved candidate for user review; no automatic identity adoption.', ['castingMode.reviewPolicy'])
    conflicts=audit_hero_prompt(rows) if mode=='HERO_CASTING' else []
    if conflicts:
        raise ValueError('CONSERVATIVE_HERO_PROMPT_CONFLICT:'+str(conflicts))
    prompt='\n\n'.join(row['text'] for row in rows)
    offset=0
    for row in rows:
        row.update(start=offset,end=offset+len(row['text']),textFingerprint=sha256_canonical(row['text']))
        offset=row['end']+2
    return {**({'approvedTargetRangeFingerprint':sha256_canonical(target_range)} if target_range is not None else {}), **({'archetypeFingerprint':sha256_canonical(archetype)} if archetype is not None else {}), 'prompt':prompt,'promptFingerprint':sha256_canonical(prompt),'segments':rows,
        'heroicFieldProjection':{f:{'value':data[f],'segment':'expression.'+f,'visualDimensions':list(ds)} for f,ds in FIELD_DIMENSIONS.items()} if mode=='HERO_CASTING' else {},
        'mode':mode,'visualRoute':route,'coreFingerprint':sha256_canonical(core),'conflicts':conflicts,
        'sourceDisposition':{'expressionProfiles.cgExpressionProfile.design':'Reconciled into explicit modeVisualIntents by the art owner; not blindly concatenated with its old camera/posture prose.'}}
