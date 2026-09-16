"""Common store contract: native POSIX and Windows CRT simulation, never Windows E2E."""
import errno
import os
from pathlib import PurePosixPath, PureWindowsPath
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from drama_plugin.contracts.base import dump_contract
from drama_plugin.contracts.director import CapabilityRequest, DirectorWorkspace
from drama_plugin.director import DirectorError, pin, request_pin
from drama_plugin.hosts.artifact_io import local_root, relative_artifact
from drama_plugin.hosts.artifact_windows import WindowsArtifactIO
from drama_plugin.hosts.director_artifacts import DirectorArtifactStore


class SimulatedCRT:
    """Byte-lock semantics only; actual msvcrt must also run in Windows CI."""
    LK_NBLCK = 1
    LK_UNLCK = 2
    def __init__(self):
        self.mutex = threading.Lock()
        self.held = set()
    def locking(self, fd, mode, count):
        assert count == 1 and os.lseek(fd, 0, os.SEEK_CUR) == 0
        key = (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        with self.mutex:
            if mode == self.LK_UNLCK:
                self.held.remove(key)
            elif key in self.held:
                raise OSError(errno.EACCES, 'locked')
            else:
                self.held.add(key)


@pytest.fixture(params=['native', 'windows-crt-simulation'])
def io(request):
    if request.param == 'native':
        from drama_plugin.hosts.artifact_io import native_io
        return native_io()
    return WindowsArtifactIO(SimulatedCRT(), timeout=1)


def started(tmp_path, io):
    s = DirectorArtifactStore(tmp_path, io=io)
    src, intent = pin('scene', {'canonical': 1}), pin('intent', {'experience': 1})
    w = s.create(DirectorWorkspace(workspace_id='w', scope_id='s', branch_id='a',
        source_pins=(src,), intent_refs=(intent,)))
    q = CapabilityRequest(request_id='q', workspace_id='w', scope_id='s', branch_id='a',
        source_pins=(src,), intent_refs=(intent,), capability='shot-design', task='Review coverage',
        required_evidence=('coverage necessity',), result_kind='DESIGN_ONLY',
        must_preserve=('canon',), prohibitions=(), priority='HIGH')
    ref = s.put(request_pin(q).key, dump_contract(q))
    current = {p.key: p.fingerprint for p in (src, intent)}
    return s, s.transition(w, 'REQUEST', ref, current), q, current


def test_store_create_load_cas_branch_resume_stale(tmp_path, io):
    s, w, q, current = started(tmp_path, io)
    b = s.create(DirectorWorkspace(workspace_id='w', scope_id='s', branch_id='b', source_pins=w.source_pins))
    assert s.load('w', 'a') == w
    def dispatch(_):
        try:
            DirectorArtifactStore(tmp_path, io=io).transition(w, 'DISPATCH', None, current)
            return 'committed'
        except DirectorError as e:
            return e.code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(dispatch, range(2))) == ['REVISION_CONFLICT', 'committed']
    assert s.load('w', 'b') == b
    assert s.resume('w', 'a', current)['action'] == 'RECONCILE_RESULT'
    current['scene'] = 'b' * 64
    assert s.resume('w', 'a', current)['action'] == 'STALE_SOURCE'
    with pytest.raises(DirectorError, match='STALE_SOURCE'):
        s.transition(s.load('w', 'a'), 'DISPATCH', None, current)
    assert s.load('w', 'a').stale_keys == ('scene',)


def test_atomic_replace_failure_keeps_old_head_and_releases_lock(tmp_path, io, monkeypatch):
    s, w, _, current = started(tmp_path, io)
    replace = os.replace
    def fail_head(src, dst):
        if dst.parent.name == 'heads':
            raise OSError('simulated sharing violation / disk error')
        return replace(src, dst)
    monkeypatch.setattr(os, 'replace', fail_head)
    with pytest.raises(OSError):
        s.transition(w, 'DISPATCH', None, current)
    assert s.load('w', 'a') == w
    monkeypatch.setattr(os, 'replace', replace)
    assert s.transition(w, 'DISPATCH', None, current).checkpoint == 'DISPATCHED'
    assert not list(tmp_path.rglob('.pending-*'))


@pytest.mark.parametrize('root,windows,expected', [
    ('/Users/example/project', False, PurePosixPath('/Users/example/project')),
    ('/home/example/project', False, PurePosixPath('/home/example/project')),
    (r'D:\home\AI', True, PureWindowsPath(r'D:\home\AI')),
    ('file:///D:/home/AI/test.png', True, PureWindowsPath(r'D:\home\AI\test.png')),
])
def test_platform_paths(root, windows, expected):
    assert local_root(root, windows=windows) == expected
    assert relative_artifact(expected, 'objects/one.json') == expected / 'objects' / 'one.json'


@pytest.mark.parametrize('reference', ['../x', '/Users/x', r'D:\x', 'file:///D:/x', r'D:x', r'..\x'])
@pytest.mark.parametrize('root', [PurePosixPath('/home/x'), PureWindowsPath(r'D:\x')])
def test_relative_boundary(root, reference):
    with pytest.raises(ValueError):
        relative_artifact(root, reference)


def test_foreign_root_not_misread_and_core_import_has_no_platform_dependency():
    for root in (r'D:\home\AI', 'file:///D:/home/AI/test.png'):
        with pytest.raises(ValueError):
            local_root(root, windows=False)
    script = '''import sys
sys.modules['fcntl'] = None
sys.modules['msvcrt'] = None
import drama_plugin.director
import drama_plugin.contracts.director
import drama_plugin.hosts.artifact_windows
import drama_plugin.hosts.director_artifacts
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_windows_busy_timeout_does_not_write(tmp_path):
    io = WindowsArtifactIO(SimulatedCRT(), timeout=0)
    path = tmp_path / 'lock'
    with io.guard(path):
        with pytest.raises(TimeoutError):
            with io.guard(path):
                pytest.fail('lock must exclude another writer')
    with io.guard(path):
        pass


def test_legacy_native_relative_root(tmp_path, monkeypatch, io):
    monkeypatch.chdir(tmp_path)
    store = DirectorArtifactStore('relative', io=io)
    assert store.root == tmp_path / 'relative'
    ref = store.put('x', {'source': 'stable'})
    assert store.read_ref(ref) == {'source': 'stable'}
