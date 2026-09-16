"""Local artifact IO semantics; platform APIs live behind this small Host boundary."""
from __future__ import annotations
from contextlib import AbstractContextManager
import os
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
import tempfile
from typing import Protocol
from urllib.parse import urlsplit
from drama_plugin.providers.http.media_source import _file_uri_path


class ArtifactIO(Protocol):
    def guard(self, path: Path) -> AbstractContextManager[None]: ...
    def write(self, path: Path, text: str) -> None: ...


def local_root(value: str | PurePath, *, windows: bool | None = None) -> PurePath:
    """Reuse the existing repaired file-URI conversion; drive letters are not URL schemes."""
    use_windows = os.name == 'nt' if windows is None else windows
    text = str(value)
    if PureWindowsPath(text).drive and not text.lower().startswith('file:'):
        if not use_windows:
            raise ValueError('Foreign Windows root requires a Windows Host')
        path: PurePath = PureWindowsPath(text)
    elif text.lower().startswith('file:'):
        parsed = urlsplit(text)
        if parsed.netloc not in ('', 'localhost') or parsed.query or parsed.fragment:
            raise ValueError('Only a local file root is permitted')
        if not use_windows and len(parsed.path) > 3 and parsed.path[2] == ':':
            raise ValueError('Foreign Windows file root requires a Windows Host')
        path = _file_uri_path(parsed.path, windows=use_windows)
    else:
        if '://' in text:
            raise ValueError('Artifact root must be local')
        path = PureWindowsPath(text) if use_windows else PurePosixPath(text)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Artifact root must be absolute and normalized')
    return path


def relative_artifact(root: PurePath, reference: str) -> PurePath:
    """Workspace-relative reference; reject foreign absolute paths and traversal on every OS."""
    win = PureWindowsPath(reference)
    if win.drive or win.root or PurePosixPath(reference).is_absolute() or '://' in reference:
        raise ValueError('Expected a workspace-relative artifact reference')
    relative = type(root)(reference)
    if not reference or '..' in relative.parts or '\\' in reference and not isinstance(root, PureWindowsPath):
        raise ValueError('Unsafe artifact reference')
    return root / relative


def reject_link(path: Path) -> None:
    if path.is_symlink() or path.is_junction():
        raise ValueError('Artifact IO does not follow links or junctions')


def atomic_write(path: Path, text: str, *, sync_directory: bool) -> None:
    reject_link(path.parent)
    reject_link(path)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)  # same volume; close every handle before replacing
        if sync_directory:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def native_io() -> ArtifactIO:
    if os.name == 'nt':
        from drama_plugin.hosts.artifact_windows import WindowsArtifactIO
        return WindowsArtifactIO()
    from drama_plugin.hosts.artifact_posix import PosixArtifactIO
    return PosixArtifactIO()
