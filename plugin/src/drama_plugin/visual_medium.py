"""Deterministic medium compilation, semantic checks and replayable source receipts.

No host, character identity, model, provider or media production dependencies.
The gate is a bounded bilingual heuristic, not a general natural-language reasoner.
"""
from copy import deepcopy
import re
from typing import Any
from .contracts.base import dump_contract, sha256_canonical
from .contracts.character_prompt import StructuredCharacterFacts, CharacterPromptFact
from .contracts.visual_medium import VisualMediumIntent, legacy_medium_intent, medium_route

COMPILER = 'visual-medium-compiler'
VERSION = '3.0.0'


def compile_visual_medium(intent: VisualMediumIntent) -> dict[str, str]:
    if intent.render_stylization is not None or intent.presentation_mode is not None:
        from .render_stylization import compile_render_stylization
        return compile_render_stylization(intent)
    if intent.visual_medium == 'CINEMATIC_CG':
        return {
            'form': 'Digital sculptural form: sculpted facial planes organize the authored face, jaw and brow; shoulder and torso planes articulate the specified anatomy. Preserve ordinary adult proportions when authored; refine volume transitions without imposing a universal heroic body.',
            'skin': 'Cinematic digital skin shading: controlled subsurface response, authored skin roughness and sculpted pore detail; deliberate highlight response follows facial planes. Keep skin supple and varied; avoid plastic, wax or figurine surfaces.',
            'groom': 'Digitally groomed hair and beard, including natural stubble when specified: controlled strand grouping and authored groom silhouette preserve the authored hair length and beard density. Do not add hair or beard absent from character facts.',
            'materials': 'Authored CG material treatment: controlled surface roughness, sculpted fold hierarchy, designed edge wear and deliberate material separation. Cloth, leather and metal retain their physical responses wherever present; preserve historically credible construction and functional joints.',
            'shape': 'Shape design: silhouette hierarchy, facial plane emphasis, proportion refinement and mass distribution make the authored geometry readable. Preserve exact authored anatomical relationships; do not invent larger shoulders, armor or weapons.',
            'rendering': 'Feature-film CG character presentation: cinematic digital character rendering with physically grounded CG lighting; a digital production character whose authored surfaces, groom and sculptural volumes remain visible under the specified composition.',
        }
    return {
        'form': 'Real human actor with achievable anatomy and individually observed face, jaw, brow, shoulders and torso; preserve the authored proportions and performable posture.',
        'skin': 'Photographed skin with real facial microdetail, natural pore variation and living skin response under practical light; retain minor irregularities without cosmetic smoothing.',
        'groom': 'Practical hair and beard, including natural stubble when specified: individual real strands and naturally irregular growth retain the authored length and density.',
        'materials': 'Practical costume and historically credible wearable equipment: photographed cloth weave, leather creases and metal reflections arise from actual construction, wear and lighting.',
        'shape': 'Human silhouette and mass distribution come from the specified actor anatomy, achievable stance and practical costume fit; role emphasis preserves performable proportions.',
        'rendering': 'Live-action cinematography: photographic optics, motivated camera perspective and real light falloff present a photographed human performer in the authored environment.',
    }


def compile_character_treatment(intent: VisualMediumIntent) -> str:
    return {
        'NATURAL': 'NATURAL treatment: retain individual asymmetry and ordinary authored proportions; no automatic enlargement or heroic massing.',
        'HEROIC': 'HEROIC treatment: emphasize authored proportion, silhouette and character-specific screen presence through readable face-to-body hierarchy, without changing authored mass. Stay within the medium and realism limits; invent no rank, weapon, fixed expression or body type.',
        'MYTHIC': 'MYTHIC treatment: heighten the authored silhouette and symbolic presence within the medium and realism limits; add no supernatural effects, new equipment or narrative facts.',
    }[intent.character_treatment]


def compile_realism_level(intent: VisualMediumIntent) -> str:
    return {
        'NATURALISTIC': 'NATURALISTIC realism: retain real human proportions, articulating anatomy, gravity and physical material behavior; no anatomical exaggeration.',
        'GROUNDED_STYLIZED': 'GROUNDED_STYLIZED realism: retain credible human anatomy, weight, gravity, joint mechanics and historically functional construction. Rendering visibility is controlled independently; non-anime, non-cartoon, no impossible anatomy.',
        'HEIGHTENED': 'HEIGHTENED realism: accentuate only authored structural contrasts while preserving support, articulating joints and functional historical equipment; do not invent fantasy armor or impossible anatomy.',
    }[intent.realism_level]


def compile_casting_mode(intent: VisualMediumIntent) -> str:
    return {
        'HERO_CASTING': 'HERO_CASTING: test leading-role presence, specific identity and expressive readability; no automatic medium, pose, lens or costume change.',
        'SUPPORTING_CASTING': 'SUPPORTING_CASTING: test distinctive supporting-role identity and readable reactions within the authored composition.',
        'DESIGN_NEUTRAL': 'DESIGN_NEUTRAL: assess identity and proportions without added leading-role emphasis; presentation and medium remain independently specified.',
    }[intent.casting_mode]


def generated_sections(intent: VisualMediumIntent) -> list[dict[str, Any]]:
    constraints = compile_visual_medium(intent)
    values = {**{'medium.' + k: v for k, v in constraints.items()},
              'treatment': compile_character_treatment(intent), 'realism': compile_realism_level(intent),
              'casting': compile_casting_mode(intent)}
    return [dict(id='compiled.' + k, kind='visual', text=v, sources=['control-plane.visualMediumIntent'],
                 sourceLayer='compiled_control_plane', sourceLayers=['compiled_control_plane'],
                 topic='visual_medium' if k.startswith('medium.') else k, compiledBy=COMPILER, compilerVersion=VERSION)
            for k, v in values.items()]


# Specific rendering/production assertions, not generic realism, pores or neutral backgrounds.
LIVE = re.compile(r'\b(?:real(?:istic)? (?:human )?actor|live[- ]action(?: actor| cinematography| photography)?|studio (?:photography|photo|portrait)|costume (?:fitting|test) (?:photo(?:graphy)?|photograph)|cosplay photography|photographic portrait|portrait photography|shot on camera|real person casting photo|photographed (?:human|skin)|photographic optics)\b|真人演员|真人(?:摄影|定妆照|照片)|摄影棚定妆照片|真实演员试装摄影|演员定妆照|实拍人物', re.I)
CG = re.compile(r'\b(?:digital(?:ly)? (?:sculpt\w*|skin|character|production character|groom\w*)|CG skin shader|3D groom|feature[- ]film (?:digital|CG) character|cinematic (?:digital|CG)|CG character|3D character|CG material)\b|数字(?:雕刻|角色|皮肤|毛发)|CG(?:角色|人物|材质|渲染)|三维角色', re.I)
# Matching declarations are forbidden in *new* Host prose too; legacy matching
# declarations survive as explicitly labelled conflict input, never compiler proof.
DECLARATION = re.compile(r'\b(?:VISIBLE_FILMIC_CG|PHOTOREAL_DIGITAL_HUMAN|HEIGHTENED_FILMIC_CG|LOOKDEV_NEUTRAL|HERO_PRESENTATION|PERFORMANCE_PRESENTATION|CG|3D|live[- ]action|photoreal(?:istic)?|studio portrait)\b|真人摄影|三维角色', re.I)
NEGATION = re.compile(r'\b(?:avoid(?:ing)?|not|never|no|without|exclude|forbidden|do not|rather than|instead of)\b|避免|不要|禁止|禁项|不得|排除|并非|不是|非真人', re.I)
REASSERTION = re.compile(r'\b(?:but|however|yet|instead use|use|show|depict|render as)\b|但是|但要|改用|呈现为|使用', re.I)


def positive_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Clause-local negation; commas retain list scope, affirmative transitions reset it.

    Section labels never exempt the rest of a row. E.g. a negative section
    containing 'Avoid cosplay photography. Use real actor' still fails.
    """
    matches = []
    for clause in re.split(r'[.!?。！？;；\n]+|\b(?:but|however|yet)\b|但是|但要', text, flags=re.I):
        for match in pattern.finditer(clause):
            prefix = clause[:match.start()]
            # 'not only' is additive, not negative.
            prefix = re.sub(r'\bnot only\b|不仅', '', prefix, flags=re.I)
            negatives = list(NEGATION.finditer(prefix))
            resets = [r for r in REASSERTION.finditer(prefix)
                      if not re.search(r'(?:do not|never|not|不要|禁止)\s*$', prefix[:r.start()], re.I)]
            if not negatives or (resets and resets[-1].start() > negatives[-1].start()):
                matches.append(match.group())
    return matches


# Surface-label removal leaves these executable cues. Evidence must be positive,
# span distinct domains and survive removal of CG/3D/digital/render labels.
EVIDENCE = {
    'form': r'sculpted facial planes|large facial forms|雕刻面部平面',
    'skin': r'controlled subsurface response|authored skin roughness|macro-to-micro hierarchy|受控次表面',
    'groom': r'controlled strand grouping|authored groom silhouette|groom silhouette first|受控发束',
    'materials': r'sculpted fold hierarchy|designed edge wear|material blocks|雕刻褶皱层级',
    'shape': r'silhouette hierarchy|proportion refinement|controlled shape abstraction|轮廓层级',
    'rendering': r'feature[- ]film\s+character presentation|physically grounded\s+lighting|lighting reveals sculptural planes|电影级角色呈现',
}


def medium_consistency_gate(intent: VisualMediumIntent, prompt: str) -> dict[str, Any]:
    intent = VisualMediumIntent.model_validate(dump_contract(intent))
    conflicts = positive_matches(prompt, LIVE if intent.visual_medium == 'CINEMATIC_CG' else CG)
    # A negative exclusion of the *other* medium is fine; an explicit rejection
    # of the selected medium is another way for Host prose to override control.
    target = (r'(?:cinematic\s+CG|CG|3D(?: character)?|digital character|digital sculpt|digitally groomed hair|数字角色|三维角色)'
              if intent.visual_medium == 'CINEMATIC_CG' else
              r'(?:live[- ]action|real (?:human )?actor|photoreal(?:ism|istic)?|photographed skin|真人(?:摄影|演员))')
    rejection = re.compile(r'(?:\b(?:avoid|do not use|never use|no|not|without)\s+(?:a |an |the )?|禁止|不要|避免|不是)\s*' + target + r'(?![a-z])', re.I)
    conflicts += [m.group() for m in rejection.finditer(prompt)]
    missing: list[str] = []
    evidence: dict[str, bool] = {}
    if intent.visual_medium == 'CINEMATIC_CG':
        stripped = re.sub(r'\b(?:CG|3D|digitally|digital|render\w*)\b', '', prompt, flags=re.I)
        evidence = {key: bool(positive_matches(stripped, re.compile(pattern, re.I))) for key, pattern in EVIDENCE.items()}
        missing = [key for key, present in evidence.items() if not present]
    # Positive evidence must govern the facts, not occur only in an appendix.
    # Inspect paragraph boundaries as well as vocabulary. This intentionally
    # blocks legacy naked facts even when all six generic paragraphs are present.
    unbound = []
    photographic_pull = []
    anchor = True
    if intent.visual_medium == 'CINEMATIC_CG':
        anchor = bool(re.match(r'Feature-film CG character\.', prompt, re.I))
        bound = re.compile(r'authored digital production character|sculpted facial planes|authored facial plane organization|controlled subsurface response|authored skin-tone variation|controlled strand grouping|authored strand grouping|sculpted fold hierarchy|authored material separation|silhouette hierarchy|controlled proportion refinement|physically grounded (?:CG|digital) lighting|neutral treatment within feature-film CG look-development|CG production character boundary|authored digital sculptural anatomy|authored CG surface variation|authored digital groom structure|authored CG material construction|designed CG silhouette structure|CG look-development composition|NATURAL treatment|HEROIC treatment|MYTHIC treatment|NATURALISTIC realism|GROUNDED_STYLIZED realism|HEIGHTENED realism|HERO_CASTING|SUPPORTING_CASTING|DESIGN_NEUTRAL|visibly authored|digitally constructed human|digital human anatomy|designed mass hierarchy|digital human proportions|near-photographic digital skin|individual-strand hair realism|physically simulated cloth|lifelike digital silhouette|look-development lighting|large facial forms|macro-to-micro hierarchy|groom silhouette first|material blocks|controlled shape abstraction', re.I)
        for index, paragraph in enumerate(re.split(r'\n\s*\n', prompt.strip())):
            if paragraph.strip() and not positive_matches(paragraph, bound) and not NEGATION.match(paragraph.strip()):
                unbound.append(index)
        if not anchor: missing.append('mediumAnchor')
        if unbound: missing.append('mediumBoundFactSections')
        # Skin/wardrobe wording cannot be redeemed by a CG label on the same row.
        pull = re.compile(r'natural skin texture|realistic pores|photographic skin detail|studio-like presentation|wardrobe[- ]test|casting (?:still|photo)|棚拍|定妆照', re.I)
        photographic_pull = positive_matches(prompt, pull) if intent.render_stylization != 'PHOTOREAL_DIGITAL_HUMAN' else []
    status = 'FAIL' if conflicts or photographic_pull else 'WARN' if missing else 'PASS'
    return dict(status=status, visualMedium=intent.visual_medium, conflicts=conflicts,
                missingEvidence=missing, labelStrippedEvidence=evidence,
                actorPhotoExplainability='WEAK_MEDIUM' if missing else 'MEDIUM_SPECIFIC' if evidence else 'NOT_APPLICABLE',
                heuristicVersion=VERSION, mediumAnchor=anchor, unboundFactParagraphs=unbound,
                mediumBalanceStatus=status, photographicAffordances=photographic_pull, blocking=status != 'PASS')


# Domain transforms apply to each source fact, including composition. No character
# identity, provider or inferred role can select a transform.
ANCHORS = {
    'CINEMATIC_CG': 'Feature-film CG character. Non-photographic digital character render; an authored digital production character. All following identity, surface and presentation choices belong to this medium.',
    'LIVE_ACTION_PHOTOREAL': 'Live-action human performer. Photographic cinematography with real skin and hair, practical costume and physical materials. All following identity, surface and presentation choices belong to this medium.',
}
TRANSLATIONS = {
    'CINEMATIC_CG': {
        'form': 'Digital sculptural construction with authored facial plane organization; preserve the specified anatomy and age exactly',
        'skin': 'CG skin: authored skin-tone variation and digitally sculpted surface detail, controlled CG skin roughness and designed subsurface response; preserve the specified irregularity',
        'groom': 'Digital groom: authored strand grouping and controlled groom silhouette; preserve the specified growth, length and density',
        'materials': 'CG materials: authored material separation, controlled roughness hierarchy, digitally sculpted cloth folds, designed leather response and CG metal surface treatment wherever those materials are specified; preserve historical construction',
        'shape': 'CG shape design: designed silhouette and controlled proportion refinement express the specified contour without changing body dimensions',
        'rendering': 'Feature-film CG look-development presentation with physically grounded digital lighting; implement this composition and performance intent as a digital character design presentation',
        'constraint': 'CG production character boundary; retain this source constraint',
    },
    'LIVE_ACTION_PHOTOREAL': {
        'form': 'Live-action human performer with individually observed face and performable anatomy; preserve the specified anatomy and age exactly',
        'skin': 'Photographic skin: real skin texture, natural pore variation and photographed skin-tone variation under physical light; preserve the specified irregularity',
        'groom': 'Live-action practical grooming: real hair strands and natural growth irregularity; preserve the specified growth, length and density',
        'materials': 'Live-action practical costume: real textile, leather and lamellar armor wherever specified, photographed material response under live-action lighting; preserve historical construction',
        'shape': 'Live-action silhouette: physical body proportions and practical costume fit express the specified contour without changing body dimensions',
        'rendering': 'Live-action character presentation with photographic optics and physical lighting; implement this composition and performance intent using a human performer',
        'constraint': 'Live-action production boundary; retain this source constraint',
    },
}
DERIVED = {'dominant_visual_traits', 'secondary_traits', 'camera_readable_features'}
SHORT_TRANSLATIONS = {
    'CINEMATIC_CG': dict(form='Authored digital sculptural anatomy', skin='Authored CG surface variation',
        groom='Authored digital groom structure', materials='Authored CG material construction',
        shape='Designed CG silhouette structure', rendering='CG look-development composition',
        constraint='CG production character boundary'),
    'LIVE_ACTION_PHOTOREAL': dict(form='Live-action performer anatomy', skin='Photographed real skin variation',
        groom='Practical real hair grooming', materials='Photographed practical costume construction',
        shape='Physical performer silhouette', rendering='Photographic live-action composition',
        constraint='Live-action production boundary'),
}


def fact_domain(row: dict[str, Any]) -> str:
    """Explicit domains win; old paragraph APIs use a documented lexical adapter."""
    if 'domain' in row:
        return CharacterPromptFact.model_validate({k: row[k] for k in ('id', 'domain', 'text')}).domain
    key = (row.get('topic', '') + ' ' + row['id']).lower()
    if row.get('kind') in ('negative', 'boundary') or re.search(r'anti.drift|forbidden|negative|boundary|avoid', key):
        return 'constraint'
    for domain, pattern in (
        ('skin', r'skin|肤'), ('groom', r'hair|beard|groom|发|须'),
        ('materials', r'cost[.-]|costume|cloth|armor|material|wardrobe|layer|wear|甲|服'),
        ('rendering', r'framing|composition|camera|scope|presence|pose|posture|lighting|rendering|background|mode|review'),
        ('shape', r'silhouette|shape'),
    ):
        if re.search(pattern, key): return domain
    # Untyped legacy prose is not the authoring contract. Classify its observable
    # content while retaining every source byte in the replay receipt.
    for domain, pattern in (
        ('skin', r'肤|skin'), ('groom', r'发式|胡须|hair|beard'),
        ('materials', r'服装|甲|衣物|costume|leather|cloth'),
        ('rendering', r'构图|背景|摄影|朝向|full body|framing|camera|lighting'),
    ):
        if re.search(pattern, row['text'], re.I): return domain
    return 'form'


def _neutral_wording(text: str, domain: str, medium: str) -> str:
    # Lexical rendering changes no anatomical facts. Original text stays in receipt.
    if medium == 'CINEMATIC_CG':
        substitutions = {
            r'natural skin texture': 'authored skin surface variation',
            r'realistic pores': 'sculpted surface microstructure',
            r'photographic skin detail': 'authored skin surface detail',
            r'自然纹理': '表面纹理起伏',
            r'统一摄影': '统一构图意图',
            r'inspection plate': 'look-development presentation',
        }
        for pattern, replacement in substitutions.items():
            text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def _key(text: str) -> str:
    return re.sub(r'[\s。.!！;；]+', '', text).casefold()


def compile_character_art(intent: VisualMediumIntent, sections: list[dict[str, Any]] | StructuredCharacterFacts, *,
                          legacy: bool = False, source_intent: str = 'control-plane') -> dict[str, Any]:
    intent = VisualMediumIntent.model_validate(dump_contract(intent))
    if isinstance(sections, StructuredCharacterFacts):
        sections = [dump_contract(f) for f in sections.facts]
    originals = deepcopy(sections)
    if not source_intent.strip(): raise ValueError('MEDIUM_SOURCE_INTENT_REQUIRED')
    if len({r['id'] for r in originals}) != len(originals) or any(r['id'].startswith('compiled.') for r in originals):
        raise ValueError('DUPLICATE_OR_RESERVED_PROMPT_SECTION')
    prepared = []
    for source in originals:
        row = deepcopy(source)
        if not isinstance(row.get('text'), str) or not row['text'].strip():
            raise ValueError('CHARACTER_FACT_TEXT_REQUIRED')
        row.pop('compiledBy', None); row.pop('compilerVersion', None)
        if row.get('sourceLayer') == 'compiled_control_plane': row['sourceLayer'] = 'host_authored'
        check = medium_consistency_gate(intent, row['text'])
        if check['conflicts']:
            raise ValueError('MEDIUM_CONSISTENCY_FAIL:' + str(check['conflicts']))
        modes = positive_matches(row['text'], re.compile(r'\b(?:HERO_CASTING|DESIGN_NEUTRAL|SUPPORTING_CASTING)\b'))
        if any(mode != intent.casting_mode for mode in modes):
            raise ValueError('MEDIUM_CASTING_MODE_AUTHORITY_CONFLICT')
        if not legacy and any(positive_matches(row['text'], pattern) for pattern in (DECLARATION, LIVE, CG)):
            raise ValueError('HOST_MEDIUM_DECLARATION_FORBIDDEN: use visualMediumIntent')
        row['domain'] = fact_domain(row)
        row['mediumAuthority'] = 'LEGACY_CONFLICT_INPUT' if legacy else 'CHARACTER_FACTS_ONLY'
        prepared.append(row)
    # Base facts own weight. Derived summaries may retain only previously unspoken
    # clauses; duplicate source references remain in the audit, not provider text.
    prepared.sort(key=lambda r: bool(r.get('derivedSummary') or r.get('topic') in DERIVED or r['id'].split('.')[-1] in DERIVED))
    seen: dict[str, str] = {}
    dedup = []
    transformed = []
    translated_domains: set[str] = set()
    for row in prepared:
        unique = []
        for atom in re.split(r'[；;\n]+', row['text']):
            key = _key(atom)
            if not key: continue
            if key in seen:
                dedup.append(dict(sourceSection=row['id'], fact=atom, retainedBy=seen[key], reason='EXACT_NORMALIZED_FACT'))
            else:
                seen[key] = row['id']; unique.append(atom.strip())
        if not unique: continue
        fact_text = '；'.join(unique)
        domain = row['domain']
        row.update(sourceFactText=fact_text, mediumTransform=intent.visual_medium + '_' + domain.upper() + '_TRANSFORM',
                   transformedBy=COMPILER, transformVersion=VERSION)
        # Explain the operation once per domain; subsequent facts retain a native
        # semantic label without repeating a full shader/anatomy policy each time.
        grammar = SHORT_TRANSLATIONS if domain in translated_domains or row.get('sourceLayer') == 'generic_capability' else TRANSLATIONS
        row['text'] = grammar[intent.visual_medium][domain] + ': ' + _neutral_wording(fact_text, domain, intent.visual_medium)
        translated_domains.add(domain)
        if intent.render_stylization is not None or intent.presentation_mode is not None:
            row['text'] = _neutral_wording(fact_text, domain, intent.visual_medium)
            row.update(renderStylization=intent.render_stylization, renderStylizationSource=intent.render_stylization_source,
                       renderStylizationCompiler='render-stylization-compiler',renderStylizationVersion='1.0.0')
        transformed.append(row)
    emitted = generated_sections(intent)
    anchor = dict(id='compiled.medium.anchor', kind='visual', text=ANCHORS[intent.visual_medium],
                  sources=['control-plane.visualMediumIntent'], sourceLayer='compiled_control_plane',
                  sourceLayers=['compiled_control_plane'], topic='visual_medium', compiledBy=COMPILER, compilerVersion=VERSION)
    rows = [anchor]
    # Six domain policies lead their translated facts. Never append a medium
    # paragraph to a naked character description. Empty domains invent no facts.
    for domain in ('form', 'skin', 'groom', 'materials', 'shape', 'rendering'):
        rows.append(next(r for r in emitted if r['id'] == 'compiled.medium.' + domain))
        rows.extend(r for r in transformed if r['domain'] == domain)
    rows.extend(r for r in emitted if not r['id'].startswith('compiled.medium.'))
    rows.extend(r for r in transformed if r['domain'] == 'constraint')
    compact = intent.render_stylization is not None or intent.presentation_mode is not None
    if compact:
        from .render_stylization import compose_domains
        rows = compose_domains(intent, transformed, compiler=COMPILER, version=VERSION,
            treatment=compile_character_treatment(intent), realism=compile_realism_level(intent), casting=compile_casting_mode(intent))
        anchor = rows[0]
    offset = 0
    for row in rows:
        row.update(start=offset, end=offset + len(row['text']), textFingerprint=sha256_canonical(row['text']))
        offset = row['end'] + 2
    if compact:
        section_starts = {r['id']: r['start'] for r in rows}
        for fact in transformed:
            fact['start'] = section_starts[fact['outputSection']] + fact['sectionRelativeStart']
            fact['end'] = section_starts[fact['outputSection']] + fact['sectionRelativeEnd']
            fact['textFingerprint'] = sha256_canonical(fact['text'])
    prompt = '\n\n'.join(row['text'] for row in rows)
    gate = medium_consistency_gate(intent, prompt)
    if gate['status'] != 'PASS': raise ValueError('MEDIUM_CONSISTENCY_' + gate['status'] + ':' + str(gate))
    from .render_stylization import render_stylization_gate
    style_gate = render_stylization_gate(intent, prompt, medium_status=gate['status'])
    if style_gate['blocking']: raise ValueError('FAIL_RENDER_STYLIZATION:' + str(style_gate))
    receipt = dict(renderStylization=intent.render_stylization, renderStylizationSource=intent.render_stylization_source,
                   renderStylizationCompiler='render-stylization-compiler', renderStylizationVersion='1.0.0',
                   renderStylizationEvidence=style_gate, presentationMode=intent.presentation_mode,
                   migrationStatus='EXPLICIT_STYLE_REVISION' if intent.render_stylization else 'LIVE_ACTION' if intent.visual_medium=='LIVE_ACTION_PHOTOREAL' else 'LEGACY_GENERIC_CG_UNSPECIFIED',
                   visualMedium=intent.visual_medium, characterTreatment=intent.character_treatment,
                   realismLevel=intent.realism_level, castingMode=intent.casting_mode,
                   compiler=COMPILER, compiledBy=COMPILER, compilerVersion=VERSION,
                   source='control-plane', sourceIntent=source_intent, intent=dump_contract(intent),
                   inputSections=originals, legacy=legacy,
                   compiledMediumConstraints=compile_visual_medium(intent),
                   generatedSections=[deepcopy(r) for r in rows if r['id'].startswith('compiled.')],
                   mediumAnchor=deepcopy(anchor), translatedFactSections=deepcopy(transformed),
                   generatedMediumSections=[r['id'] for r in rows if r['id'].startswith('compiled.medium.')],
                   deduplicatedFacts=dedup, negativeGuards=[r['id'] for r in transformed if r['domain']=='constraint'],
                   mediumBalanceStatus=gate['status'], gateStatus=gate['status'], promptFingerprint=sha256_canonical(prompt))
    return dict(prompt=prompt, promptFingerprint=sha256_canonical(prompt), segments=rows,
                visualMediumIntent=dump_contract(intent), visualMediumCompilation=receipt, mediumGate=gate, renderStylizationGate=style_gate)


def verify_medium_compilation(brief: dict[str, Any]) -> None:
    """Replay facts, transforms, deduplication and every source span, not just boilerplate.

    Reproducibility is not a signature or permission to spend. Old receipts fail
    closed and require explicit recompilation and fresh authorization downstream.
    """
    try:
        intent = VisualMediumIntent.model_validate(brief['visualMediumIntent'])
        receipt = brief['visualMediumCompilation']
        expected = compile_character_art(intent, receipt['inputSections'], legacy=receipt['legacy'], source_intent=receipt['sourceIntent'])
        for key in expected:
            if brief[key] != expected[key]: raise ValueError('MEDIUM_COMPILATION_PROOF_MISMATCH:' + key)
        if 'visualRoute' in brief and brief['visualRoute'] != medium_route(intent):
            raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
        if 'visualLanguage' in brief and legacy_medium_intent(brief['visualLanguage']).visual_medium != intent.visual_medium:
            raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
        for key in ('visualMedium', 'castingMode', 'renderStylization', 'presentationMode'):
            if key in brief and brief[key] != dump_contract(intent)[key]: raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
    except (KeyError, TypeError) as exc:
        raise ValueError('MEDIUM_COMPILATION_PROOF_REQUIRED') from exc
