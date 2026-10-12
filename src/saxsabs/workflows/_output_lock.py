"""Small cross-process lock for workflow output directories."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import threading
from typing import Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl


_LOCAL_LOCKS: set[str] = set()
_LOCAL_LOCKS_GUARD = threading.Lock()
_LOCK_FILENAME = ".saxsabs.lock"


def _acquire_file_lock(file_handle) -> None:
    file_handle.seek(0)
    if os.name == "nt":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _release_file_lock(file_handle) -> None:
    file_handle.seek(0)
    if os.name == "nt":
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def output_lock(root: Path) -> Iterator[None]:
    """Exclusively lock ``root`` across processes, refusing contention immediately.

    The lock file is persistent by design: unlinking it could let concurrent processes lock
    different inodes. The operating system releases the lock when its owning process exits.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / _LOCK_FILENAME
    lock_key = os.path.normcase(str(lock_path.resolve()))

    with _LOCAL_LOCKS_GUARD:
        if lock_key in _LOCAL_LOCKS:
            raise FileExistsError(f"output directory is already locked in this process: {root}")
        _LOCAL_LOCKS.add(lock_key)

    file_handle = None
    acquired = False
    try:
        file_handle = lock_path.open("a+b")
        file_handle.seek(0, os.SEEK_END)
        if file_handle.tell() == 0:
            file_handle.write(b"\0")
            file_handle.flush()

        try:
            _acquire_file_lock(file_handle)
            acquired = True
        except OSError as exc:
            raise FileExistsError(f"output directory is locked by another process: {root}") from exc

        yield
    finally:
        try:
            if file_handle is not None:
                if acquired:
                    try:
                        _release_file_lock(file_handle)
                    except OSError:
                        # Closing the handle still releases an OS lock after an unlock error.
                        pass
                file_handle.close()
        finally:
            with _LOCAL_LOCKS_GUARD:
                _LOCAL_LOCKS.discard(lock_key)
