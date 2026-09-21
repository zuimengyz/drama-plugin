"""Host-scoped fail-closed read audit for package-only compilation."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import sys

_scope = ContextVar('character_package_source_scope',default=None)
def _audit(event,args):
    scope=_scope.get()
    if scope is None or event!='open' or not isinstance(args[0],(str,bytes)):return
    raw=args[0].decode() if isinstance(args[0],bytes) else args[0]
    path=Path(raw).resolve();record={'path':str(path),'operation':'open'}
    for denied in scope['denied']:
        if path==denied or path.is_relative_to(denied):
            record['allowed']=False;scope['events'].append(record)
            raise PermissionError('FAILED_SOURCE_OF_TRUTH_LEGACY_INPUT_READ')
    if scope['artifact_root'] and path.is_relative_to(scope['artifact_root']) and not path.is_relative_to(scope['task_root']):
        record['allowed']=False;scope['events'].append(record)
        raise PermissionError('FAILED_SOURCE_OF_TRUTH_OLD_ARTIFACT_READ')
    record['allowed']=True;scope['events'].append(record)
sys.addaudithook(_audit)

@contextmanager
def package_source_guard(*, denied_roots, artifact_root=None, task_root=None):
    events=[];token=_scope.set({'denied':[Path(p).resolve() for p in denied_roots],
        'artifact_root':Path(artifact_root).resolve() if artifact_root else None,
        'task_root':Path(task_root).resolve() if task_root else None,'events':events})
    try:yield events
    finally:_scope.reset(token)
