"""Deterministic Seedance translator. No completion, paraphrase or transport."""
from __future__ import annotations
import re
from typing import Any, cast
from drama_plugin.contracts.base import sha256_canonical as fp
from drama_plugin.contracts.visual_prompt import VisualPromptIR
from drama_plugin.prompt_generators.contracts import PromptAtom, CoverageReceipt, ProjectionAnnotations, AtomPriority
from .policy import policy

MODES = ('text_to_video', 'image_to_video', 'first_last_frame', 'reference')
DUTIES = {
    'FACE_IDENTITY': ('identity', '面部身份'), 'HAIR': ('identity', '发型'),
    'BODY': ('identity', '体型'), 'COSTUME': ('costume', '服装'),
    'SCENE': ('environment', '场景'), 'OBJECT': ('prop', '物件'),
}
ROLE = {'identity': '身份', 'costume': '服装', 'prop': '物件', 'environment': '场景',
        'style': '风格', 'motion': '动作', 'camera': '运镜', 'continuity': '连续性'}
OWNER = {'subject': 'specialized-asset-design', 'blocking': 'blocking', 'action': 'action-choreography',
         'camera': 'cinematography', 'lighting': 'lighting-design', 'world': 'scene-development',
         'environment': 'specialized-asset-design', 'video': 'clip-decomposition',
         'continuity': 'shot-design', 'preserve': 'reference-strategy', 'positive_target': 'shot-design',
         'secondary': 'shot-design', 'medium': 'global-visual-style'}
LABELS = {'start_state': '开场', 'end_state': '终态', 'performance': '表演', 'camera_motion': '运镜',
          'positions': '站位', 'orientation': '朝向', 'contact': '接触', 'visible_relation': '关系',
          'current_visible_action': '动作', 'expression': '表情', 'framing': '构图', 'shot_size': '景别',
          'perspective': '视角', 'readable_details': '可见细节', 'time_of_day': '时段',
          'light_sources': '光源', 'contrast': '明暗', 'realism': '成像', 'face': '面部',
          'hair': '头发', 'body_proportions': '体型', 'apparent_age': '年龄', 'costume': '服装',
          'visible_condition': '当前状态', 'beard': '胡须', 'role': '身份'}
ABSTRACT = {'sad', 'angry', 'alienated', 'lonely', '悲伤', '愤怒', '孤独', '疏离'}


def atoms_from_rows(ir: VisualPromptIR, rows: list[dict[str, Any]]) -> list[PromptAtom]:
    atoms = []
    for row in rows:
        path, text = row['path'], row['text']
        group = path.split('.')[0].split('[')[0]
        field = path.rsplit('.', 1)[-1].split('[')[0]
        subject = next((s.id for s in ir.subjects if path.startswith(f'subject.{s.id}.')), None)
        owner = OWNER[group]
        if path == 'action.expression': owner = 'dramatic-performance-direction'
        if path.startswith('video.performance'): owner = 'dramatic-performance-direction'
        if path.startswith('video.camera_motion'): owner = 'cinematography'
        if path.startswith('video.audio_requirements'): owner = 'audio-production'
        # Do not guess the subject/target of an opaque authored proposition. Keep
        # the full clause in the key and record that those roles remain embedded.
        phase = ('start' if group in {'blocking', 'action'} or field == 'start_state' else
                 'end' if field == 'end_state' else path if group == 'video' else 'current')
        priority = row['priority'] if row['priority'] != 'SECONDARY' else ('SUPPORTING' if row['required'] else 'OPTIONAL')
        atoms.append(PromptAtom(obligation_id=path, path=path, source=row['source'], owner=owner,
            scope=(ir.task.clip_id or '') + ':' + row['scope'], subject=(subject,) if subject else tuple(s.id for s in ir.subjects),
            target='EMBEDDED:' + text, relation_action_state=text, temporal_meaning=phase,
            negation='PRESERVE_LITERAL:' + text, reference_duty=field if group == 'subject' else group,
            priority=cast(AtomPriority, priority), required=row['required'] or priority in {'CRITICAL', 'IMPORTANT'}, text=text))
    return atoms


def semantic_key(atom: PromptAtom) -> tuple[Any, ...]:
    # Full literal equality is necessary, never sufficient: scope/owner/duty/time
    # also have to match. No fuzzy/embedding merge or token deletion.
    return (atom.owner, atom.scope, atom.subject, atom.target, atom.relation_action_state,
            atom.temporal_meaning, atom.negation, atom.reference_duty)


def valid_coverage_path(path: str, duty: str, subject: str | None) -> bool:
    if duty in {'FACE_IDENTITY', 'HAIR', 'BODY', 'COSTUME'}:
        field = {'FACE_IDENTITY': 'face', 'HAIR': 'hair', 'BODY': 'body_proportions', 'COSTUME': 'costume'}[duty]
        return subject is not None and path == f'subject.{subject}.{field}'
    if duty == 'SCENE': return path in {'environment.architecture', 'environment.topology'}
    if duty == 'OBJECT': return path.startswith('environment.props_vehicles[')
    return False


class Seedance2PromptGenerator:
    family = 'seedance_2'
    version = '1'
    supported_modes: tuple[str, ...] = MODES

    def generate(self, ir: VisualPromptIR, rows: list[dict[str, Any]], *,
                 context: dict[str, Any], hard_limit: int) -> dict[str, Any]:
        mode = context['mode']
        if mode not in MODES:
            raise ValueError('SEEDANCE_UNSUPPORTED_MODE:' + mode)
        if ir.video_temporal is None:
            raise ValueError('UNRESOLVED:clip-decomposition:TEMPORAL_REQUIRED')
        if hard_limit <= 0: raise ValueError('SEEDANCE_PROVIDER_HARD_LIMIT_REQUIRED')
        annotation = ProjectionAnnotations.model_validate(context.get('annotations', {}))
        if annotation.camera_conflict:
            raise ValueError('UNRESOLVED:cinematography:SIMULTANEOUS_CAMERA_CONFLICT')
        if annotation.approved_compound_camera_source and annotation.approved_compound_camera_source != ir.video_temporal.camera_motion.source:
            raise ValueError('UNRESOLVED:cinematography:COMPOUND_SOURCE_MISMATCH')
        camera = ir.video_temporal.camera_motion.text
        opposite = (('推近' in camera and '拉远' in camera and '同时' in camera)
                    or ('push in' in camera and 'pull out' in camera and 'simultaneous' in camera))
        if opposite and not annotation.approved_compound_camera_source:
            raise ValueError('UNRESOLVED:cinematography:SIMULTANEOUS_CAMERA_CONFLICT')
        # Literal diagnostics supplement (never replace) upstream professional review.
        for row in rows:
            if re.search(r'@(?:图片|视频|音频)\d+|<主体\d+>', row['text']):
                raise ValueError('UNRESOLVED:reference-strategy:PROVIDER_LABELS_MUST_BE_GENERATED')
            if (row['path'].startswith(('action.', 'video.performance', 'video.action_progression'))
                    and row['text'].removeprefix('AT CLIP START: ').strip().casefold() in ABSTRACT):
                raise ValueError('UNRESOLVED:performance:OBSERVABLE_CARRIER_REQUIRED:' + row['path'])
        if ir.subjects and not (ir.action and ir.blocking):
            raise ValueError('UNRESOLVED:action:APPROVED_ACTION_REQUIRED')
        subjects = {s.id: f'<主体{i + 1}>' for i, s in enumerate(sorted(ir.subjects, key=lambda s: s.id))}
        aliases = {s.role.text: subjects[s.id] for s in ir.subjects}
        if len(aliases) != len(subjects):
            raise ValueError('UNRESOLVED:character:AMBIGUOUS_SUBJECT_ROLE')
        atoms = atoms_from_rows(ir, rows)
        by_path = {a.path: a for a in atoms}
        if len(by_path) != len(atoms): raise ValueError('DUPLICATE_OBLIGATION_ID')
        refs = context['references']
        if mode == 'text_to_video' and refs: raise ValueError('SEEDANCE_T2V_HAS_REFERENCES')
        if mode != 'text_to_video' and not refs: raise ValueError('SEEDANCE_REFERENCE_REQUIRED')
        counters = {'image': 0, 'video': 0, 'audio': 0}
        kind_name = {'image': '图片', 'video': '视频', 'audio': '音频'}
        coverage: dict[str, tuple[dict[str, Any], str, str]] = {}
        preamble: list[str] = []
        slots = []
        for ref in refs:
            kind = ref['kind']; counters[kind] += 1
            tag = '@' + kind_name[kind] + str(counters[kind])
            slots.append(dict(tag=tag, media_id=ref['media_id'], version=ref['version'], content_hash=ref['content_hash'], slot=ref['slot']))
            binding = ref.get('prompt_binding') or {}
            actor = binding.get('subject_id')
            if actor is not None and actor not in subjects: raise ValueError('UNRESOLVED:reference-strategy:UNKNOWN_SUBJECT')
            if ir.subjects and set(ref['semantics']) & {'identity', 'costume'} and actor is None:
                raise ValueError('UNRESOLVED:reference-strategy:SUBJECT_BINDING_REQUIRED')
            prefix = subjects.get(actor, '') if actor is not None else ''
            duties = '、'.join(ROLE[x] for x in ref['semantics'])
            preamble.append(f'{prefix}仅参考 {tag} 的{duties}。')
            if ref['slot'] in {'first_frame', 'last_frame'}:
                preamble.append(f'{tag} 作为' + ('首帧' if ref['slot'] == 'first_frame' else '尾帧') + '约束。')
            for excluded in binding.get('must_not_carry', ()):
                preamble.append(f'{tag} 不承担' + {'pose': '姿势', 'lighting': '灯光', 'composition': '构图', 'expression': '表情'}[excluded] + '职责。')
            for claim in binding.get('coverage', ()):
                path, duty = claim['path'], claim['duty']
                atom = by_path.get(path)
                if (atom is None or kind != 'image' or DUTIES[duty][0] not in ref['semantics']
                        or not valid_coverage_path(path, duty, actor)
                        or atom.source != claim['source'] or fp(atom.text) != claim['text_hash']
                        or not ref['review_ref']):
                    raise ValueError('SEEDANCE_REFERENCE_COVERAGE_UNVERIFIED:' + path)
                if path in coverage: raise ValueError('SEEDANCE_MULTIPLE_COVERAGE_AUTHORITIES:' + path)
                reference_phrase = f'{prefix}的{DUTIES[duty][1]}保持与 {tag} 一致。' if prefix else f'{DUTIES[duty][1]}保持与 {tag} 一致。'
                coverage[path] = (ref, tag, reference_phrase)
        audio = {x.path: x for x in annotation.audio}
        if len(audio) != len(annotation.audio): raise ValueError('SEEDANCE_DUPLICATE_AUDIO_BINDING')
        audio_paths = {a.path for a in atoms if a.path.startswith('video.audio_requirements')}
        if set(audio) != audio_paths:
            raise ValueError('UNRESOLVED:audio-production:EXACT_AUDIO_BINDING_REQUIRED')

        def literal(text: str, *, replace_aliases: bool = True) -> str:
            # Only explicit canonical actor placeholders are substituted; no name
            # guessing, pronoun rewriting, or replacement inside approved dialogue.
            for actor, label in subjects.items(): text = text.replace('{{actor:' + actor + '}}', label)
            if '{{actor:' in text: raise ValueError('UNRESOLVED:character:UNKNOWN_ACTOR_TOKEN')
            if replace_aliases and aliases:
                pattern = '|'.join(('(?<![A-Za-z0-9_])' + re.escape(alias) + '(?![A-Za-z0-9_])'
                                    if alias.isascii() else re.escape(alias))
                                   for alias in sorted(aliases, key=len, reverse=True))
                text = re.sub(pattern, lambda match: aliases[match[0]], text)
            return text

        def phrase(atom: PromptAtom) -> str:
            if atom.path in coverage: return coverage[atom.path][2]
            if atom.path in audio:
                a = audio[atom.path]
                if a.source != atom.source or a.text_hash != fp(atom.text): raise ValueError('SEEDANCE_DIALOGUE_SOURCE_CHANGED')
                if not context['native_audio']: raise ValueError('SEEDANCE_AUDIO_UNSUPPORTED')
                if a.kind == 'DIALOGUE':
                    if a.speaker not in subjects or not a.language: raise ValueError('UNRESOLVED:dialogue-design:SPEAKER_LANGUAGE_REQUIRED')
                    return (a.timing + ' ' if a.timing else '') + f'{subjects[a.speaker]} 用{a.language}说道' + '{' + atom.text + '}'
                left, right = ('（', '）') if a.kind == 'BGM' else ('<', '>')
                return (a.timing + ' ' if a.timing else '') + left + atom.text + right
            field = atom.path.rsplit('.', 1)[-1].split('[')[0]
            text = literal(atom.text, replace_aliases=field != 'role')
            if atom.path.startswith(('blocking.', 'action.')):
                text = text.removeprefix('AT CLIP START: ')
            label = LABELS.get(field, '')
            if atom.path.startswith('video.action_progression'):
                label = '事件' + str(int(atom.path.rsplit('[', 1)[1].rstrip(']')) + 1)
            elif atom.path.startswith(('continuity[', 'preserve[')):
                label = '全程保持' if atom.scope.endswith(':CLIP') else '当前保持'
            if atom.path.startswith(('blocking.', 'action.')): label = '开场' + label
            if atom.path.startswith('subject.'):
                label = subjects[atom.subject[0]] + label
            return (label + '：' if label else '') + text

        # A duplicate may share one span only if its complete scoped proposition
        # agrees. Required is OR across the group; optional cannot erase critical.
        groups: dict[tuple[Any, ...], list[PromptAtom]] = {}
        for atom in atoms:
            key = (semantic_key(atom), coverage.get(atom.path, (None, None, None))[1],
                   atom.path if atom.path in audio else '')
            groups.setdefault(key, []).append(atom)
        selected = list(groups.values())
        complex_clip = len(ir.video_temporal.action_progression) > 1

        def render(groups_to_emit: list[list[PromptAtom]]) -> tuple[str, list[CoverageReceipt]]:
            text = ''.join(preamble)
            receipts = []
            for group in groups_to_emit:
                first = group[0]
                if text: text += '\n' if complex_clip else '；'
                start = len(text); text += phrase(first); end = len(text)
                for atom in group:
                    if atom.path in coverage:
                        ref, tag, _ = coverage[atom.path]
                        receipts.append(CoverageReceipt(obligation_id=atom.obligation_id, status='REFERENCE_COVERED',
                            span=(start, end), input_tag=tag, input_hash=ref['content_hash'], input_version=ref['version'],
                            duty=atom.reference_duty))
                    else:
                        receipts.append(CoverageReceipt(obligation_id=atom.obligation_id, status='TEXT_COVERED', span=(start, end)))
            return text, receipts

        full, _ = render(selected)
        omitted: list[dict[str, str]] = []
        for group in reversed(list(selected)):
            if len(render(selected)[0]) <= hard_limit: break
            if all(a.priority == 'OPTIONAL' and not a.required for a in group):
                selected.remove(group)
                omitted.extend({'path': a.path, 'reason': 'APPROVED_OPTIONAL_BUDGET'} for a in group)
        prompt, receipts = render(selected)
        if len(prompt) > hard_limit:
            raise ValueError('SEEDANCE_CRITICAL_BUDGET_OVERFLOW:RETURN_TO_PLANNING')
        covered = [r.obligation_id for r in receipts]
        if len(covered) != len(set(covered)) or any(a.required and a.obligation_id not in covered for a in atoms):
            raise ValueError('SEEDANCE_REQUIRED_OBLIGATION_UNCOVERED')
        # No internal addresses or unauthored reference tags in the final text.
        if re.search(r'asset-[\w-]+|media-id|SourcePin|\{\{actor:', prompt):
            raise ValueError('SEEDANCE_INTERNAL_IDENTIFIER_LEAK')
        for ref in refs:
            if len(ref['media_id']) > 3 and ref['media_id'] in prompt: raise ValueError('SEEDANCE_INTERNAL_IDENTIFIER_LEAK')
        valid_tags = {s['tag'] for s in slots}
        if not set(re.findall(r'@(?:图片|视频|音频)\d+', prompt)) <= valid_tags:
            raise ValueError('SEEDANCE_UNBOUND_REFERENCE_TAG')
        return dict(prompt=prompt, generator=dict(family=self.family, version=self.version, mode=mode,
                    policy=policy(), soft_budget='UNVALIDATED'),
                    atoms=[a.model_dump(mode='json') for a in atoms],
                    coverage=[r.model_dump(mode='json') for r in receipts], input_slots=slots,
                    retained=[r for r in rows if r['path'] in covered], omitted=omitted,
                    statistics=dict(obligations_total=len(atoms), text_covered=sum(r.status == 'TEXT_COVERED' for r in receipts),
                        reference_covered=sum(r.status == 'REFERENCE_COVERED' for r in receipts),
                        omitted_optional=len(omitted), uncovered_required=0,
                        semantic_duplicates=sum(len(g)-1 for g in groups.values()), chars_before_budget=len(full), chars_after=len(prompt)))
