"""Vidu clip projection; full temporal facts and authority anchors stay executable."""
from typing import Any
from drama_plugin.contracts.visual_prompt import VisualPromptIR


def select_rows(ir: VisualPromptIR, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    # Text-only generation has no image to carry static appearance/context.
    if ir.task.input_mode == 'text':
        return rows, []
    kept, omitted = [], []
    for row in rows:
        path = row['path']
        needed = (path.startswith(('video.', 'world.', 'blocking.', 'action.', 'lighting.', 'camera.',
                                   'continuity[', 'preserve[', 'positive_target['))
                  or path in {'medium', 'environment.architecture'}
                  or path.startswith('subject.') and path.rsplit('.', 1)[-1] in {'role', 'apparent_age', 'face', 'costume'})
        if needed:
            kept.append(row)
        else:
            omitted.append({'path': path, 'reason': 'REFERENCE_STATIC_DETAIL_NOT_REDESCRIBED'})
    return kept, omitted


def render(ir: VisualPromptIR, rows: list[dict[str, Any]]) -> str:
    used: set[str] = set()
    def section(title: str, prefixes: tuple[str, ...]) -> str:
        texts = []
        for row in rows:
            if row['path'].startswith(prefixes):
                text = row['text'].removeprefix('AT CLIP START: ')
                if text not in used:
                    texts.append(text); used.add(text)
        return title + '\n' + '\n'.join(texts) if texts else ''
    # Bind canonical speaker/actor keys to their visible role without expanding a Bible.
    identities = []
    for subject in ir.subjects:
        facts = [r['text'] for r in rows if r['path'].startswith(f'subject.{subject.id}.')]
        identities.append(subject.id + ': ' + '；'.join(dict.fromkeys(facts)))
        used.update(facts)
    parts = [section('START STATE', ('video.start_state', 'blocking.', 'action.')),
             'IDENTITY\n' + '\n'.join(identities) if identities else '',
             section('ACTION', ('video.action_progression',)),
             section('PERFORMANCE', ('video.performance',)),
             section('CAMERA', ('video.camera_motion', 'camera.')),
             # Endpoints remain explicit even when identical to the start.
             'END STATE\n' + ir.video_temporal.end_state.text if ir.video_temporal else '',
             section('AUDIO', ('video.audio_requirements',)),
             section('SETTING / CONTINUITY', ('medium', 'world.', 'environment.', 'lighting.',
                                               'continuity[', 'preserve[', 'positive_target[', 'secondary['))]
    return '\n\n'.join(p for p in parts if p)
