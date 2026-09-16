"""Linux/macOS implementation. fcntl is intentionally isolated to this module."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
from typing import Iterator
from drama_plugin.hosts.artifact_io import atomic_write, reject_link


class PosixArtifactIO:
    @contextmanager
    def guard(self, path: Path) -> Iterator[None]:
        reject_link(path)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def write(self, path: Path, text: str) -> None:
        atomic_write(path, text, sync_directory=True)
