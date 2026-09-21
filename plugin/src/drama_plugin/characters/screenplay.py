"""Source-bound inventory; semantic grouping/dedication is explicitly Host-authored."""
import re
from .repository import CharacterPackageError, digest

def approved_screenplay(work: dict, screenplay: bytes) -> dict:
    content = work['content']
    if content.get('approval',{}).get('status') != 'APPROVED':
        raise CharacterPackageError('CURRENT_APPROVED_WORK_REQUIRED')
    authority = content.get('screenplayAuthority',{})
    expected = authority.get('sha256')
    if expected != digest(screenplay): raise CharacterPackageError('CURRENT_SCREENPLAY_HASH_MISMATCH')
    scenes = []; current = None
    for number,line in enumerate(screenplay.decode('utf-8').splitlines(),1):
        match = re.match(r'^#{2,3}\s+(S\d+)\b(.*)',line)
        if match:
            current = {'sceneId':match[1], 'heading':match[2].strip(), 'line':number, 'cast':[], 'speakers':[]}
            scenes.append(current)
        elif current:
            if '**Character：**' in line or '出场' in line[:20]: current['cast'].append({'line':number,'text':line})
            if re.match(r'^\*\*[^*]+〔[^*]+：\*\*',line): current['speakers'].append({'line':number,'text':line})
    if not scenes: raise CharacterPackageError('SCREENPLAY_SCENES_NOT_PARSED')
    return {'sourceWork':work['id'],'sourceRevision':content['revisionId'],'sourceFingerprint':expected,
            'scenes':scenes,'semanticClassificationOwner':'HOST_CHARACTER_EXTERNAL_DRIVER'}
