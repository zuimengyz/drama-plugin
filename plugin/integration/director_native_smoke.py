"""One native, offline artifact smoke entry for macOS/Linux/Windows.

Run with the installed package on PYTHONPATH. No mocks, providers, or formal data.
The same spawned-process CAS race uses the actual OS adapter on every platform.
"""
from __future__ import annotations
import argparse
import json
import multiprocessing
import platform
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.director import CapabilityRequest, DirectorWorkspace
from drama_plugin.director import DirectorError, pin, request_pin
from drama_plugin.hosts.artifact_io import local_root, relative_artifact
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore
from drama_plugin.hosts.director_runtime import resume_with_execution


def contender(root: str, expected: dict[str, Any], current: dict[str, str], queue: Any) -> None:
    try:
        store = DirectorArtifactStore(root)
        store.transition(DirectorWorkspace.model_validate(expected), 'DISPATCH', None, current)
        queue.put('COMMITTED')
    except DirectorError as error:
        queue.put(error.code)


def run() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix='director-native-') as directory:
        store = DirectorArtifactStore(Path(directory))
        source = pin('source:smoke', {'canonical': 'synthetic native smoke only'})
        intent = store.put('intent:smoke', {'experience': 'test transport invariants'})
        current = {p.key: p.fingerprint for p in (source, intent)}
        w = store.create(DirectorWorkspace(workspace_id='smoke', scope_id='scope', branch_id='live',
            source_pins=(source,), intent_refs=(intent,)))
        other = store.create(DirectorWorkspace(workspace_id='smoke', scope_id='scope', branch_id='cg', source_pins=(source,)))
        checks['create_load'] = store.load('smoke', 'live') == w
        q = CapabilityRequest(request_id='request', workspace_id='smoke', scope_id='scope', branch_id='live',
            source_pins=w.source_pins, intent_refs=w.intent_refs, capability='shot-design', task='Smoke only',
            required_evidence=('CONTRACT_VALID',), must_preserve=('source',), prohibitions=(), priority='HIGH', result_kind='DESIGN_ONLY')
        w = store.transition(w, 'REQUEST', store.put(request_pin(q).key, dump_contract(q)), current)
        ctx = multiprocessing.get_context('spawn'); queue = ctx.Queue()
        processes = [ctx.Process(target=contender, args=(directory, dump_contract(w), current, queue)) for _ in range(2)]
        for process in processes: process.start()
        for process in processes:
            process.join(15)
            if process.is_alive():
                process.terminate(); process.join()
                raise AssertionError('Native lock/CAS process exceeded time bound')
            assert process.exitcode == 0
        outcomes = sorted(queue.get(timeout=5) for _ in processes)
        queue.close()
        checks['native_multiprocess_lock_cas'] = outcomes == ['COMMITTED', 'REVISION_CONFLICT']
        checks['checkpoint_atomic_replace'] = store.load('smoke', 'live').checkpoint == 'DISPATCHED' and not list(Path(directory).rglob('.pending-*'))
        checks['branch_isolation'] = store.load('smoke', 'cg') == other
        state = resume_with_execution(store, 'smoke', 'live', current, lambda _: None)
        checks['resume_uncertain_no_redispatch'] = state['action'] == 'RECONCILIATION_REQUIRED' and not state['delegate']
        changed = {**current, source.key: 'f' * 64}
        checks['stale_resume'] = store.resume('smoke', 'live', changed)['action'] == 'STALE_SOURCE'
        checks['relative_long_term_refs'] = directory not in json.dumps(dump_contract(store.load('smoke', 'live')))
        assert store.read_ref(intent)['experience'] == 'test transport invariants'
        checks['immutable_artifact_read'] = True
        for root in (r'D:\home\AI', 'D:/home/AI', 'file:///D:/home/AI'):
            parsed = local_root(root, windows=True)
            assert parsed == PureWindowsPath(r'D:\home\AI') and parsed.is_absolute()
            assert relative_artifact(parsed, 'objects/test.json') == parsed / 'objects' / 'test.json'
        checks['windows_path_contract'] = True  # native Windows IO only when platform.system()==Windows
        try: relative_artifact(Path(directory), '../escape')
        except ValueError: checks['workspace_boundary'] = True
        assert all(checks.values()), checks
        return {'platform': platform.system(), 'kernel': platform.release(), 'python': platform.python_version(),
            'adapter': type(store.io).__name__, 'level': 'NATIVE_OFFLINE_PASS', 'checks': checks,
            'casOutcomes': outcomes, 'providerCalls': 0, 'formalWrites': 0,
            'windowsIOActuallyRun': platform.system() == 'Windows'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))
