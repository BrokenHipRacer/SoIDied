"""Single-process leadership for the check-in background tracker.

When several app workers run (for example gunicorn with multiple processes), only the
process that acquires an exclusive lock on ``check_in_scheduler_lock_file`` starts the
APScheduler job. Other workers skip tracker startup and continue serving API requests.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_LOCK_FILE = 'instance/check_in_scheduler.lock'

_lock_fd: int | None = None
_lock_path: Path | None = None


def scheduler_lock_path(settings) -> Path:
    configured = settings.get('defences', {}).get(
        'check_in_scheduler_lock_file',
        DEFAULT_LOCK_FILE,
    )
    return Path(configured)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def _read_lock_pid(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding='utf-8').strip()
    except OSError:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _remove_stale_lock(path: Path) -> None:
    pid = _read_lock_pid(path)
    if pid is not None and _pid_alive(pid):
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def try_acquire_scheduler_leadership(lock_path: Path | str) -> bool:
    """Return True when this process becomes the scheduler leader."""
    global _lock_fd, _lock_path

    if _lock_fd is not None:
        return True

    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if os.name == 'nt':
        _remove_stale_lock(path)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError:
            return False
        os.write(fd, str(os.getpid()).encode())
        _lock_fd = fd
        _lock_path = path
        return True

    import fcntl

    fd = os.open(str(path), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return False
    os.ftruncate(fd, 0)
    os.write(fd, str(os.getpid()).encode())
    _lock_fd = fd
    _lock_path = path
    return True


def release_scheduler_leadership() -> None:
    """Release the leader lock held by this process, if any."""
    global _lock_fd, _lock_path

    if _lock_fd is None:
        return

    fd = _lock_fd
    path = _lock_path
    _lock_fd = None
    _lock_path = None

    if os.name != 'nt':
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass

    try:
        os.close(fd)
    except OSError:
        pass

    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
