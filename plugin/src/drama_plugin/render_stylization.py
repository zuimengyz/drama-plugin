"""Creative-owned CG visibility and presentation; deterministic, no provider access.

Evidence is a bounded bilingual heuristic, not proof of generated image quality.
The contract vocabulary is reusable; this composer implements characters only.
"""
import re
from typing import Any
from .contracts.visual_medium import VisualMediumIntent

COMPILER = 'render-stylization-compiler'
VERSION = '1.0.0'

VISIBLE = {
    'form': 'Large facial forms dominate first reading. Visibly authored facial planes organize cheek, jaw, brow and nose as digital sculpture; simplify incidental asymmetry while retaining authored identity and asymmetry.',
    'body': 'Designed mass hierarchy and a readable torso-to-head relationship preserve the specified body dimensions; no automatic enlargement.',
    'skin': 'Macro-to-micro hierarchy: controlled skin-tone blocks and authored roughness grouping. Microtexture stays subordinate to sculptural planes; reduce photographic randomness while keeping living variation, not plastic skin.',
    'groom': 'Groom silhouette first: controlled hair masses and designed strand clumps; selective strand detail stays subordinate to the groom masses. Preserve authored growth and length.',
    'materials': 'Material blocks read clearly: designed cloth fold hierarchy, leather grouped into readable planes, metal roughness in authored zones, intentionally clustered edge wear. Reduce micro-noise; retain historical construction and weight.',
    'shape': 'Controlled shape abstraction, clear silhouette rhythm and slightly heightened facial plane organization preserve character-specific proportions. No universal jaw, enlarged shoulders or extra muscle.',
    'rendering': 'Look-development lighting reveals sculptural planes through controlled key-to-fill hierarchy and volume/material grouping; edge separation only when useful. Use a non-photographic neutral presentation field with subtle tonal depth, not conventional studio portrait lighting.',
}
PHOTO = {
    'form': 'Digital human anatomy with sculpted facial planes resolved toward a near-photographic likeness; observed facial irregularity remains legible.',
    'body': 'Individual digital human proportions preserve the specified torso-to-head relation and physical support.',
    'skin': 'Near-photographic digital skin: fine pores, random micro-variation and high-frequency skin realism with controlled subsurface response.',
    'groom': 'Individual-strand hair realism in a digital groom: fine flyaway detail and controlled strand grouping follow the authored growth.',
    'materials': 'Physically simulated cloth, leather and metal wherever specified; photographic material noise and small wear variations reproduce credible material response and sculpted fold hierarchy.',
    'shape': 'Lifelike digital silhouette hierarchy follows individually specified anatomy without visible abstraction or generic body enhancement.',
    'rendering': 'Near-photographic digital illumination uses physically grounded CG lighting and camera-like light falloff to match human appearance within the authored composition.',
}
LIVE = {
    'form': 'Live-action human performer: individually observed face, age and achievable anatomy.',
    'body': 'Physical performer proportions and supported posture preserve the specified body mass and torso-to-head relation.',
    'skin': 'Photographed skin with natural pores, skin-tone variation and real surface microdetail under physical light.',
    'groom': 'Practical grooming with real hair strands, individual growth irregularity and the specified hair or beard length.',
    'materials': 'Practical costume of real textile, leather and armor wherever specified; photographed material response follows construction, wear and gravity.',
    'shape': 'Human silhouette comes from actual anatomy, practical costume fit and achievable stance; no digital shape abstraction.',
    'rendering': 'Photographic cinematography: motivated physical light and photographic optics retain real light falloff and visible face/body/costume.',
}


def compile_render_stylization(intent: VisualMediumIntent) -> dict[str, str]:
    if intent.visual_medium == 'LIVE_ACTION_PHOTOREAL': return dict(LIVE)
    if intent.render_stylization is None: raise ValueError('EXPLICIT_RENDER_STYLIZATION_REQUIRED')
    if intent.render_stylization == 'PHOTOREAL_DIGITAL_HUMAN': return dict(PHOTO)
    values = dict(VISIBLE)
    if intent.render_stylization == 'HEIGHTENED_FILMIC_CG':
        values['form'] += ' Stronger facial plane emphasis sharpens authored structural contrasts without changing identity.'
        values['body'] += ' Heightened mass organization emphasizes only existing contrasts; body dimensions remain source-owned.'
        values['shape'] += ' Stronger silhouette abstraction intensifies existing contour relationships; no new anatomy or equipment.'
    return values


def compile_presentation(intent: VisualMediumIntent) -> str:
    if intent.presentation_mode is None: raise ValueError('EXPLICIT_PRESENTATION_MODE_REQUIRED')
    context = 'digital look-development stage' if intent.visual_medium == 'CINEMATIC_CG' else 'live-action presentation space'
    return {
        'LOOKDEV_NEUTRAL': f'LOOKDEV_NEUTRAL: controlled {context}; readable proportions and materials, without added dramatic posing.',
        'HERO_PRESENTATION': f'HERO_PRESENTATION: foreground character readability and leading-role visual emphasis in the {context}; preserve identity, anatomy and authored pose.',
        'PERFORMANCE_PRESENTATION': f'PERFORMANCE_PRESENTATION: reveal the source-authored playable state and attention in the {context}; invent no action, expression or narrative event.',
    }[intent.presentation_mode]


def style_anchor(intent: VisualMediumIntent) -> str:
    if intent.visual_medium == 'LIVE_ACTION_PHOTOREAL':
        return 'Live-action human performer. Photographic cinematography; real skin and hair, practical costume and physical materials.'
    if intent.render_stylization is None: raise ValueError('EXPLICIT_RENDER_STYLIZATION_REQUIRED')
    return {
        'PHOTOREAL_DIGITAL_HUMAN': 'Feature-film CG character. PHOTOREAL_DIGITAL_HUMAN: a digitally constructed human targeting near-photographic appearance.',
        'VISIBLE_FILMIC_CG': 'Feature-film CG character. VISIBLE_FILMIC_CG: visibly authored digital form reads immediately as a designed cinematic character. Large forms, material groups and groom masses take priority over photographic micro-randomness.',
        'HEIGHTENED_FILMIC_CG': 'Feature-film CG character. HEIGHTENED_FILMIC_CG: visibly authored digital form with stronger sculptural contrast and silhouette abstraction, grounded in human anatomy.',
    }[intent.render_stylization]


# Each domain requires complementary positive cues. A style label alone supplies none.
VISIBLE_EVIDENCE = {
    'FORM_HIERARCHY': (r'large facial forms|大形体|面部大形', r'facial planes|面部平面'),
    'MICRODETAIL_CONTROL': (r'macro-to-micro hierarchy|宏观.*微观层级', r'microtexture stays subordinate|微纹理.*从属'),
    'GROOM_MASSING': (r'groom silhouette first|毛发轮廓优先', r'hair masses|strand clumps|发束体块'),
    'MATERIAL_GROUPING': (r'material blocks|材质分组', r'authored zones|clustered edge wear|roughness grouping|分区粗糙度'),
    'SHAPE_ABSTRACTION': (r'controlled shape abstraction|受控形体抽象', r'silhouette rhythm|轮廓节奏'),
    'LIGHTING_PRESENTATION': (r'lighting reveals sculptural planes|光照.*雕塑平面', r'key-to-fill hierarchy|主辅光层级'),
}
PHOTO_EVIDENCE = {
    'DIGITAL_HUMAN': (r'digitally constructed human|digital human anatomy',),
    'PHOTOGRAPHIC_SKIN': (r'fine pores', r'random micro-variation'),
    'INDIVIDUAL_GROOM': (r'individual-strand hair realism',),
    'PHYSICAL_MATERIAL': (r'photographic material noise',),
    'PHOTO_LIGHTING': (r'near-photographic digital illumination',),
}
PULL_PATTERNS = {
    'PHOTOGRAPHIC_PORE_EMPHASIS': r'fine pores|sculpted pore detail|photographic pore emphasis|hyperreal skin capture|高密度毛孔|摄影级毛孔',
    'INDIVIDUAL_STRAND_PRIORITY': r'individual.strand hair realism|every individual hair|individual hair realism|逐根.*写实',
    'CAMERA_STUDIO': r'studio portrait lighting|wardrobe.test|camera-like light|摄影棚.*光|定妆照',
    'MICRO_NOISE_PRIORITY': r'random micro-variation|high-frequency skin realism|photographic material noise|incidental physical noise priority|随机.*微细节',
}


def render_stylization_gate(intent: VisualMediumIntent, prompt: str, *, medium_status: str | None = None) -> dict[str, Any]:
    from .visual_medium import positive_matches, medium_consistency_gate
    if medium_status is None:
        medium_status = medium_consistency_gate(intent, prompt)['status']
    target = intent.render_stylization
    if intent.visual_medium != 'CINEMATIC_CG' or target is None:
        return dict(mediumStatus=medium_status, renderStylizationStatus='NOT_APPLICABLE' if intent.visual_medium != 'CINEMATIC_CG' else 'LEGACY_UNSPECIFIED', target=target, positiveEvidence={}, photorealPullEvidence={}, missingDomains=[], blocking=False, heuristicVersion=VERSION)
    patterns = PHOTO_EVIDENCE if target == 'PHOTOREAL_DIGITAL_HUMAN' else VISIBLE_EVIDENCE
    evidence = {domain: [positive_matches(prompt, re.compile(p, re.I)) for p in parts] for domain, parts in patterns.items()}
    missing = [domain for domain, matches in evidence.items() if not all(matches)]
    if target == 'HEIGHTENED_FILMIC_CG':
        evidence['HEIGHTENED_CONTRAST'] = [positive_matches(prompt, re.compile(p,re.I)) for p in (r'stronger facial plane emphasis',r'stronger silhouette abstraction')]
        if not all(evidence['HEIGHTENED_CONTRAST']): missing.append('HEIGHTENED_CONTRAST')
    pull = {key: matches for key, pattern in PULL_PATTERNS.items() if (matches := positive_matches(prompt,re.compile(pattern,re.I)))}
    # Style declarations are bound too; a photo contract cannot quietly emit the
    # visible/heightened recipe, nor can a visible contract declare photo priority.
    declarations = positive_matches(prompt, re.compile(r'\b(?:PHOTOREAL_DIGITAL_HUMAN|VISIBLE_FILMIC_CG|HEIGHTENED_FILMIC_CG)\b'))
    conflicts = [d for d in declarations if d != target]
    rejected = re.compile(r'(?:\b(?:avoid|no|not|never use|do not use)\s+|禁止|不要|避免)' + re.escape(target),re.I)
    conflicts += [m.group() for m in rejected.finditer(prompt)]
    if target == 'PHOTOREAL_DIGITAL_HUMAN':
        conflicts += positive_matches(prompt,re.compile(r'microtexture stays subordinate|controlled shape abstraction',re.I))
    fail = bool(missing or conflicts or (pull and target != 'PHOTOREAL_DIGITAL_HUMAN'))
    return dict(mediumStatus=medium_status, renderStylizationStatus='FAIL' if fail else 'PASS', target=target,
        positiveEvidence=evidence, photorealPullEvidence=pull, missingDomains=missing, conflicts=conflicts,
        detectedPull='PHOTOREAL_DIGITAL_HUMAN' if pull else None,
        verdict='FAIL_RENDER_STYLIZATION' if fail else 'PASS', blocking=fail, heuristicVersion=VERSION)


def compose_domains(intent: VisualMediumIntent, facts: list[dict[str, Any]], *, compiler: str, version: str,
                    treatment: str, realism: str, casting: str) -> list[dict[str, Any]]:
    """One policy per visual domain; exact fact spans remain separately replayable."""
    policies = compile_render_stylization(intent)
    groups: dict[str, list[dict[str, Any]]] = {d: [] for d in (*policies, 'constraint')}
    for fact in facts:
        d = fact['domain']
        if d == 'form' and re.search(r'body|mass|shoulder|height', fact.get('topic','')+' '+fact['id'],re.I): d='body'
        groups[d].append(fact)
    rows = []
    def emit(key: str, text: str, domain_facts: list[dict[str, Any]]) -> None:
        row = dict(id='compiled.'+key, kind='visual',text=text,sources=['control-plane.visualMediumIntent', *dict.fromkeys(s for f in domain_facts for s in f.get('sources',[]))],sourceLayer='compiled_control_plane',sourceLayers=['compiled_control_plane'],topic=key,compiledBy=compiler,compilerVersion=version,renderStylization=intent.render_stylization,renderStylizationSource=intent.render_stylization_source,renderStylizationCompiler=COMPILER,renderStylizationVersion=VERSION)
        for f in domain_facts:
            f['outputSection']=row['id'];f['sectionRelativeStart']=len(row['text'])+1
            row['text']+='\n'+f['text']
            f['sectionRelativeEnd']=len(row['text'])
        rows.append(row)
    emit('medium.anchor',style_anchor(intent),[])
    for domain in ('form','body','skin','groom','materials','shape','rendering'):
        text=policies[domain]
        if domain=='rendering': text+=' '+compile_presentation(intent)
        emit('medium.'+domain,text,groups[domain])
    emit('treatment',treatment+' '+casting,[])
    emit('realism',realism,[])
    if groups['constraint']:
        emit('constraints','CG production character boundary.' if intent.visual_medium=='CINEMATIC_CG' else 'Live-action production boundary.',groups['constraint'])
    return rows
