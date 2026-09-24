"""Static-image execution prose. IR keys and priorities stay in the audit record."""
from typing import Any
from drama_plugin.contracts.visual_prompt import VisualPromptIR

MEDIUM = {'LIVE_ACTION': 'Live-action cinematic still.', 'DESIGNED_CG': 'Designed cinematic CG still.',
          'CINEMATIC_CG': 'Cinematic CG still.', 'ILLUSTRATION': 'Illustration.', 'ANIMATION': 'Animation still.'}


def select_image_rows(ir: VisualPromptIR, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not ir.edit_delta:
        return rows, []
    # An edit is a delta over the supplied image. Keep identity/clothing anchors
    # and current relations, not a re-generation of every asset surface detail.
    selected = []; omitted = []
    for row in rows:
        path = row['path']
        needed = (path.startswith(('edit_delta[', 'preserve[', 'world.', 'blocking.', 'action.', 'positive_target['))
                  or path in {'medium', 'environment.architecture', 'lighting.realism'}
                  or path.startswith('subject.') and path.rsplit('.', 1)[-1] in {'role', 'face', 'costume'})
        if needed:
            selected.append(row)
        else:
            omitted.append({'path': path, 'reason': 'EDIT_SOURCE_PRESERVED_NOT_REDESCRIBED'})
    return selected, omitted


def render_image(ir: VisualPromptIR, rows: list[dict[str, Any]]) -> str:
    values = {r['path']: r['text'] for r in rows}
    def texts(*prefixes: str) -> list[str]:
        return [r['text'] for r in rows if r['path'].startswith(prefixes)]
    def unique(items: list[str]) -> list[str]:
        return list(dict.fromkeys(items))
    def prose(items: list[str]) -> str:
        return ' '.join(unique(items))
    def section(title: str, items: list[str]) -> str:
        content = prose(items)
        return title + '\n' + content if content else ''
    def subjects() -> list[str]:
        output = []
        for subject in ir.subjects:
            prefix = f'subject.{subject.id}.'
            facts = [r['text'] for r in rows if r['path'].startswith(prefix) and r['path'] != prefix + 'role']
            if facts:
                output.append(subject.role.text + ': ' + '; '.join(unique(facts)))
        return output
    medium = MEDIUM[ir.task.visual_medium] if 'medium' in values else ''
    if ir.edit_delta:
        changes = []
        for i, delta in enumerate(ir.edit_delta):
            # Render the typed operation, not a positive paraphrase of the issue.
            if f'edit_delta[{i}].{delta.operation}' in values:
                changes.append(f'- {delta.operation.capitalize()} {delta.region}: {delta.source_issue.text} → {delta.target_correction.text}')
        preservation = unique(texts('preserve[') + subjects() + texts('blocking.', 'action.'))
        return '\n\n'.join([
            'MUST CHANGE\n' + '\n'.join(changes),
            'PRESERVE\nKeep the supplied image unchanged except for the corrections above.\n' +
                '\n'.join('- ' + text for text in preservation),
            section('TARGET RESULT', texts('world.') + texts('environment.architecture') +
                    [medium] + texts('lighting.realism', 'positive_target[')),
        ])
    # First/key frames are initial static targets, never source-image repairs.
    sections = [section('TARGET WORLD', texts('world.')),
                section('SUBJECTS', subjects()),
                section('CURRENT BLOCKING', texts('blocking.', 'action.')),
                section('ENVIRONMENT', texts('environment.')),
                section('CAMERA', texts('camera.')),
                section('LIGHTING', texts('lighting.')),
                section('TARGET LOOK', [medium] + texts('positive_target[', 'continuity[', 'preserve[', 'secondary['))]
    return '\n\n'.join(s for s in sections if s)
