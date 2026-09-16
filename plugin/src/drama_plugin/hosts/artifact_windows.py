"""Windows byte-range writer lock + flushed same-volume replacement; no POSIX imports."""
from contextlib import contextmanager
import errno
import importlib
import os
from pathlib import Path
import time
from typing import Iterator, Protocol, cast
from drama_plugin.hosts.artifact_io import atomic_write, reject_link


class WindowsLocking(Protocol):
    LK_NBLCK: int
    LK_UNLCK: int
    def locking(self, fd: int, mode: int, count: int, /) -> None: ...


class WindowsArtifactIO:
    def __init__(self, api: WindowsLocking | None = None, *, timeout: float = 10.0):
        # Injection is for contract simulation; real Windows uses its standard CRT.
        self.api = api if api is not None else cast(WindowsLocking, importlib.import_module('msvcrt'))
        self.timeout = timeout

    @contextmanager
    def guard(self, path: Path) -> Iterator[None]:
        reject_link(path)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'r+b', buffering=0) as lock:
            if os.fstat(fd).st_size == 0:
                lock.write(b'\0')
            deadline = time.monotonic() + self.timeout
            while True:
                lock.seek(0)
                try:
                    self.api.locking(fd, self.api.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Workspace writer is busy; no update committed') from error
                    time.sleep(0.01)
            try:
                yield
            finally:
                lock.seek(0)
                self.api.locking(fd, self.api.LK_UNLCK, 1)

    def write(self, path: Path, text: str) -> None:
        # Windows does not support opening a directory for fsync with os.open.
        # Failure to replace (e.g. an external reader denies sharing) fails closed.
        atomic_write(path, text, sync_directory=False)
