"""Deterministic medium compilation, semantic checks and replayable source receipts.

No host, character identity, model, provider or media production dependencies.
The gate is a bounded bilingual heuristic, not a general natural-language reasoner.
"""
from copy import deepcopy
import re
from typing import Any
from .contracts.base import dump_contract, sha256_canonical
from .contracts.visual_medium import VisualMediumIntent, legacy_medium_intent, medium_route

COMPILER = 'visual-medium-compiler'
VERSION = '1.0.0'


def compile_visual_medium(intent: VisualMediumIntent) -> dict[str, str]:
    if intent.visual_medium == 'CINEMATIC_CG':
        return {
            'form': 'Digital sculptural form: sculpted facial planes organize the authored face, jaw and brow; shoulder and torso planes articulate the specified anatomy. Preserve ordinary adult proportions when authored; refine volume transitions without imposing a universal heroic body.',
            'skin': 'Cinematic digital skin shading: controlled subsurface response, authored skin roughness and sculpted pore detail; deliberate highlight response follows facial planes. Keep skin supple and varied; avoid plastic, wax or figurine surfaces.',
            'groom': 'Digitally groomed hair and beard, including natural stubble when specified: controlled strand grouping and authored groom silhouette preserve the authored hair length and beard density. Do not add hair or beard absent from character facts.',
            'materials': 'Authored CG material treatment: controlled surface roughness, sculpted fold hierarchy, designed edge wear and deliberate material separation. Cloth, leather and metal retain their physical responses wherever present; preserve historically credible construction and functional joints.',
            'shape': 'Shape design: silhouette hierarchy, facial plane emphasis, proportion refinement and mass distribution make the authored geometry readable. Controlled anatomical exaggeration stays within the selected realism and character treatment; do not invent larger shoulders, armor or weapons.',
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
        'HEROIC': 'HEROIC treatment: emphasize authored proportion, silhouette and character-specific screen presence through deliberate heroic massing and readable face-to-body hierarchy. Stay within the medium and realism limits; invent no rank, weapon, fixed expression or body type.',
        'MYTHIC': 'MYTHIC treatment: heighten the authored silhouette and symbolic presence within the medium and realism limits; add no supernatural effects, new equipment or narrative facts.',
    }[intent.character_treatment]


def compile_realism_level(intent: VisualMediumIntent) -> str:
    return {
        'NATURALISTIC': 'NATURALISTIC realism: retain real human proportions, articulating anatomy, gravity and physical material behavior; no anatomical exaggeration.',
        'GROUNDED_STYLIZED': 'GROUNDED_STYLIZED realism: retain human anatomy, weight and historically credible equipment while refining authored forms, silhouette and material hierarchy. Permit controlled emphasis within plausible joint mechanics; non-cartoon, non-anime, without exaggerated game-cutscene anatomy.',
        'HEIGHTENED': 'HEIGHTENED realism: accentuate only authored structural contrasts while preserving support, articulating joints and functional historical equipment; do not invent fantasy armor or impossible anatomy.',
    }[intent.realism_level]


def compile_casting_mode(intent: VisualMediumIntent) -> str:
    return {
        'HERO_CASTING': 'HERO_CASTING: test leading-role presence, specific identity and expressive readability; no automatic medium, pose, lens or costume change.',
        'SUPPORTING_CASTING': 'SUPPORTING_CASTING: test distinctive supporting-role identity and readable reactions within the authored composition.',
        'DESIGN_NEUTRAL': 'DESIGN_NEUTRAL: inspect proportion and costume with even visibility; no automatic hero staging.',
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
DECLARATION = re.compile(r'\b(?:CG|3D|live[- ]action|photoreal(?:istic)?|studio portrait)\b|真人摄影|三维角色', re.I)
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
    'form': r'sculpted facial planes|雕刻面部平面',
    'skin': r'controlled subsurface response|authored skin roughness|受控次表面',
    'groom': r'controlled strand grouping|authored groom silhouette|受控发束',
    'materials': r'sculpted fold hierarchy|designed edge wear|雕刻褶皱层级',
    'shape': r'silhouette hierarchy|proportion refinement|轮廓层级',
    'rendering': r'feature[- ]film\s+character presentation|physically grounded\s+lighting|电影级角色呈现',
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
    status = 'FAIL' if conflicts else 'WARN' if missing else 'PASS'
    return dict(status=status, visualMedium=intent.visual_medium, conflicts=conflicts,
                missingEvidence=missing, labelStrippedEvidence=evidence,
                actorPhotoExplainability='WEAK_MEDIUM' if missing else 'MEDIUM_SPECIFIC' if evidence else 'NOT_APPLICABLE',
                heuristicVersion=VERSION)


def compile_character_art(intent: VisualMediumIntent, sections: list[dict[str, Any]], *,
                          legacy: bool = False, source_intent: str = 'control-plane') -> dict[str, Any]:
    intent = VisualMediumIntent.model_validate(dump_contract(intent))
    rows = deepcopy(sections)
    if len({r['id'] for r in rows}) != len(rows) or any(r['id'].startswith('compiled.') for r in rows):
        raise ValueError('DUPLICATE_OR_RESERVED_PROMPT_SECTION')
    for row in rows:
        # A source row can never attest that the generic compiler ran.
        row.pop('compiledBy', None); row.pop('compilerVersion', None)
        if row.get('sourceLayer') == 'compiled_control_plane':
            row['sourceLayer'] = 'host_authored'
        row['mediumAuthority'] = 'LEGACY_CONFLICT_INPUT' if legacy else 'CHARACTER_FACTS_ONLY'
        check = medium_consistency_gate(intent, row['text'])
        if check['status'] == 'FAIL':
            raise ValueError('MEDIUM_CONSISTENCY_FAIL:' + str(check['conflicts']))
        if not legacy and (positive_matches(row['text'], DECLARATION) or positive_matches(row['text'], LIVE) or positive_matches(row['text'], CG)):
            raise ValueError('HOST_MEDIUM_DECLARATION_FORBIDDEN: use visualMediumIntent')
    emitted = generated_sections(intent)
    rows += emitted
    prompt = '\n\n'.join(row['text'] for row in rows)
    offset = 0
    for row in rows:
        row.update(start=offset, end=offset + len(row['text']), textFingerprint=sha256_canonical(row['text']))
        offset = row['end'] + 2
    gate = medium_consistency_gate(intent, prompt)
    if gate['status'] != 'PASS':
        raise ValueError('MEDIUM_CONSISTENCY_' + gate['status'])
    receipt = dict(visualMedium=intent.visual_medium, compiler=COMPILER, compiledBy=COMPILER,
                   compilerVersion=VERSION, source='control-plane', sourceIntent=source_intent,
                   intent=dump_contract(intent), compiledMediumConstraints=compile_visual_medium(intent),
                   generatedSections=[deepcopy(row) for row in emitted], gateStatus=gate['status'],
                   promptFingerprint=sha256_canonical(prompt))
    return dict(prompt=prompt, promptFingerprint=sha256_canonical(prompt), segments=rows,
                visualMediumIntent=dump_contract(intent), visualMediumCompilation=receipt, mediumGate=gate)


def verify_medium_compilation(brief: dict[str, Any]) -> None:
    """Replay generated sections and recheck the exact final prompt before projection.

    A receipt is reproducibility evidence, not a signature from a trusted server.
    Reservation separately binds source intent and prompt to the authorized Work.
    """
    try:
        intent = VisualMediumIntent.model_validate(brief['visualMediumIntent'])
        receipt = brief['visualMediumCompilation']
        rows = brief['segments']
        prompt = brief['prompt']
        generated = [r for r in rows if r['id'].startswith('compiled.')]
        expected = generated_sections(intent)
        if (receipt['compiler'] != COMPILER or receipt['compiledBy'] != COMPILER or receipt['compilerVersion'] != VERSION
                or receipt['source'] != 'control-plane' or receipt['intent'] != dump_contract(intent)
                or not isinstance(receipt['sourceIntent'], str) or not receipt['sourceIntent'].strip()
                or receipt['visualMedium'] != intent.visual_medium
                or receipt['compiledMediumConstraints'] != compile_visual_medium(intent)
                or receipt['generatedSections'] != generated
                or [{k: r[k] for k in e} for r, e in zip(generated, expected)] != expected
                or len(generated) != len(expected)
                or len({r['id'] for r in rows}) != len(rows)
                or '\n\n'.join(r['text'] for r in rows) != prompt
                or receipt['promptFingerprint'] != sha256_canonical(prompt)
                or brief['promptFingerprint'] != sha256_canonical(prompt)):
            raise ValueError('MEDIUM_COMPILATION_PROOF_MISMATCH')
        offset = 0
        for row in rows:
            if row['start'] != offset or row['end'] != offset + len(row['text']) or row['textFingerprint'] != sha256_canonical(row['text']):
                raise ValueError('MEDIUM_SOURCE_MAP_MISMATCH')
            offset = row['end'] + 2
        gate = medium_consistency_gate(intent, prompt)
        if gate['status'] != 'PASS' or brief['mediumGate'] != gate or receipt['gateStatus'] != gate['status']:
            raise ValueError('MEDIUM_CONSISTENCY_FAIL')
        if 'visualRoute' in brief and brief['visualRoute'] != medium_route(intent):
            raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
        if 'visualLanguage' in brief and legacy_medium_intent(brief['visualLanguage']).visual_medium != intent.visual_medium:
            raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
        for key in ('visualMedium', 'castingMode'):
            if key in brief and brief[key] != dump_contract(intent)[key]:
                raise ValueError('MEDIUM_CONTROL_PLANE_MISMATCH')
    except (KeyError, TypeError) as exc:
        raise ValueError('MEDIUM_COMPILATION_PROOF_REQUIRED') from exc
